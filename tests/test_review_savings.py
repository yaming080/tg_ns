"""Routing/coverage regressions with simulated responses, not model-quality scores."""
import json
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

import doorinews_editor as editor
import news_event_review as events
import news_review_cache as cache


def payload(prompt):
    return json.JSONDecoder().raw_decode(prompt[prompt.index('{"candidate"'):])[0]


def mini_result(prompt, uncertain=False, ids=None):
    data = payload(prompt)
    return json.dumps({'related_ids':ids or [], 'uncertain':uncertain,
                       'checked_count':len(data['history'])})


class ReviewSavingsTests(unittest.TestCase):
    def setUp(self):
        self.story = dict(title='리플, 새 국가에서 결제 서비스 출시', url='https://new.example/a')
        self.caption = '리플이 별도 국가에서 XRP 결제 서비스를 출시했다고 밝힘'
        self.history = {'a':dict(title='Ripple plans XRP payment pilot', url='https://old.example/a',
                                summary='Ripple announced a limited pilot, not a launch')}

    def test_all_history_languages_and_manual_examples_reach_mini(self):
        history = {str(i):dict(title=f'새 기업 {i} launches new product',url=f'https://old.example/{i}')
                   for i in range(321)}
        seen=[]
        def mini(prompt):
            seen.extend(payload(prompt)['history'])
            return mini_result(prompt)
        strong=Mock()
        result=events.review_event(self.story,self.caption,history,strong,mini)
        self.assertEqual(result['status'],'new')
        self.assertEqual({r['id'] for r in seen},{r['id'] for r in events.history_records(history)})
        self.assertEqual(len(seen),len(events.history_records(history)))
        strong.assert_not_called()

    def test_uncertain_incomplete_invalid_or_failed_mini_falls_back(self):
        for answer in ('', '{}', '{"related_ids":["invented"],"uncertain":false,"checked_count":1}',
                       'exception', 'uncertain', 'incomplete'):
            with self.subTest(answer=answer):
                def mini(prompt):
                    if answer=='exception':
                        raise RuntimeError('model unavailable')
                    if answer=='uncertain':
                        return mini_result(prompt,True)
                    if answer=='incomplete':
                        return '{"related_ids":[],"uncertain":false,"checked_count":0}'
                    return answer
                strong=Mock(return_value='{"related_ids":[]}')
                result=events.review_event(self.story,self.caption,self.history,strong,mini)
                self.assertEqual(result['status'],'new')
                self.assertEqual(strong.call_count,len(list(events.history_batches(events.history_records(self.history)))))

    def test_both_models_unavailable_holds(self):
        result=events.review_event(self.story,self.caption,self.history,lambda p:'',lambda p:'')
        self.assertEqual(result['status'],'hold')

    def test_all_final_verdicts_still_come_from_strong_model(self):
        target=events.history_records(self.history)[0]['id']
        def mini(prompt):
            ids=[r['id'] for r in payload(prompt)['history'] if r['id']==target]
            return mini_result(prompt,ids=ids)
        for verdict in ('duplicate','supplement','uncertain','new','update'):
            strong=Mock(return_value=json.dumps({'decision':verdict,'matched_id':target,
                        'reason':'계획과 실제 출시를 대조','new_fact':'원문에 별도 지역 실제 출시 확인'}))
            result=events.review_event(self.story,self.caption,self.history,strong,mini)
            self.assertEqual(result['status'],'hold' if verdict=='uncertain' else verdict)
            strong.assert_called_once()

    def test_uncertain_mini_match_is_not_lost_when_fallback_returns_empty(self):
        target=events.history_records(self.history)[0]['id']
        def mini(prompt):
            ids=[r['id'] for r in payload(prompt)['history'] if r['id']==target]
            return mini_result(prompt,True,ids)
        def strong(prompt):
            if 'related_ids' in prompt:
                return '{"related_ids":[]}'
            return json.dumps({'decision':'duplicate','matched_id':target,'reason':'같은 사건'})
        self.assertEqual(events.review_event(self.story,self.caption,self.history,strong,mini)['status'],'duplicate')

    def test_same_url_is_rejected_without_paid_work(self):
        strong=Mock();mini=Mock()
        story=dict(self.story,url='https://old.example/a?utm_source=rss')
        self.assertEqual(events.review_event(story,self.caption,self.history,strong,mini)['status'],'duplicate')
        strong.assert_not_called();mini.assert_not_called()

    def test_new_history_changes_one_bucket_and_keeps_all_entries(self):
        records=events.history_records({str(i):dict(title=f'Company {i}',url=f'https://old.example/{i}') for i in range(350)})
        before=[json.dumps(b,sort_keys=True) for b in events.history_batches(records)]
        after=[json.dumps(b,sort_keys=True) for b in events.history_batches(records+[dict(id='0000000000000001',title='new')])]
        self.assertEqual(len(set(before)-set(after)),1)
        self.assertEqual(sum(len(b) for b in events.history_batches(records)),len(records))

    def test_small_history_does_not_add_requests(self):
        records=events.history_records(self.history)
        self.assertEqual(len(list(events.history_batches(records))),1)
        self.assertEqual(list(events.history_batches([])),[])

    def test_changed_history_summary_invalidates_cache(self):
        state={};client=Mock()
        def respond(**kwargs):
            return SimpleNamespace(status='completed',output_text='{"related_ids":[]}',usage=None)
        client.responses.create.side_effect=respond
        def strong(p): return cache.request_text(client,'gpt-5.4',p)
        with cache.review_session(state,lambda:None,lambda s:None):
            events.review_event(self.story,self.caption,self.history,strong)
            calls=client.responses.create.call_count
            events.review_event(self.story,self.caption,self.history,strong)
            self.assertEqual(client.responses.create.call_count,calls)
            self.history['a']['summary']='Now includes new licensing evidence'
            events.review_event(self.story,self.caption,self.history,strong)
            self.assertEqual(client.responses.create.call_count,calls+1)

    def test_only_search_uses_mini_and_kill_switch_restores_strong(self):
        client=Mock()
        def respond(**kwargs):
            text=mini_result(kwargs['input']) if kwargs['model']=='gpt-5.4-mini' else '{"related_ids":[]}'
            return SimpleNamespace(status='completed',output_text=text)
        client.responses.create.side_effect=respond
        with patch.object(editor,'_RUNTIME',{'openai_client':client,'OPENAI_MODEL':'gpt-5.4'}),patch.dict(editor.os.environ,{'OPENAI_EVENT_SEARCH_MODEL':'gpt-5.4-mini'}):
            editor.review_article_event(self.story,self.caption,self.history)
            self.assertEqual({c.kwargs['model'] for c in client.responses.create.call_args_list},{'gpt-5.4-mini'})
            client.reset_mock()
            with patch.dict(editor.os.environ,{'OPENAI_EVENT_SEARCH_MODEL':''}):
                editor.review_article_event(self.story,self.caption,self.history)
            self.assertEqual({c.kwargs['model'] for c in client.responses.create.call_args_list},{'gpt-5.4'})

    def test_digest_labels_block_before_article_or_api_work(self):
        for title in ('[저녁 뉴스브리핑] 홍콩 라이선스 外','[시세브리핑] 비트코인 가격 상승'):
            with patch.object(editor,'_call_openai') as ai:
                self.assertEqual(editor.build_message({'title':title}), '')
                ai.assert_not_called()
        blocked,reason=editor._is_hard_blocked({'title':'홍콩 정부 브리핑: 새 가상자산 법안 제출'})
        self.assertNotEqual(reason,'정기 뉴스·시세 모음 브리핑')
