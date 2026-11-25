import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import doorinews_editor as editor
import news_nov25_scope as policy
import news_manual_nov25 as manual
import news_review_cache as cache
import news_images as images
from news_quality import manual_post_reason
from news_event_review import history_records, url_key


def story(title, url='https://example.com/new'):
    return dict(title=title, url=url, pub=max(datetime.now(timezone.utc),
                policy.ENABLED_AT + timedelta(minutes=1)).isoformat())


class Nov25Feedback(unittest.TestCase):
    def test_bounded_new_candidates_reach_review(self):
        for index in (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12):
            s = story(manual.EVENTS[index][1])
            self.assertTrue(policy.scope(s), s['title'])
            self.assertFalse(editor._is_hard_blocked(s)[0], (s, editor._is_hard_blocked(s)))
            self.assertTrue(editor.matches_keywords(s, [], [], []), s)
        for title in ('UniCredit opens €1,000 Bitcoin certificate to Italian retail',
                      '금융당국, 가상자산 거래소 1거래소 1은행 체제 유지',
                      '메타 스레드, 암호화폐·미국 주식 실시간 시세 기능 도입'):
            self.assertTrue(policy.scope(story(title)), title)

    def test_manual_history_blocks_all_known_examples_without_api(self):
        self.assertEqual(len(manual.EVENTS), 18)
        with patch.object(editor, '_call_openai') as api:
            for url, title, _ in manual.EVENTS:
                s = story(title, url)
                self.assertTrue(manual_post_reason(s), url)
                self.assertEqual(editor.build_message(s), '')
        api.assert_not_called()
        keys = {url_key(row['url']) for row in history_records({})}
        self.assertTrue(all(url_key(row[0]) in keys for row in manual.EVENTS))

    def test_new_scope_does_not_replay_old_or_undated_queue(self):
        for index in (2, 3, 7, 11, 12):
            for date in ('', 'bad', policy.ENABLED_AT.isoformat(), '2026-11-25T07:01:00'):
                s=story(manual.EVENTS[index][1]); s['pub']=date
                self.assertTrue(editor._is_hard_blocked(s)[0], (index, date))

    def test_rumor_and_existing_exclusions_remain(self):
        for title in ('Rumor: Nvidia about to buy $2.5 billion XRP',
                      'Sui launches USDC payment service',
                      'XRP Ledger critical vulnerability revealed'):
            self.assertTrue(editor._is_hard_blocked(story(title))[0], title)
        for title in ('XRPL daily DEX volume up 5%', 'XRP price target $50',
                      'Franklin Templeton Stellar price prediction'):
            self.assertFalse(policy.scope(story(title)), title)

    def test_source_constraints_and_readability_are_in_generation_and_review(self):
        prompt=editor._summary_prompt(manual.EVENTS[4][1], 'source')
        for term in ('만기', '매수까지 확대하지', '26%', '34%', '거래·중개 서비스',
                     '공식 확인', '• 불릿', '320자'):
            self.assertIn(term, prompt)

    def test_formatting_keeps_all_validated_conditions(self):
        body='유니크레딧이 비트코인 연계 증서를 출시함\n\n6년 만기 보유 시 원금 100%이며 수익은 최대 65%임\n\n최소 1000유로이며 자문 채널에서 판매됨'
        output=policy.readable_summary(editor._clean_summary(body))
        self.assertEqual(output.count('• '), 2)
        for term in ('6년', '만기', '100%', '65%', '1000유로', '자문 채널'):
            self.assertIn(term, output)
        bulleted='증서 출시\n\n• 조건 1\n\n• 조건 2\n\n• 조건 3\n\n• 만기 전 매도 제외\n\n추가 필수 조건'
        cleaned=editor._clean_summary(bulleted)
        self.assertIn('만기 전 매도 제외', cleaned)
        self.assertIn('추가 필수 조건', cleaned)

    def test_subject_asset_tags_and_no_usde_substring_collision(self):
        body='에테나가 스텔라에서 USDe와 sUSDe를 출시함'
        tagged,_=editor._inject_inline_tags(body, story('Ethena goes live on Stellar'))
        for tag in ('#에테나', '#스텔라', '#USDe', '#sUSDe'):
            self.assertIn(tag, tagged)
        self.assertNotIn('s#USDe', tagged)
        tagged,selected=editor._inject_inline_tags('유니크레디트가 원금보장 ETP를 통해 비트코인 투자를 지원함', story('UniCredit opens Bitcoin certificate'))
        for tag in ('#유니크레딧', '#원금보장', '#ETP', '#비트코인'):
            self.assertIn(tag, tagged)
        self.assertIn('#UniCredit', editor._build_footer_tags({},selected))

    def test_subject_image_wins_over_generic_rss_but_not_publisher_logo(self):
        s=story('UniCredit opens Bitcoin certificate'); s['image_url']='https://example.com/bitcoin.png'
        page=b'<meta property="og:image" content="/default.png"><article><img src="/asset.png" alt="UniCredit"><img src="https://tokenpost.kr/tokenpost-logo.png" alt="UniCredit"></article>'
        urls=images.image_candidates(s, lambda *args: page)
        self.assertEqual(urls[0], 'https://example.com/asset.png')
        self.assertFalse(any('tokenpost-logo' in url for url in urls))
        self.assertIn(s['image_url'], urls)

    def test_current_release_migrates_unrelated_cache_without_extending_expiry(self):
        m=json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text('utf8'))
        old=m['nov25_only_previous_identities'][0]
        with cache.review_session({}, lambda:None, logger=lambda _:None) as store:
            expiry=store.clock()+1000
            for kind,title,changed in (
                ('source_summary',manual.EVENTS[7][1],True),
                ('source_summary','Unchanged rejected article',False),
                ('source_summary','Nubank Secures Brazil Banking License',False),
                ('image_held',manual.EVENTS[4][1],False)):
                scope=dict(title=title,source='unchanged')
                key=cache.fingerprint([cache.VERSION,old,kind,scope])
                store.data.setdefault('content_results_v1',{})[key]={'result':{'summary':'','reason':'excluded'},'expires':expiry}
                result=cache.content_result(kind,scope)
                if changed:self.assertIsNone(result)
                else:self.assertEqual(result['reason'],'excluded')
            self.assertTrue(all(x['expires']==expiry for x in store.data['content_results_v1'].values()))


if __name__=='__main__':
    unittest.main()
