"""Paid-call routing and cache regressions; no live API or Telegram calls."""
import json
import os
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import doorinews_editor as editor
import news_event_review as events
import news_review_cache as cache


def payload(prompt):
    return json.JSONDecoder().raw_decode(prompt[prompt.index('{"candidate"'):])[0]


def response(text):
    return SimpleNamespace(status='completed', output_text=text, usage=SimpleNamespace(
        input_tokens=10000, output_tokens=50,
        input_tokens_details=SimpleNamespace(cached_tokens=0)))


class ReviewSavingsTests(unittest.TestCase):
    def setUp(self):
        self.story = dict(title='Ripple new payment launch', url='https://new.example/a',
                          _review_source_sha256='original-source')
        self.caption = 'Ripple launches payments in a new country'
        self.history = {'a':dict(title='Ripple plans payment pilot', url='https://old.example/a',
                                summary='A limited pilot, not a launch')}
        self.client = Mock()
        self.client.responses.create.return_value = response('{"decision":"new","matched_id":"","reason":"Different business"}')
        self.runtime = {'openai_client':self.client, 'OPENAI_MODEL':'gpt-5.4'}

    def test_unrelated_history_has_no_paid_search(self):
        history={str(i):dict(title=f'Unrelated business {i}',url=f'https://old.example/{i}') for i in range(321)}
        strong=Mock()
        with patch.object(events,'MANUAL_EVENTS',()):
            self.assertEqual(events.review_event(self.story,self.caption,history,strong)['status'],'new')
        strong.assert_not_called()

    def test_invalid_search_holds_without_second_model_or_retry(self):
        for text in ('', '{}', '{"related_ids":["invented"]}', '{"related_ids":false}'):
            with self.subTest(text=text), patch.object(editor,'_RUNTIME',self.runtime):
                self.client.responses.create.reset_mock()
                self.client.responses.create.return_value=response(text)
                self.assertEqual(editor.review_article_event(self.story,self.caption,self.history)['status'],'hold')
                self.client.responses.create.assert_called_once()

    def test_old_mini_environment_override_cannot_add_paid_pass(self):
        for configured in ('gpt-5.4-mini','gpt-5.4',''):
            with self.subTest(configured=configured), patch.object(editor,'_RUNTIME',self.runtime), patch.dict(os.environ,{'OPENAI_EVENT_SEARCH_MODEL':configured}):
                self.client.responses.create.reset_mock()
                state={}
                with cache.review_session(state,lambda:None,lambda s:None):
                    result=editor.review_article_event(self.story,self.caption,self.history)
                self.assertEqual(result['status'],'new')
                self.client.responses.create.assert_called_once()
                self.assertEqual(self.client.responses.create.call_args.kwargs['model'],'gpt-5.4')
                self.assertAlmostEqual(state['ai_review']['recent_runs'][-1]['estimated_usd'],.02575)

    def test_exact_result_survives_restart_without_any_paid_pass(self):
        state={}
        with patch.object(editor,'_RUNTIME',self.runtime):
            for _ in range(2):
                with cache.review_session(state,lambda:None,lambda s:None):
                    editor.review_article_event(self.story,self.caption,self.history)
                state=json.loads(json.dumps(state))
        self.client.responses.create.assert_called_once()
        self.assertEqual(state['ai_review']['recent_runs'][-1]['api_calls'],0)
        self.assertEqual(state['ai_review']['recent_runs'][-1]['estimated_usd'],0)

    def test_old_search_cache_cannot_substitute_for_final_verdict(self):
        state={}
        with cache.review_session(state,lambda:None,lambda s:None):
            cache.request_text(self.client,'gpt-5.4','old all-history search',stage='event_search',scope='original-source')
        self.client.responses.create.reset_mock()
        with patch.object(editor,'_RUNTIME',self.runtime),cache.review_session(state,lambda:None,lambda s:None):
            self.assertEqual(editor.review_article_event(self.story,self.caption,self.history)['status'],'new')
        self.client.responses.create.assert_called_once()
        self.assertNotIn('related_ids',self.client.responses.create.call_args.kwargs['input'])

    def test_changed_source_and_history_must_recheck(self):
        state={}
        with patch.object(editor,'_RUNTIME',self.runtime),cache.review_session(state,lambda:None,lambda s:None):
            editor.review_article_event(self.story,self.caption,self.history)
            editor.review_article_event(self.story,self.caption,self.history)
            self.assertEqual(self.client.responses.create.call_count,1)
            self.story['_review_source_sha256']='new-source-evidence'
            editor.review_article_event(self.story,self.caption,self.history)
            self.assertEqual(self.client.responses.create.call_count,2)
            self.history['a']['summary']='Now includes new licensing evidence'
            editor.review_article_event(self.story,self.caption,self.history)
            self.assertEqual(self.client.responses.create.call_count,3)

    def test_all_final_verdicts_still_come_from_original_model(self):
        target=events.history_records(self.history)[0]['id']
        for verdict in ('duplicate','supplement','uncertain','new','update'):
            strong=Mock(return_value=json.dumps({
                'decision':verdict,'matched_id':target,'reason':'Compare event and stage',
                'new_fact':'Actual launch in a new country confirmed by source'}))
            result=events.review_event(self.story,self.caption,self.history,strong)
            self.assertEqual(result['status'],'hold' if verdict=='uncertain' else verdict)
            self.assertEqual(strong.call_count,1)

    def test_same_url_is_rejected_without_paid_work(self):
        strong=Mock()
        story=dict(self.story,url='https://old.example/a?utm_source=rss')
        self.assertEqual(events.review_event(story,self.caption,self.history,strong)['status'],'duplicate')
        strong.assert_not_called()

    def test_new_history_changes_one_bucket_and_keeps_all_entries(self):
        records=events.history_records({str(i):dict(title=f'Company {i}',url=f'https://old.example/{i}') for i in range(350)})
        before=[json.dumps(b,sort_keys=True) for b in events.history_batches(records)]
        after=[json.dumps(b,sort_keys=True) for b in events.history_batches(records+[dict(id='0000000000000001',title='new')])]
        self.assertEqual(len(set(before)-set(after)),1)
        self.assertEqual(sum(len(b) for b in events.history_batches(records)),len(records))

    def test_small_history_does_not_add_requests(self):
        self.assertEqual(len(list(events.history_batches(events.history_records(self.history)))),1)
        self.assertEqual(list(events.history_batches([])),[])

    def test_digest_labels_block_before_article_or_api_work(self):
        for title in ('[저녁 뉴스브리핑] 홍콩 라이선스 外','[시세브리핑] 비트코인 가격 상승'):
            with patch.object(editor,'_call_openai') as ai:
                self.assertEqual(editor.build_message({'title':title}), '')
                ai.assert_not_called()
        blocked,reason=editor._is_hard_blocked({'title':'홍콩 정부 브리핑: 새 가상자산 법안 제출'})
        self.assertNotEqual(reason,'정기 뉴스·시세 모음 브리핑')
