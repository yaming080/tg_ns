"""Repeat-run regressions with mocked verdicts: no live API or posting."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import news_event_review as events
import news_review_cache as cache


def data(prompt):
    return json.loads(prompt[prompt.index('{"candidate"'):])


class IncrementalMemoryTests(unittest.TestCase):
    def setUp(self):
        self.state = {'posted':{}}
        self.story = dict(title='New payment launch',url='https://new.example/a',
                          pub='2026-10-06T00:00:00Z',_review_source_sha256='source-A')
        self.caption = 'Company launches payments in a separate country'
        self.history = {str(i):dict(title=f'Company {i} project',url=f'https://old.example/{i}',
                                   summary=f'Confirmed project {i}') for i in range(350)}
        self.client = Mock()
        self.client.responses.create.side_effect = self.answer
        self.requests=[]
        self.verdict='new'
        self.now=1000000

    def answer(self, **kwargs):
        p=kwargs['input']; self.requests.append(p)
        rows=data(p)['history']
        if '"related_ids"' in p:
            value={'related_ids':[r['id'] for r in rows if 'MATCH' in r.get('summary','')]}
        else:
            value={'decision':self.verdict,'matched_id':rows[0]['id'],
                   'reason':'Compare subject, action and stage',
                   'new_fact':'Confirmed new launch after the earlier plan'}
        return SimpleNamespace(status='completed',output_text=json.dumps(value),usage=None)

    def run_review(self, model='gpt-5.4'):
        with patch.object(cache.time,'time',return_value=self.now):
            # ReviewStore's default clock is bound at definition time.
            original=cache.ReviewStore.__init__
            def init(store,state,persist,logger=print):
                original(store,state,persist,logger,clock=lambda:self.now)
            with patch.object(cache.ReviewStore,'__init__',init):
                with cache.review_session(self.state,lambda:None,lambda s:None):
                    result=events.review_event(self.story,self.caption,self.history,
                        lambda p:cache.request_text(self.client,model,p),review_identity=model)
        self.state=json.loads(json.dumps(self.state))
        return result

    def test_restart_unchanged_article_does_not_call_api(self):
        self.assertEqual(self.run_review()['status'],'new')
        calls=self.client.responses.create.call_count
        self.run_review()
        self.assertEqual(self.client.responses.create.call_count,calls)
        self.assertEqual(self.state['ai_review']['recent_runs'][-1]['event_records_reviewed'],0)
        self.assertEqual(self.state['posted'],{})

    def test_appended_record_only_is_sent_not_its_old_bucket(self):
        self.run_review(); self.requests.clear()
        self.history['extra']=dict(title='New company announcement',url='https://old.example/new',summary='New facts')
        self.run_review()
        self.assertEqual(len(self.requests),1)
        self.assertEqual([r['title'] for r in data(self.requests[0])['history']],['New company announcement'])
        self.assertEqual(self.state['ai_review']['recent_runs'][-1]['event_records_reviewed'],1)

    def test_changed_full_record_beyond_excerpt_is_rechecked(self):
        self.history['0']['summary']='x'*700+'original fact'
        self.run_review(); self.requests.clear()
        self.history['0']['summary']='x'*700+'changed fact'
        self.run_review()
        self.assertEqual(len(self.requests),1)
        self.assertEqual(len(data(self.requests[0])['history']),1)
        self.assertEqual(data(self.requests[0])['history'][0]['title'],'Company 0 project')

    def test_changed_candidate_source_caption_and_model_invalidate_memory(self):
        self.run_review()
        for change in ('source','caption','model'):
            with self.subTest(change=change):
                self.requests.clear()
                if change=='source': self.story['_review_source_sha256']='source-B'
                if change=='caption': self.caption+=' New confirmed contract.'
                self.run_review(model='different-model' if change=='model' else 'gpt-5.4')
                sent=sum(len(data(p)['history']) for p in self.requests)
                self.assertEqual(sent,len(events.history_records(self.history)))

    def test_same_excerpt_cannot_reuse_comparison_after_full_evidence_changes(self):
        self.history={'one':dict(title='Record',url='https://old.example/one',summary='x'*700+'old')}
        with patch.object(events,'MANUAL_EVENTS',()):
            self.run_review(); self.requests.clear()
            self.history['one']['summary']='x'*700+'new'
            self.run_review()
        self.assertEqual(len(self.requests),1)

    def test_confirmed_duplicate_survives_other_new_posts_without_calls(self):
        self.history['0']['summary']='MATCH already published event'
        self.verdict='duplicate'
        self.assertEqual(self.run_review()['status'],'duplicate')
        self.requests.clear()
        self.history['new']=dict(title='Other coin new project',url='https://old.example/new')
        self.state['ai_review']['entries']={}
        self.now+=24*3600
        self.assertEqual(self.run_review()['status'],'duplicate')
        self.assertEqual(self.requests,[])

    def test_changed_or_removed_duplicate_evidence_cannot_keep_blocking(self):
        for remove in (True,False):
            with self.subTest(remove=remove):
                self.setUp()
                self.history['0']['summary']='MATCH old event'
                self.verdict='duplicate'
                self.run_review(); self.requests.clear()
                if remove: del self.history['0']
                else: self.history['0']['summary']='Actually unrelated corrected evidence'
                self.assertEqual(self.run_review()['status'],'new')

    def test_new_fact_after_duplicate_gets_fresh_comparison(self):
        self.history['0']['summary']='MATCH previous plan'
        self.verdict='duplicate'; self.run_review()
        self.story['_review_source_sha256']='confirmed-launch-source'
        self.caption='Company now launches after earlier plan'
        self.verdict='update'; self.requests.clear()
        self.assertEqual(self.run_review()['status'],'update')
        self.assertTrue(self.requests)

    def test_invalid_batch_does_not_mark_unreviewed_records_checked(self):
        count=0
        def broken(**kwargs):
            nonlocal count
            count+=1
            if count==2:
                return SimpleNamespace(status='completed',output_text='{}',usage=None)
            return self.answer(**kwargs)
        self.client.responses.create.side_effect=broken
        self.assertEqual(self.run_review()['status'],'hold')
        first_ids={r['id'] for r in data(self.requests[0])['history']}
        self.requests.clear()
        self.client.responses.create.side_effect=self.answer
        self.assertEqual(self.run_review()['status'],'new')
        remaining={r['id'] for p in self.requests for r in data(p)['history']}
        self.assertFalse(first_ids & remaining)
        self.assertEqual(first_ids | remaining,{r['id'] for r in events.history_records(self.history)})

    def test_uncertain_decision_stays_held_without_rechecking_same_evidence(self):
        self.history['0']['summary']='MATCH ambiguous event'
        self.verdict='uncertain'; self.run_review(); self.requests.clear()
        self.run_review()
        self.assertEqual(self.requests,[])
        self.now+=cache.NEGATIVE_TTL+1
        self.assertEqual(self.run_review()['status'],'hold')
        self.assertEqual(self.requests,[])
        self.story['_review_source_sha256']='new-evidence'
        self.assertEqual(self.run_review()['status'],'hold')
        self.assertTrue(self.requests)

    def test_policy_change_invalidates_both_memory_and_exact_requests(self):
        self.run_review(); self.requests.clear()
        with patch.object(cache,'VERSION','new-cache-policy'),patch.object(events,'EVENT_MEMORY_VERSION','new-event-policy'):
            self.run_review()
        self.assertTrue(self.requests)

    def test_memory_is_bounded_and_stale_records_expire(self):
        self.run_review()
        self.now+=cache.MEMORY_TTL+1
        self.requests.clear(); self.run_review()
        self.assertTrue(self.requests)
        with patch.object(cache,'MAX_EVENT_MEMORIES',2):
            for i in range(4):
                self.story['_review_source_sha256']=f'source-{i}'
                self.run_review()
        self.assertEqual(len(self.state['ai_review']['event_memory_v33']),2)


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
