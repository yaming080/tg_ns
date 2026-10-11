import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import doorinews_editor as e
import news_coverage as c
import news_public_interest as p
import news_manual_oct12 as manual
import news_event_review as events
import news_review_cache as cache
from news_publication import prepare_publication

TITLES = (
    '"코인 지갑 찾았는데"…가짜 렛저 웹사이트 구글 상단에 버젓이',
    'Japan arrests 6 over $580K crypto laundering case',
    'Russia’s new mining rules: Can Bitcoin miners lose power?',
    '"中, 국가 차원 블록체인 네트워크 구축 추진"',
)


def story(title=TITLES[0], **extra):
    return dict(title=title, url='https://example.com/new-event',
                pub=datetime.now(timezone.utc).isoformat(), **extra)


class PublicInterestTests(unittest.TestCase):
    def test_four_missed_titles_reach_source_review_for_new_stories(self):
        for title in TITLES:
            with self.subTest(title=title):
                self.assertTrue(p.public_interest_scope(story(title)))
                self.assertFalse(e._is_hard_blocked(story(title))[0])
                self.assertTrue(e.matches_keywords(story(title), [], [], []))

    def test_scope_works_across_languages(self):
        for title in ('Fake Ledger websites appear atop Google search results',
                      '일본 경찰, 암호화폐 자금세탁 혐의 6명 체포',
                      '러시아 정부, 채굴 시설 전력 연결 새 규정 도입',
                      'China plans national blockchain network in digital push',
                      'Chinese Communist Party Calls for a National Blockchain Network'):
            with self.subTest(title=title):
                self.assertTrue(e.matches_keywords(story(title), [], [], []))

    def test_only_newly_published_stories_enter_expanded_scope(self):
        for title in TITLES:
            for value in ('', 'bad date', p.ENABLED_AT.isoformat(),
                          (p.ENABLED_AT-timedelta(seconds=1)).isoformat()):
                s=story(title); s['pub']=value
                self.assertTrue(e._is_hard_blocked(s)[0], (title,value))
        s=story(); s['pub']=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
        self.assertTrue(e._is_hard_blocked(s)[0])

    def test_user_confirmed_four_posts_never_call_model_or_repost(self):
        with patch.object(e, '_call_openai') as api:
            for url, title, _ in manual.EVENTS:
                for variant in (url, url+'?utm_source=rss', url.rstrip('/')+'/'):
                    s=story(title); s['url']=variant
                    self.assertIn('게시', e._is_hard_blocked(s)[1])
                    self.assertEqual(e.build_message(s), '')
        api.assert_not_called()

    def test_negative_portfolio_and_outside_platform_still_precede_expansion(self):
        for title in ('XRP Ledger critical vulnerability patched',
                      "Bitcoin treasury companies get two Anchorage routes into Sui's Hashi",
                      'Sui launches national blockchain network with China government',
                      'Bitcoin network outage after new Russia mining power rules'):
            self.assertTrue(e._is_hard_blocked(story(title))[0],title)

    def test_no_blanket_security_mining_or_blockchain_allowance(self):
        titles=(
            'Coldcard hardware wallet vulnerability exposes Bitcoin seed phrases',
            'How to avoid fake Ledger websites: general wallet safety tips',
            'Crypto fraud annual losses report',
            'Kazakhstan miner electricity fee rises',
            'Russia Bitcoin mining profitability and electricity price comparison',
            'China blockchain startup launches sponsored giveaway',
            'Japan arrests 6 in tax case unrelated to digital assets',
            'Analyst Bitcoin price prediction after Russia new mining power rules',
        )
        for title in titles:
            with self.subTest(title=title):
                self.assertFalse(p.public_interest_scope(story(title)))
                self.assertFalse(e.matches_keywords(story(title), [], [], []))

    def test_publication_does_not_bypass_source_and_image_gates(self):
        s=story(TITLES[2]); selector=Mock()
        result=prepare_publication(s,lambda _: '',None,'unused',selector=selector)
        self.assertEqual(result['status'],'held')
        selector.assert_not_called()
        selector=Mock(return_value=(None, []))
        caption='러시아가 채굴 시설의 신규 전력 연결 규정을 도입했다고 밝힘\n\n🌐 <a href="https://t.me/Doorinews">도리뉴스</a>\n\n<a href="https://example.com/new-event">출처</a>\n\n'+' '.join(e.FIXED_FOOTER_TAGS)
        result=prepare_publication(s,lambda _:caption,None,'unused',selector=selector)
        self.assertNotEqual(result['status'],'ready')

    def test_cross_language_duplicate_review_includes_all_four_manual_events(self):
        records=events.history_records({})
        for url,_,_ in manual.EVENTS:
            self.assertTrue(any(r['url']==url for r in records))
        prompts=[]
        def model(prompt):
            prompts.append(prompt)
            payload=json.loads(prompt[prompt.index('{"candidate"'):])
            if 'related_ids' in prompt:
                ids=[r['id'] for r in payload['history'] if '국가 차원 블록체인' in r['title']]
                return json.dumps({'related_ids':ids})
            return json.dumps(dict(decision='duplicate', matched_id=payload['history'][0]['id'],
                                   reason='매체가 다르지만 같은 중국 국가 네트워크 계획', new_fact=''))
        result=events.review_event(story('China plans national blockchain network'),
                                   '중국이 국가 블록체인 네트워크 구축 계획을 발표했다고 밝힘',{},model)
        self.assertEqual(result['status'],'duplicate')

    def test_policy_change_invalidates_rejected_summary_cache(self):
        scopes=[]
        with patch.object(e,'repair_memory',side_effect=lambda s:scopes.append(s) or {'summary':''}):
            self.assertEqual(e._rewrite_summary(story(TITLES[1],article_text='New arrests reported by police.')),'')
        self.assertIn(c.POLICY,scopes[0]['policy'])

    def test_source_review_can_reject_stale_or_unverified_event(self):
        for failed in ('source_sufficient','new_substantive_fact','allowed_category'):
            checks=dict.fromkeys(('faithful','conditions_preserved','allowed_category',
                                 'new_substantive_fact','source_sufficient','understandable'),True)
            checks[failed]=False
            prompts=[]
            replies=iter(['러시아가 채굴 전력 규정을 도입했다고 밝힘',json.dumps(dict(publish=False,checks=checks,reason='근거 불충분'))])
            with patch.object(e,'_RUNTIME',{}),patch.object(e,'_call_openai',side_effect=lambda prompt:prompts.append(prompt) or next(replies)) as api:
                with cache.review_session({},lambda:None,logger=lambda *_:None):
                    self.assertEqual(e._rewrite_summary(story(TITLES[2],article_text='An old regulation explained without a new official action.')),'')
                self.assertEqual(api.call_count,2)
            self.assertTrue(all('2026-10-12 운영자 보완' in text for text in prompts))


if __name__=='__main__': unittest.main()
