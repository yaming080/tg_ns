import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, Mock
import doorinews_editor as e
import news_nov8_scope as scope
import news_manual_nov8 as manual
import news_review_cache as cache
import news_event_review as events
from news_publication import prepare_publication


def story(title, url='https://example.com/new-article'):
    return dict(title=title, url=url, pub=max(datetime.now(timezone.utc), scope.ENABLED_AT+timedelta(seconds=1)).isoformat())


class Nov8FeedbackTests(unittest.TestCase):
    def test_team_types_and_bilingual_titles_reach_review(self):
        titles=[x[1] for x in manual.EVENTS]+[
            '"美 중간선거 당선자 69.5%는 \'親 가상자산\'…2024년보다 높아"',
            '69.5% of US Midterm Winners Classified as Pro-Crypto, Higher Than in 2024',
            '리플, 블랙록·스탠다드차타드와 토큰화 보고서 참여',
            'DFSA publishes Scaling Tokenisation white paper',
            'Fidelity’s Jurrien Timmer favors Bitcoin over gold amid sell-off',
            '피델리티 주리엔 팀머, 금보다 비트코인을 선호하는 이유 설명',
        ]
        for title in titles:
            with self.subTest(title=title):
                s=story(title)
                self.assertTrue(scope.scope(s))
                self.assertFalse(e._is_hard_blocked(s)[0],e._is_hard_blocked(s)[1])
                self.assertTrue(e.matches_keywords(s,[],[],[]))

    def test_team_posts_block_without_paid_calls_and_enter_event_history(self):
        with patch.object(e,'_call_openai') as api:
            for url,title,_ in manual.EVENTS:
                s=story(title,url+'?utm_source=telegram')
                self.assertIn('게시',e._is_hard_blocked(s)[1])
                self.assertEqual(e.build_message(s),'')
        api.assert_not_called()
        history=events.history_records({})
        for url,_,_ in manual.EVENTS:
            self.assertTrue(any(events.url_key(r['url'])==events.url_key(url) for r in history))

    def test_new_scope_does_not_release_old_queue(self):
        for _,title,_ in manual.EVENTS:
            for pub in ('bad','',scope.ENABLED_AT.isoformat()):
                s=story(title);s['pub']=pub
                self.assertTrue(e._is_hard_blocked(s)[0],(title,pub))

    def test_narrow_scope_and_existing_exclusions(self):
        for title in ('US midterm poll says crypto prices could rise',
                      'US election campaign crypto donations reach record high',
                      'Ripple attended tokenization conference with BlackRock',
                      'Anonymous trader prefers Bitcoin over gold',
                      'Fidelity Jurrien Timmer Bitcoin gold technical analysis price target',
                      'Ripple tokenization report sponsored giveaway'):
            self.assertFalse(scope.scope(story(title)),title)
        for title in ('Sui joins BlackRock in new tokenization report',
                      'XRP Ledger critical vulnerability revealed in Ripple tokenization report'):
            self.assertTrue(e._is_hard_blocked(story(title))[0],title)

    def test_scope_is_not_source_or_image_approval(self):
        title=manual.EVENTS[1][1]
        selector=Mock()
        result=prepare_publication(story(title),lambda _: '',None,'unused',selector=selector)
        self.assertEqual(result['status'],'held');selector.assert_not_called()
        required=('faithful','conditions_preserved','allowed_category','new_substantive_fact','source_sufficient','understandable')
        for failed in required:
            checks=dict.fromkeys(required,True);checks[failed]=False
            with patch.object(e,'_call_openai',return_value=json.dumps({'publish':False,'reason':'unverified','checks':checks})):
                self.assertFalse(e._validate_summary_against_source(title,'source','summary'))

    def test_guidance_preserves_report_opinion_and_classification(self):
        self.assertEqual(scope.guidance('Unrelated service launch'),'')
        for _,title,_ in manual.EVENTS:
            prompt=e._summary_prompt(title,'source')
            for text in ('보고서 발표·참여와 실제 제휴','개인 견해','분류 기관'):
                self.assertIn(text,prompt)
        tagged,_=e._inject_inline_tags('피델리티 주리엔 팀머가 금보다 비트코인을 선호하는 이유를 설명함',story(manual.EVENTS[2][1]))
        self.assertIn('#주리엔팀머',tagged)
        self.assertIn('#피델리티',tagged)

    def test_only_changed_types_invalidate_latest_cached_exclusions(self):
        m=json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text('utf8'))
        old=m['nov8_only_previous_identities'][0]
        with cache.review_session({},lambda:None,logger=lambda _:None) as store:
            expiry=store.clock()+1000
            samples=[(x[1],True) for x in manual.EVENTS]+[
                ('Gopax halts trading amid cyber threats',False),
                ('AWS unveils cloud architecture for crypto exchange custody',False),
                ('Unchanged excluded article',False)]
            for title,affected in samples:
                s={'title':title,'source':'unchanged'}
                key=cache.fingerprint([cache.VERSION,old,'source_summary',s])
                store.data.setdefault('content_results_v1',{})[key]={'result':{'summary':'','reason':'excluded'},'expires':expiry}
                result=cache.content_result('source_summary',s)
                if affected:self.assertIsNone(result)
                else:self.assertEqual(result['reason'],'excluded')
            self.assertEqual(store.calls,0)
            self.assertTrue(all(r['expires']==expiry for r in store.data['content_results_v1'].values()))
