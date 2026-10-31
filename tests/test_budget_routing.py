import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import news_review_cache as cache
from news_budget import BudgetLedger, maximum_request_usd


def response(text='ok',usage=True):
    return NS(output_text=text,status='completed',usage=NS(input_tokens=1000,output_tokens=100,
        input_tokens_details=NS(cached_tokens=200,cache_write_tokens=500)) if usage else None)


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'NEWS_MONTHLY_API_BUDGET_USD':'28'})
        self.env.start();self.addCleanup(self.env.stop)
        self.persist=Mock()
        self.state={}
        self.client=Mock()
        self.client.responses.create.return_value=response()

    def test_stage_routing_and_exact_reuse(self):
        with cache.review_session(self.state,self.persist,logger=lambda _:None):
            for stage in ('summary','source_review','event_search','event_decision','image_review'):
                for _ in range(2):cache.request_text(self.client,'gpt-6-luna',stage,stage=stage)
        self.assertEqual(self.client.responses.create.call_count,5)
        self.assertEqual([c.kwargs['model'] for c in self.client.responses.create.call_args_list],
                         ['gpt-6-luna','gpt-6.1-sol','gpt-6-luna','gpt-6.1-sol','gpt-6-luna'])
        self.assertFalse(self.state['ai_review']['budget_reservations_v1'])

    def test_cache_remains_available_when_budget_is_zero(self):
        with cache.review_session(self.state,self.persist,logger=lambda _:None):
            self.assertEqual(cache.request_text(self.client,'gpt-6-luna','a'),'ok')
            with patch.dict(os.environ,{'NEWS_MONTHLY_API_BUDGET_USD':'0'}):
                self.assertEqual(cache.request_text(self.client,'gpt-6-luna','a'),'ok')
                self.assertEqual(cache.request_text(self.client,'gpt-6-luna','new'),'')
        self.assertEqual(self.client.responses.create.call_count,1)
        self.assertEqual(self.state['ai_review']['recent_runs'][-1]['status'],'completed')

    def test_unknown_failure_is_reserved_but_does_not_blacklist_recovery(self):
        def timeout(**kw):
            self.assertTrue(self.state['ai_review']['budget_reservations_v1'])
            self.assertGreater(self.persist.call_count,0)
            raise TimeoutError('response unknown')
        self.client.responses.create.side_effect=timeout
        with cache.review_session(self.state,self.persist,logger=lambda _:None):
            with self.assertRaises(TimeoutError):cache.request_text(self.client,'gpt-6-luna','a')
        self.client.responses.create.side_effect=None
        self.client.responses.create.return_value=response()
        with cache.review_session(self.state,self.persist,logger=lambda _:None):
            self.assertEqual(cache.request_text(self.client,'gpt-6-luna','a'),'ok')
        self.assertEqual(self.client.responses.create.call_count,2)
        self.assertEqual(len(self.state['ai_review']['budget_reservations_v1']),1)

    def test_missing_usage_retains_reservation(self):
        self.client.responses.create.return_value=response(usage=False)
        with cache.review_session(self.state,self.persist,logger=lambda _:None):
            cache.request_text(self.client,'gpt-6-luna','a')
        self.assertTrue(self.state['ai_review']['budget_reservations_v1'])

    def test_current_month_cost_and_reservations_limit_new_calls(self):
        store=cache.ReviewStore({},lambda:None,logger=lambda _:None,
            clock=lambda:datetime(2026,11,1,tzinfo=timezone.utc).timestamp())
        store.usage.update({'2026-10-31':{'m':{'s':{'estimated_usd':100}}},
                            '2026-11-01':{'m':{'s':{'estimated_usd':27.99}}}})
        ledger=BudgetLedger(store)
        self.assertAlmostEqual(ledger.spent(),27.99)
        self.assertIsNone(ledger.reserve('x','gpt-6.1-sol','a',cache.request_options('gpt-6.1-sol'),cache.PRICES['gpt-6.1-sol']))

    def test_zero_invalid_and_nonfinite_budget_fail_closed(self):
        for raw in ['0','oops','nan','inf','-1']:
            with patch.dict(os.environ,{'NEWS_MONTHLY_API_BUDGET_USD':raw}),cache.review_session({},lambda:None,logger=lambda _:None):
                self.assertEqual(cache.request_text(self.client,'gpt-6-luna','a'),'')
        self.client.responses.create.assert_not_called()

    def test_sol_cache_write_cost_and_output_not_double_counted(self):
        store=cache.ReviewStore({},lambda:None,logger=lambda _:None)
        row=store.bucket('gpt-6.1-sol','source_review')
        cost=store.record_usage(response(),'gpt-6.1-sol','source_review',row)
        self.assertAlmostEqual(cost,.00287)
        self.assertEqual(row['cache_write_tokens'],500)

    def test_image_bound_does_not_depend_on_compressed_byte_size(self):
        opts=cache.request_options('gpt-6-luna')
        price=maximum_request_usd('gpt-6-luna',[{'type':'input_image','image_url':'data:image/png;base64,x'}],opts,cache.PRICES['gpt-6-luna'])
        self.assertGreater(price,.52)
        self.assertLess(price,1)

    def test_model_downgrade_never_bypasses_source_review(self):
        with patch.dict(os.environ,{'NEWS_MONTHLY_API_BUDGET_USD':'0'}),cache.review_session({},lambda:None,logger=lambda _:None):
            result=cache.request_text(self.client,'gpt-6-luna','a',stage='source_review')
            self.assertEqual(result,'')
        self.client.responses.create.assert_not_called()

    def test_approved_previous_release_outcome_migrates_without_api_or_ttl_extension(self):
        old='ac4043d670ade556c4b7ed76478e4079f903a6313820d28c8aafb2327b49f8eb'
        scope={'source':'unchanged','model':'gpt-6-luna'}
        with cache.review_session({},lambda:None,logger=lambda _:None) as store:
            expires=store.clock()+1000
            key=cache.fingerprint([cache.VERSION,old,'source_summary',scope])
            store.data['content_results_v1']={key:{'result':{'summary':''},'expires':expires}}
            cache.compatible_identity.cache_clear()
            self.assertEqual(cache.content_result('source_summary',scope),{'summary':''})
            self.assertEqual(next(iter(store.data['content_results_v1'].values()))['expires'],expires)
            self.assertEqual(store.calls,0)

    def test_mixed_policy_cannot_migrate_previous_verdict(self):
        cache.compatible_identity.cache_clear()
        with patch.object(cache,'editorial_identity',return_value='changed-editorial-policy'):
            self.assertIsNone(cache.compatible_identity())
        cache.compatible_identity.cache_clear()

if __name__=='__main__':unittest.main()
