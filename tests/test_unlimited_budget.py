import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import news_review_cache as cache
import news_manual_nov10 as manual
from news_budget import BudgetLedger
from news_resume import configure_resume_boundary, resume_exclusion_reason


class UnlimitedBudgetTests(unittest.TestCase):
    def test_unlimited_allows_review_above_old_cap_and_keeps_accounting_and_cache(self):
        state={}; persist=Mock(); client=Mock()
        client.responses.create.return_value=NS(output_text='reviewed',status='completed',
            usage=NS(input_tokens=1000,output_tokens=100,input_tokens_details=NS(cached_tokens=0,cache_write_tokens=0)))
        with patch.dict(os.environ,{'NEWS_MONTHLY_API_BUDGET_USD':'unlimited'}),cache.review_session(state,persist,logger=lambda _:None) as store:
            ledger=BudgetLedger(store)
            store.usage[ledger.month+'-01']={'old':{'summary':{'estimated_usd':200.0}}}
            self.assertIsNone(ledger.limit)
            for _ in range(2):
                self.assertEqual(cache.request_text(client,'gpt-6-luna','same story',stage='source_review'),'reviewed')
            self.assertGreater(ledger.spent(),200)
            self.assertFalse(store.data['budget_reservations_v1'])
            self.assertEqual(store.calls,1)
        self.assertEqual(client.responses.create.call_count,1)
        self.assertEqual(client.responses.create.call_args.kwargs['model'],'gpt-6.1-sol')
        self.assertGreater(persist.call_count,0)

    def test_default_is_unlimited_but_bad_numeric_config_still_fails_closed(self):
        with patch.dict(os.environ,{},clear=True),cache.review_session({},lambda:None,logger=lambda _:None) as store:
            self.assertIsNone(BudgetLedger(store).limit)
            for value in ('0','-1','nan','inf','bad'):
                with patch.dict(os.environ,{'NEWS_MONTHLY_API_BUDGET_USD':value}):
                    self.assertEqual(BudgetLedger(store).limit,0)

    def test_unlimited_does_not_drop_unknown_usage_reservations_or_validation(self):
        with patch.dict(os.environ,{'NEWS_MONTHLY_API_BUDGET_USD':'unlimited'}),cache.review_session({},lambda:None,logger=lambda _:None) as store:
            ledger=BudgetLedger(store)
            ticket=ledger.reserve('r','gpt-6-luna','input',cache.request_options('gpt-6-luna'),cache.PRICES['gpt-6-luna'])
            self.assertTrue(ticket)
            ledger.settle(ticket,None)
            self.assertIn(ticket,ledger.pending)
            self.assertIsNone(ledger.reserve('bad','unsupported','input',{},(1,1,1)))

    def test_existing_editorial_outcomes_migrate_without_paid_recheck(self):
        m=json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text('utf8'))
        old=m['operational_only_previous_identities'][-1]
        with cache.review_session({},lambda:None,logger=lambda _:None) as store:
            expiry=store.clock()+1000
            for _,title,_ in manual.EVENTS:
                s={'title':title,'source':'unchanged'}
                key=cache.fingerprint([cache.VERSION,old,'source_summary',s])
                store.data.setdefault('content_results_v1',{})[key]={'result':{'summary':'','reason':'previous exclusion'},'expires':expiry}
                self.assertEqual(cache.content_result('source_summary',s)['reason'],'previous exclusion')
            self.assertTrue(all(row['expires']==expiry for row in store.data['content_results_v1'].values()))
            self.assertEqual(store.calls,0)

    def test_fresh_boundary_is_saved_and_survives_older_environment(self):
        state={'posted':{'old':{'title':'Already posted'}}}
        with patch.dict(os.environ,{'NEWS_PUBLISH_NOT_BEFORE_UTC':'2026-11-10T08:20:00Z'}):
            configure_resume_boundary(state)
            self.assertEqual(state['publish_not_before_utc'],'2026-11-10T08:20:00+00:00')
            self.assertTrue(resume_exclusion_reason({'pub':'2026-11-10T08:19:59Z'}))
            self.assertFalse(resume_exclusion_reason({'pub':'2026-11-10T08:20:01Z'}))
        with patch.dict(os.environ,{'NEWS_PUBLISH_NOT_BEFORE_UTC':'2026-11-07T00:00:00Z'}):
            configure_resume_boundary(state)
            self.assertTrue(resume_exclusion_reason({'pub':'2026-11-10T08:19:59Z'}))
        self.assertEqual(state['posted'],{'old':{'title':'Already posted'}})

    def test_both_live_entrypoints_use_unlimited_with_same_fresh_boundary(self):
        root=Path(cache.__file__).parent
        for name in ('news-bot.yml','news-single-test.yml'):
            workflow=(root/'.github/workflows'/name).read_text('utf8')
            self.assertIn('NEWS_MONTHLY_API_BUDGET_USD: "unlimited"',workflow)
            self.assertIn('NEWS_PUBLISH_NOT_BEFORE_UTC: "2026-11-10T08:20:00+00:00"',workflow)


if __name__=='__main__':
    unittest.main()
