"""Offline migration checks: routing, bounded requests, cache and cost."""
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import doorinews_editor as editor
import news_review_cache as cache
from news_event_review import history_records

MODEL = 'gpt-6-luna'

def response(text='검토 결과', **kwargs):
    return NS(output_text=text, status='completed', usage=NS(input_tokens=1000,
        output_tokens=100, input_tokens_details=NS(cached_tokens=200, cache_write_tokens=100),
        output_tokens_details=NS(reasoning_tokens=30)), **kwargs)


class LunaMigrationTests(unittest.TestCase):
    def test_runtime_and_all_workflows_default_to_luna(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/'doorinews_bot.py').read_text(encoding='utf-8')
        self.assertIn('os.environ.get("OPENAI_MODEL", "gpt-6-luna")',text)
        for p in (root/'.github/workflows').glob('*.yml'):
            for line in p.read_text(encoding='utf-8').splitlines():
                if 'OPENAI_MODEL:' in line:
                    self.assertIn(MODEL,line)

    def test_text_and_image_share_bounded_luna_settings(self):
        client=Mock();client.responses.create.return_value=response()
        payload=[{'role':'user','content':[{'type':'input_text','text':'verify'},
            {'type':'input_image','image_url':'data:image/png;base64,TEST','detail':'high'}]}]
        for value,stage in [('summary','summary'),(payload,'image_review')]:
            cache.request_text(client,MODEL,value,stage=stage)
            args=client.responses.create.call_args.kwargs
            self.assertEqual(args['model'],MODEL)
            self.assertEqual(args['input'],value)
            self.assertEqual(args['reasoning'],{'effort':'low'})
            self.assertEqual(args['max_output_tokens'],4096)
            self.assertEqual(args['service_tier'],'default')

    def test_persistent_reuse_and_changed_source(self):
        state={};client=Mock();client.responses.create.return_value=response()
        for _ in range(2):
            with cache.review_session(state,lambda:None,logger=lambda *_:None):
                cache.request_text(client,MODEL,'same',scope={'source':'one'})
        self.assertEqual(client.responses.create.call_count,1)
        with cache.review_session(state,lambda:None,logger=lambda *_:None):
            cache.request_text(client,MODEL,'same',scope={'source':'two'})
        self.assertEqual(client.responses.create.call_count,2)

    def test_old_model_cache_does_not_skip_luna_review(self):
        state={};client=Mock();client.responses.create.return_value=response()
        with cache.review_session(state,lambda:None,logger=lambda *_:None):
            cache.request_text(client,'gpt-5.4','same')
            cache.request_text(client,MODEL,'same')
        self.assertEqual(client.responses.create.call_count,2)

    def test_standard_usage_counts_cache_write_and_reasoning_once(self):
        client=Mock();client.responses.create.return_value=response()
        with cache.review_session({},lambda:None,logger=lambda *_:None) as store:
            cache.request_text(client,MODEL,'test')
            self.assertAlmostEqual(store.estimated_usd,(800*.10+200*.01+100*.025+100*.50)/1e6)
            self.assertEqual(store.unpriced_calls,0)

    def test_long_context_rate(self):
        client=Mock();r=response();r.usage.input_tokens=300000
        client.responses.create.return_value=r
        with cache.review_session({},lambda:None,logger=lambda *_:None) as store:
            cache.request_text(client,MODEL,'test')
            self.assertAlmostEqual(store.estimated_usd,((299800*.10+200*.01+100*.025)*2+100*.50*1.5)/1e6)

    def test_incomplete_is_not_reused_or_escalated(self):
        client=Mock();r=response();r.status='incomplete';client.responses.create.return_value=r
        with cache.review_session({},lambda:None,logger=lambda *_:None) as store:
            self.assertEqual(cache.request_text(client,MODEL,'test'),'')
            self.assertFalse(store.entries)
        self.assertEqual(client.responses.create.call_count,1)
        self.assertEqual(client.responses.create.call_args.kwargs['model'],MODEL)

    def test_related_new_update_duplicate_decisions_all_use_luna(self):
        story={'title':'Flare new service','url':'https://example.org/new'}
        posted={'old':{'title':'Flare previous service','url':'https://example.org/old','summary':'previous'}}
        match=next(r['id'] for r in history_records(posted) if r.get('url')=='https://example.org/old')
        for decision in ['new','update','duplicate','supplement','uncertain']:
            client=Mock()
            client.responses.create.side_effect=[response(json.dumps({'related_ids':[match]})),
                response(json.dumps({'decision':decision,'reason':'evidence','matched_id':match,'new_fact':'new launch'}))]
            with patch.object(editor,'_RUNTIME',{'openai_client':client,'OPENAI_MODEL':MODEL}), \
                 patch.dict(editor.os.environ,{'OPENAI_EVENT_SEARCH_MODEL':'gpt-5.4-mini'}):
                result=editor.review_article_event(story,'Flare launches a new service',posted)
            self.assertEqual(result['status'],'hold' if decision=='uncertain' else decision)
            self.assertEqual(client.responses.create.call_count,2)
            self.assertEqual({c.kwargs['model'] for c in client.responses.create.call_args_list},{MODEL})

    def test_invalid_search_holds_without_expensive_fallback(self):
        client=Mock();client.responses.create.return_value=response('not json')
        with patch.object(editor,'_RUNTIME',{'openai_client':client,'OPENAI_MODEL':MODEL}), \
             patch.dict(editor.os.environ,{'OPENAI_EVENT_SEARCH_MODEL':'gpt-5.4-mini'}):
            result=editor.review_article_event({'title':'new','url':'https://example.org/new'},'new launch',{})
        self.assertEqual(result['status'],'hold')
        self.assertEqual(client.responses.create.call_count,1)
        self.assertEqual(client.responses.create.call_args.kwargs['model'],MODEL)


if __name__=='__main__':
    unittest.main()
