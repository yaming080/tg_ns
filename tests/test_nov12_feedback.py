import json
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch, Mock

import doorinews_editor as editor
import news_nov12_scope as scope
import news_manual_nov12 as manual
import news_event_review as events
import news_review_cache as cache
import news_sources as sources
from news_publication import prepare_publication


def story(title, url='https://example.com/future-article'):
    return {'title': title, 'url': url,
            'pub': (scope.ENABLED_AT + timedelta(minutes=1)).isoformat()}


class Nov12FeedbackTests(unittest.TestCase):
    def test_reported_types_and_real_feed_variants_reach_review(self):
        titles = [row[1] for row in manual.EVENTS] + [
            'Nomura weighs Laser Digital sale months after securing Japan crypto license',
            'Nomura explores sale of crypto unit Laser Digital: Bloomberg',
            'Texas Bill Would Allow Cities, Counties to Invest $10M in Crypto',
            '리플 APAC 이은진 이사, 2030년 30조달러 자산 온체인 이동 전망',
            '금융위, 가상자산 해킹 의심 시 출금 정지 허용',
            'Hyun Song Shin appointed chair of CPMI',
        ]
        for title in titles:
            s = story(title)
            self.assertTrue(scope.scope(s), title)
            self.assertFalse(editor._is_hard_blocked(s)[0], (title, editor._is_hard_blocked(s)))
            self.assertTrue(editor.matches_keywords(s, [], [], []), title)

    def test_all_eight_manual_posts_block_before_paid_calls(self):
        self.assertEqual(len(manual.EVENTS), 8)
        with patch.object(editor, '_call_openai') as api:
            for url, title, _ in manual.EVENTS:
                s = story(title, url + '?utm_source=telegram&s=20')
                self.assertIn('게시', editor._is_hard_blocked(s)[1])
                self.assertEqual(editor.build_message(s), '')
        api.assert_not_called()
        history = events.history_records({})
        for url, _, _ in manual.EVENTS:
            self.assertTrue(any(events.url_key(row['url']) == events.url_key(url) for row in history))

    def test_newly_admitted_old_and_undated_articles_do_not_replay(self):
        for i in (0, 1, 4, 5, 7):
            for pub in ('', 'bad', scope.ENABLED_AT.isoformat(), '2026-11-12T12:46:00'):
                s = story(manual.EVENTS[i][1]); s['pub'] = pub
                self.assertTrue(editor._is_hard_blocked(s)[0], (i, pub))

    def test_attributed_uncertainty_survives_final_format_gate(self):
        s = story('Nomura weighs Laser Digital sale months after securing Japan crypto license')
        summary = '노무라가 레이저디지털 매각을 검토 중이라고 블룸버그가 보도했으며, 매각 여부는 아직 확정되지 않음'
        with patch.object(editor, '_rewrite_summary', return_value=summary):
            caption = editor.build_message(s)
        self.assertTrue(caption)
        self.assertIn('확정되지', caption)
        self.assertIn('#노무라', caption)

    def test_promotions_price_targets_and_protocol_harm_stay_excluded(self):
        for title in ('Ripple onchain assets price target $10', 'Nomura crypto sale rumor',
                      '신현송 경제 전망', '국회 기본법 행사 참석', 'Bitcoin price prediction'):
            self.assertFalse(scope.scope(story(title)), title)
        for title in ('Sui launches new payment platform with USDC',
                      'XRP Ledger critical vulnerability revealed'):
            self.assertTrue(editor._is_hard_blocked(story(title))[0], title)
        s = story(manual.EVENTS[1][1]); s['article_text'] = 'This is sponsored content.'
        self.assertIn('협찬', editor._is_hard_blocked(s)[1])

    def test_guidance_preserves_stages_and_unsupported_xrp_claims(self):
        prompt = editor._summary_prompt(manual.EVENTS[3][1], 'source')
        for text in ('37개 은행 전체가 리플과 새 제휴한 것이 아니다',
                     'XRP 채택·제휴·가격 상승을 추론', '매각 미확정',
                     '단순 조속 추진 재확인', '같은 법안이라는 이유만으로'):
            self.assertIn(text, prompt)
        candidate = story(manual.EVENTS[4][1]); image = Mock()
        result = prepare_publication(candidate, lambda _: '', None, 'unused', selector=image)
        self.assertEqual(result['status'], 'held'); image.assert_not_called()
        checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                               'new_substantive_fact', 'source_sufficient', 'understandable'), True)
        for failed in checks:
            verdict = dict(checks); verdict[failed] = False
            with patch.object(editor, '_call_openai', return_value=json.dumps(
                    {'publish': False, 'checks': verdict, 'reason': 'unverified'})):
                self.assertFalse(editor._validate_summary_against_source(candidate['title'], 'source', 'summary'))

    def test_hankyung_first_fetch_is_silent_and_x_not_added(self):
        feed = 'https://www.hankyung.com/feed/economy'
        self.assertIn(feed, [url for _, url in sources.NEW_FEEDS])
        self.assertFalse(any('x.com' in url for _, url in sources.NEW_FEEDS))
        state = {}; old = story(manual.EVENTS[7][1], manual.EVENTS[7][0])
        now = scope.ENABLED_AT + timedelta(minutes=2)
        self.assertEqual(sources.after_baseline(state, feed, [old], now), [])
        new = dict(old, url='https://www.hankyung.com/article/new', pub=(now + timedelta(minutes=1)).isoformat())
        self.assertEqual(sources.after_baseline(state, feed, [old, new], now + timedelta(minutes=2)), [new])

    def test_cache_migrates_unchanged_card_and_other_decisions(self):
        manifest = json.loads((Path(cache.__file__).parent / 'news_cache_compatibility.json').read_text('utf8'))
        old = manifest['nov12_only_previous_identities'][0]
        with cache.review_session({}, lambda: None, logger=lambda _: None) as store:
            expiry = store.clock() + 1000
            for title, changed in ((manual.EVENTS[0][1], True), (manual.EVENTS[1][1], True),
                                   ('신한카드 "스테이블코인 결제, 초기에는 기존 카드망 활용할 수도"', False),
                                   ('Unchanged rejected article', False)):
                s = {'title': title, 'source': 'unchanged'}
                key = cache.fingerprint([cache.VERSION, old, 'source_summary', s])
                store.data.setdefault('content_results_v1', {})[key] = {
                    'result': {'summary': '', 'reason': 'excluded'}, 'expires': expiry}
                result = cache.content_result('source_summary', s)
                if changed: self.assertIsNone(result)
                else: self.assertEqual(result['reason'], 'excluded')
            self.assertTrue(all(row['expires'] == expiry for row in store.data['content_results_v1'].values()))


if __name__ == '__main__':
    unittest.main()
