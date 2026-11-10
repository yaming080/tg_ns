import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, Mock
import doorinews_editor as editor
import news_nov10_scope as scope
import news_manual_nov10 as manual
import news_event_review as events
import news_review_cache as cache
from news_publication import prepare_publication


def story(title, url='https://example.com/new-event'):
    return {'title':title, 'url':url,
            'pub':max(datetime.now(timezone.utc),scope.ENABLED_AT+timedelta(seconds=1)).isoformat()}


class Nov10FeedbackTests(unittest.TestCase):
    def test_real_missed_headlines_reach_review(self):
        titles=[row[1] for i,row in enumerate(manual.EVENTS) if i not in (5,6)]+[
            'PNC Bank tests turning USDC payments into dollar deposits',
            'Coinbase secures national trust bank charter from OCC',
            'Coinbase’s US national trust bank charter takes effect',
            'Robinhood opens access to US IPOs for UK retail investors',
            'Strategy buys 1,036 Bitcoin as BTC holdings climb to 850,364',
            'Bitmine Buys $20M in ETH as Tom Lee Hails Vitalik Buterin’s Store-of-Value Shift',
            '불리시, 전 NYSE 사장 스테이시 커닝햄 신임 사장으로 선임',
            '경찰청 압수 가상자산, 업비트 커스터디 위탁 보관',
            '警 압수 가상자산 ‘업비트 커스터디’ 위탁보관',
        ]
        for title in titles:
            with self.subTest(title=title):
                s=story(title)
                self.assertTrue(scope.scope(s))
                self.assertFalse(editor._is_hard_blocked(s)[0],editor._is_hard_blocked(s))
                self.assertTrue(editor.matches_keywords(s,[],[],[]))

    def test_manual_posts_block_before_any_paid_request(self):
        self.assertEqual(len(manual.EVENTS),12)
        with patch.object(editor,'_call_openai') as api:
            for url,title,_ in manual.EVENTS:
                s=story(title,url+'?utm_source=telegram&s=20')
                self.assertIn('게시',editor._is_hard_blocked(s)[1])
                self.assertEqual(editor.build_message(s),'')
        api.assert_not_called()
        history=events.history_records({})
        for url,_,_ in manual.EVENTS:
            self.assertTrue(any(events.url_key(row['url'])==events.url_key(url) for row in history))

    def test_no_stale_queue_or_unknown_dates_for_new_types(self):
        for i in (0,1,2,3,4,7,8,9,10):
            title=manual.EVENTS[i][1]
            for pub in ('bad','',scope.ENABLED_AT.isoformat()):
                s=story(title); s['pub']=pub
                self.assertTrue(editor._is_hard_blocked(s)[0],(title,pub))

    def test_keep_rumors_promotions_nonportfolio_and_simple_metrics_excluded(self):
        titles=[
            'Strategy may buy 1,036 Bitcoin next week',
            'Strategy hints at another 1,036 BTC purchase',
            'Strategy Bitcoin holdings hit 850,000 BTC',
            'Bitmine Ethereum price target $10,000',
            'PNC stablecoin payment referral giveaway',
            'Robinhood UK IPO access price prediction',
            'HTX launches sponsored tokenized stock trading',
            manual.EVENTS[6][1],
        ]
        for title in titles:
            self.assertFalse(scope.scope(story(title)),title)
        for title in ('Sui launches tokenized stocks via HTX',
                      'XRP Ledger critical vulnerability revealed',manual.EVENTS[6][1]):
            self.assertTrue(editor._is_hard_blocked(story(title))[0],title)
        sponsored=story(manual.EVENTS[0][1]); sponsored['article_text']='This is sponsored content.'
        self.assertIn('협찬',editor._is_hard_blocked(sponsored)[1])

    def test_intake_is_not_source_or_publication_approval(self):
        candidate=story(manual.EVENTS[3][1])
        image=Mock()
        result=prepare_publication(candidate,lambda _: '',None,'unused',selector=image)
        self.assertEqual(result['status'],'held'); image.assert_not_called()
        required=('faithful','conditions_preserved','allowed_category','new_substantive_fact','source_sufficient','understandable')
        for failed in required:
            checks=dict.fromkeys(required,True); checks[failed]=False
            with patch.object(editor,'_call_openai',return_value=json.dumps({'publish':False,'reason':'not verified','checks':checks})):
                self.assertFalse(editor._validate_summary_against_source(candidate['title'],'source','summary'))

    def test_guidance_separates_claims_stages_and_duplicate_purchases(self):
        prompt=editor._summary_prompt(manual.EVENTS[4][1],'source')
        for phrase in ('실제 거래와 개인 전망을 분리','새 보고기간의 독립된 거래','일반 상업은행','종전·협상 타결 확정이 아니다'):
            self.assertIn(phrase,prompt)

    def test_unchanged_semantic_exclusions_keep_original_expiry(self):
        manifest=json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text('utf8'))
        old=manifest['nov10_only_previous_identities'][0]
        with cache.review_session({},lambda:None,logger=lambda _:None) as store:
            expiry=store.clock()+1000
            for title,changed in [(manual.EVENTS[3][1],True),
                                  ('Ripple joins BlackRock in new tokenization report',False),
                                  ('Gopax halts trading amid cyber threats',False),
                                  ('Unchanged rejected article',False)]:
                s={'title':title,'source':'unchanged'}
                key=cache.fingerprint([cache.VERSION,old,'source_summary',s])
                store.data.setdefault('content_results_v1',{})[key]={'result':{'summary':'','reason':'excluded'},'expires':expiry}
                result=cache.content_result('source_summary',s)
                if changed: self.assertIsNone(result)
                else: self.assertEqual(result['reason'],'excluded')
            self.assertTrue(all(row['expires']==expiry for row in store.data['content_results_v1'].values()))


if __name__=='__main__':
    unittest.main()
