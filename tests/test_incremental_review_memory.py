"""Persistent local retrieval and paid-verdict reuse; all API responses mocked."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import news_event_review as events
import news_event_index as index
import news_review_cache as cache

def data(prompt):
    return json.loads(prompt[prompt.index('{"candidate"'):])

class IncrementalMemoryTests(unittest.TestCase):
    def setUp(self):
        self.state={'posted':{}}
        self.story=dict(title='Ripple launches payments',url='https://new.example/a',
                        _review_source_sha256='source-A')
        self.caption='Ripple launches payments in Korea after an earlier pilot'
        self.history={str(i):dict(title=f'Unrelated history {i}',url=f'https://old.example/{i}') for i in range(350)}
        self.history['match']=dict(title='Ripple payment pilot',url='https://old.example/match',summary='Ripple plans payments in Korea')
        self.client=Mock(); self.client.responses.create.side_effect=self.answer
        self.requests=[]; self.verdict='new'; self.now=1000000
        self.manual=patch.object(events,'MANUAL_EVENTS',()); self.manual.start(); self.addCleanup(self.manual.stop)

    def answer(self,**kwargs):
        prompt=kwargs['input']; self.requests.append(prompt)
        rows=data(prompt)['history']
        value=dict(decision=self.verdict,matched_id=rows[0]['id'],reason='Compare actor, business and stage',
                   new_fact='Actual launch after earlier pilot')
        return SimpleNamespace(status='completed',output_text=json.dumps(value),usage=None)

    def run_review(self,model='gpt-5.4'):
        original=cache.ReviewStore.__init__
        def init(store,state,persist,logger=print):
            original(store,state,persist,logger,clock=lambda:self.now)
        with patch.object(cache.ReviewStore,'__init__',init),cache.review_session(self.state,lambda:None,lambda s:None):
            result=events.review_event(self.story,self.caption,self.history,
                lambda p:cache.request_text(self.client,model,p),review_identity=model)
        self.state=json.loads(json.dumps(self.state))
        return result

    def test_restart_reuses_index_and_paid_result_without_touching_posted(self):
        self.assertEqual(self.run_review()['status'],'new')
        with patch.object(index,'feature',wraps=index.feature) as build:
            self.assertEqual(self.run_review()['status'],'new')
            self.assertEqual(build.call_count,1) # candidate only, history persisted
        self.assertEqual(self.client.responses.create.call_count,1)
        self.assertEqual(len(data(self.requests[0])['history']),1)
        self.assertEqual(self.state['posted'],{})

    def test_unrelated_append_builds_only_new_feature_and_reuses_verdict(self):
        self.run_review(); self.requests.clear()
        self.history['extra']=dict(title='Unrelated new history',url='https://other.example/extra')
        with patch.object(index,'feature',wraps=index.feature) as build:
            self.run_review(); self.assertEqual(build.call_count,2)
        self.assertEqual(self.requests,[])

    def test_related_append_rechecks_only_related_records(self):
        self.run_review(); self.requests.clear()
        self.history['extra']=dict(title='Ripple payment agreement',url='https://other.example/extra')
        self.run_review()
        self.assertEqual(len(self.requests),1)
        self.assertEqual(len(data(self.requests[0])['history']),2)

    def test_changed_full_evidence_beyond_old_excerpt_is_rechecked(self):
        self.history['match']['summary']='Ripple payments '+('x'*700)+' old'
        self.run_review(); self.requests.clear()
        self.history['match']['summary']='Ripple payments '+('x'*700)+' new'
        self.run_review()
        self.assertEqual(len(self.requests),1)
        self.assertTrue(data(self.requests[0])['history'][0]['summary'].endswith('new'))

    def test_source_caption_and_model_changes_recheck_only_related_record(self):
        self.run_review()
        for change in ('source','caption','model'):
            self.requests.clear()
            if change=='source': self.story['_review_source_sha256']='source-B'
            if change=='caption': self.caption+=' New separate contract.'
            self.run_review('different-model' if change=='model' else 'gpt-5.4')
            self.assertEqual(len(self.requests),1)
            self.assertEqual(len(data(self.requests[0])['history']),1)

    def test_confirmed_duplicate_remembered_even_after_raw_cache_eviction(self):
        self.verdict='duplicate'; self.assertEqual(self.run_review()['status'],'duplicate')
        self.requests.clear(); self.state['ai_review']['entries']={}
        self.history['extra']=dict(title='Other business',url='https://old.example/extra')
        self.assertEqual(self.run_review()['status'],'duplicate')
        self.assertEqual(self.requests,[])

    def test_changed_or_removed_duplicate_evidence_does_not_keep_blocking(self):
        self.verdict='duplicate'; self.run_review(); self.requests.clear()
        self.history['match']['summary']='Ripple now launches payments in Korea'
        self.verdict='update'
        self.assertEqual(self.run_review()['status'],'update'); self.assertTrue(self.requests)
        del self.history['match']; self.requests.clear()
        self.assertEqual(self.run_review()['status'],'new'); self.assertEqual(self.requests,[])

    def test_new_fact_after_duplicate_rechecks(self):
        self.verdict='duplicate'; self.run_review(); self.requests.clear()
        self.story['_review_source_sha256']='confirmed-new-launch'
        self.caption+=' New country launch confirmed.'; self.verdict='update'
        self.assertEqual(self.run_review()['status'],'update'); self.assertTrue(self.requests)

    def test_invalid_verdict_is_not_cached_as_checked(self):
        self.client.responses.create.side_effect=None
        self.client.responses.create.return_value=SimpleNamespace(status='completed',output_text='{}',usage=None)
        self.assertEqual(self.run_review()['status'],'hold')
        self.client.responses.create.side_effect=self.answer
        self.assertEqual(self.run_review()['status'],'new')
        self.assertEqual(self.client.responses.create.call_count,2)

    def test_uncertain_result_reused_until_evidence_or_durable_ttl_changes(self):
        self.verdict='uncertain'; self.assertEqual(self.run_review()['status'],'hold')
        self.requests.clear(); self.now+=cache.NEGATIVE_TTL+1
        self.assertEqual(self.run_review()['status'],'hold'); self.assertEqual(self.requests,[])
        self.story['_review_source_sha256']='new-evidence'; self.run_review()
        self.assertTrue(self.requests)

    def test_index_policy_rebuilds_locally_without_invalidating_identical_paid_prompt(self):
        self.run_review(); self.requests.clear()
        with patch.object(index,'INDEX_VERSION','new-index-policy'),patch.object(index,'feature',wraps=index.feature) as build:
            self.run_review(); self.assertEqual(build.call_count,len(self.history)+1)
        self.assertEqual(self.requests,[])

    def test_cache_policy_and_expiry_require_new_paid_verdict(self):
        self.run_review(); self.requests.clear()
        self.now+=cache.MEMORY_TTL+1; self.run_review(); self.assertTrue(self.requests)
        self.requests.clear()
        with patch.object(cache,'VERSION','new-cache-policy'): self.run_review()
        self.assertTrue(self.requests)

    def test_legacy_pair_ledger_retired_without_deleting_posted_or_usage(self):
        self.run_review()
        self.state['ai_review']['event_memory_v33']['old']={'expires':self.now+10000,'value':{'checked':{'old':'hash'}}}
        self.run_review()
        self.assertNotIn('old',self.state['ai_review']['event_memory_v33'])
        self.assertEqual(len(self.state['ai_review']['local_event_index']['entries']),len(self.history))

class DurableResultsTests(unittest.TestCase):
    def test_same_rejected_source_and_image_are_reused_after_seven_hours(self):
        state={}; clock=Mock(return_value=1000); client=Mock()
        client.responses.create.return_value=SimpleNamespace(status='completed',
            output_text='{"approved":false,"reason":"wrong subject"}',usage=None)
        store=cache.ReviewStore(state,lambda:None,lambda s:None,clock)
        for stage in ('summary','source_review','image_review'):
            for now in (1000,1000+7*3600):
                clock.return_value=now
                store.request(client,'gpt-5.4','same full request',stage,'same-source',lambda t:bool(t))
        self.assertEqual(client.responses.create.call_count,3)

    def test_new_image_is_checked_without_repeating_old_image(self):
        state={}; client=Mock()
        client.responses.create.return_value=SimpleNamespace(status='completed',
            output_text='{"approved":false}',usage=None)
        with cache.review_session(state,lambda:None,lambda s:None):
            for image in ('old-image','old-image','new-image'):
                cache.request_text(client,'gpt-5.4',{'image':image},stage='image_review')
        self.assertEqual(client.responses.create.call_count,2)
