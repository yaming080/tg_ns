"""Paid work reuse and invalidation boundaries; no network or Telegram calls."""
import copy
import json
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import news_review_cache as cache
import doorinews_editor as editor
import news_images as images
from news_event_review import review_event
from news_publication import prepare_publication
from news_source_cleanup import strip_page_furniture


SOURCE_FIELDS = ('faithful','conditions_preserved','allowed_category',
                 'new_substantive_fact','source_sufficient','understandable')


def response(text='검토 결과', **kwargs):
    return NS(output_text=text, status='completed', usage=NS(input_tokens=1000,
              output_tokens=100, input_tokens_details=NS(cached_tokens=200),
              output_tokens_details=NS(reasoning_tokens=30)), **kwargs)


def checks(flag, fields, approved=True):
    return json.dumps({flag:approved,'reason':'원문과 대상 확인',
                       'checks':dict.fromkeys(fields,approved)},ensure_ascii=False)


class ReviewCacheTests(unittest.TestCase):
    def setUp(self):
        self.state = {'posted':{'old':{'title':'posted item'}}}
        self.persist = Mock()
        self.client = Mock()
        self.client.responses.create.return_value = response()
        self.log = Mock()

    def test_exact_review_reused_across_runs_without_marking_posted(self):
        for _ in range(2):
            with cache.review_session(self.state,self.persist,self.log):
                self.assertEqual(cache.request_text(self.client,'gpt-5.4','same request'),'검토 결과')
            self.state = json.loads(json.dumps(self.state))
        self.assertEqual(self.client.responses.create.call_count,1)
        self.assertEqual(self.state['posted'],{'old':{'title':'posted item'}})

    def test_new_article_changed_source_prompt_model_image_or_stage_rechecks(self):
        with cache.review_session(self.state,self.persist,self.log):
            base = dict(stage='summary',scope={'url':'a','source':'one','published':'today'})
            cache.request_text(self.client,'gpt-5.4','prompt',**base)
            for field,value in [('url','b'),('source','two'),('published','tomorrow')]:
                args = copy.deepcopy(base); args['scope'][field]=value
                cache.request_text(self.client,'gpt-5.4','prompt',**args)
            cache.request_text(self.client,'gpt-5.4','new prompt',**base)
            cache.request_text(self.client,'gpt-5.4-mini','prompt',**base)
            cache.request_text(self.client,'gpt-5.4','prompt',stage='source_review',scope=base['scope'])
            for data in ('image-one','image-two'):
                cache.request_text(self.client,'gpt-5.4',[{'image':data}],stage='image_review')
        self.assertEqual(self.client.responses.create.call_count,9)

    def test_invalid_incomplete_and_empty_responses_are_not_cached(self):
        validator=lambda text: cache.valid_checks(text,'publish',SOURCE_FIELDS)
        for text in ('','not json','{}','[]',checks('publish',SOURCE_FIELDS).replace('true','"true"')):
            self.client.responses.create.return_value=response(text)
            with cache.review_session({},self.persist,self.log):
                for _ in range(2):
                    cache.request_text(self.client,'gpt-5.4','prompt',validator=validator)
            self.assertEqual(self.client.responses.create.call_count,2)
            self.client.responses.create.reset_mock()
        partial=response(checks('publish',SOURCE_FIELDS)); partial.status='incomplete'
        self.client.responses.create.return_value=partial
        with cache.review_session({},self.persist,self.log):
            for _ in range(2):
                self.assertEqual(cache.request_text(self.client,'gpt-5.4','prompt',validator=validator),'')
        self.assertEqual(self.client.responses.create.call_count,2)

    def test_network_failure_can_retry_and_is_not_a_rejection(self):
        self.client.responses.create.side_effect=[TimeoutError(),response()]
        with cache.review_session(self.state,self.persist,self.log):
            with self.assertRaises(TimeoutError):
                cache.request_text(self.client,'gpt-5.4','prompt')
            self.assertEqual(cache.request_text(self.client,'gpt-5.4','prompt'),'검토 결과')
        self.assertEqual(self.client.responses.create.call_count,2)

    def test_quota_stops_further_api_calls_and_marks_run_failed(self):
        exc=RuntimeError('billing unavailable'); exc.code='credit_balance_exhausted'
        self.client.responses.create.side_effect=exc
        with self.assertRaises(cache.ReviewQuotaError):
            with cache.review_session(self.state,self.persist,self.log):
                with self.assertRaises(RuntimeError):
                    cache.request_text(self.client,'gpt-5.4','first')
                with self.assertRaises(cache.ReviewQuotaError):
                    cache.request_text(self.client,'gpt-5.4','second')
        self.assertEqual(self.client.responses.create.call_count,1)
        self.assertEqual(self.state['ai_review']['entries'],{})
        self.assertIsNone(cache._STORE.get())

    def test_real_usage_cached_input_and_reasoning_are_counted_once(self):
        with cache.review_session(self.state,self.persist,self.log):
            for _ in range(2):
                cache.request_text(self.client,'gpt-5.4','prompt')
        day=next(iter(self.state['ai_review']['usage_by_day_utc'].values()))
        row=day['gpt-5.4']['summary']
        self.assertEqual((row['api_calls'],row['cache_hits']),(1,1))
        self.assertEqual((row['input_tokens'],row['cached_input_tokens'],row['output_tokens'],row['reasoning_tokens']),
                         (1000,200,100,30))
        self.assertAlmostEqual(row['estimated_usd'],.00355)
        self.assertAlmostEqual(self.state['ai_review']['recent_runs'][-1]['estimated_usd'],.00355)

    def test_run_records_only_confirmed_posts_and_keeps_failure_status(self):
        with cache.review_session(self.state,self.persist,self.log):
            cache.record_publication()
        row=self.state['ai_review']['recent_runs'][-1]
        self.assertEqual((row['published'],row['status']),(1,'completed'))
        with self.assertRaises(ValueError):
            with cache.review_session(self.state,self.persist,self.log):
                raise ValueError('simulated failure')
        row=self.state['ai_review']['recent_runs'][-1]
        self.assertEqual((row['published'],row['status']),(0,'failed'))

    def test_missing_usage_and_unknown_model_are_explicit(self):
        self.client.responses.create.side_effect=[NS(output_text='x',status='completed'),response()]
        with cache.review_session(self.state,self.persist,self.log):
            cache.request_text(self.client,'gpt-5.4','one')
            cache.request_text(self.client,'unknown-model','two')
        day=next(iter(self.state['ai_review']['usage_by_day_utc'].values()))
        self.assertEqual(day['gpt-5.4']['summary']['missing_usage'],1)
        self.assertEqual(day['unknown-model']['summary']['unpriced_calls'],1)

    def test_negative_verdict_expires_and_policy_version_invalidates(self):
        self.client.responses.create.return_value=response(checks('approved',images.IMAGE_CHECKS,False))
        clock=Mock(return_value=1000)
        store=cache.ReviewStore(self.state,self.persist,self.log,clock)
        validator=lambda text: cache.valid_checks(text,'approved',images.IMAGE_CHECKS)
        for now in (1000,1001,1001+cache.MEMORY_TTL+1):
            clock.return_value=now
            store.request(self.client,'gpt-5.4','same','image_review',None,validator)
        self.assertEqual(self.client.responses.create.call_count,2)
        self.state['ai_review']['version']='old-policy'
        fresh=cache.ReviewStore(self.state,self.persist,self.log,clock)
        self.assertEqual(fresh.entries,{})
        self.assertTrue(fresh.usage)

    def test_image_bytes_not_saved_and_cap_enforced(self):
        with patch.object(cache,'MAX_ENTRIES',2):
            with cache.review_session(self.state,self.persist,self.log):
                for i in range(4):
                    cache.request_text(self.client,'gpt-5.4',{'image':'BASE64-IMAGE-'+str(i)},stage='image_review')
        data=json.dumps(self.state)
        self.assertNotIn('BASE64-IMAGE',data)
        self.assertEqual(len(self.state['ai_review']['entries']),2)

    def test_source_cleanup_retains_negation_amounts_and_conditions(self):
        source='<body><nav><p>menu subscribe</p></nav><article><p>Trial only; NOT launched. $20 &amp; 2028.</p><p>Available only in Korea.</p></article><footer><p>unrelated links</p></footer></body>'
        cleaned=strip_page_furniture(source)
        self.assertNotIn('menu subscribe',cleaned)
        self.assertNotIn('unrelated links',cleaned)
        self.assertIn('Trial only; NOT launched. $20 &amp; 2028.',cleaned)
        self.assertIn('Available only in Korea.',cleaned)
        malformed='<nav>bad markup<article><p>story'
        self.assertEqual(strip_page_furniture(malformed),malformed)

    def test_image_only_retry_reuses_text_and_event_but_reviews_new_image(self):
        story=dict(title='Ripple receives final approval for XRP payments license in Singapore',
                   desc='Ripple received final approval for an XRP payments license in Singapore.',
                   url='https://example.com/news',pub='2026-10-05T00:00:00Z')
        requests=[]
        def answer(**kwargs):
            payload=kwargs['input']; requests.append(payload)
            if isinstance(payload,list):
                # First image is unrelated; second candidate appears on next run.
                approved='bmV3LWltYWdl' in str(payload)
                return response(checks('approved',images.IMAGE_CHECKS,approved))
            if '뉴스의 사건 중복을 판정' in payload:
                return response('{"decision":"new","matched_id":"","reason":"Separate licensing event"}')
            if '"related_ids"' in payload:
                data, _ = json.JSONDecoder().raw_decode(payload[payload.index('{"candidate"'):])
                return response(json.dumps({'related_ids':[], 'uncertain':False,
                                            'checked_count':len(data['history'])}))
            if '"publish"' in payload:
                return response(checks('publish',SOURCE_FIELDS))
            return response('리플이 싱가포르에서 XRP 결제 서비스 정식 라이선스를 취득했다고 밝힘')
        self.client.responses.create.side_effect=answer
        runtime={'openai_client':self.client,'OPENAI_MODEL':'gpt-5.4'}
        current=[b'old-image']
        def selector(s,c,cl,m):
            approved,reason=images.review_image(cl,m,s,c,current[0],'image/png')
            return (object() if approved else None),[]
        with patch.object(editor,'_RUNTIME',runtime),patch.object(editor,'_is_hard_blocked',return_value=(False,'')):
            for image,expected in [(b'old-image','held'),(b'new-image','ready')]:
                current[0]=image
                with cache.review_session(self.state,self.persist,self.log):
                    result=prepare_publication(story,editor.build_message,self.client,'gpt-5.4',selector,
                        event_review=lambda caption: editor.review_article_event(story,caption,{}))
                    self.assertEqual(result['status'],expected)
        # Summary and source review only: no related past licensing event.
        self.assertEqual(sum(isinstance(p,str) for p in requests),2)
        self.assertEqual(sum(isinstance(p,list) for p in requests),2)
        self.assertEqual(self.state['posted'],{'old':{'title':'posted item'}})

    def test_changed_related_history_rechecks_event_even_with_same_candidate(self):
        self.client.responses.create.return_value=response('{"decision":"new","matched_id":"","reason":"New project"}')
        candidate=dict(title='Ripple launches payment network',url='https://example.com/new')
        runtime={'openai_client':self.client,'OPENAI_MODEL':'gpt-5.4'}
        one={'a':dict(title='Ripple payment pilot',url='https://example.com/old',summary='Earlier pilot')}
        two=dict(one,b=dict(title='Ripple payment launch',url='https://example.com/other',summary='New related evidence'))
        with patch.object(editor,'_RUNTIME',runtime):
            with cache.review_session(self.state,self.persist,self.log):
                for history in (one,one,two):
                    self.assertEqual(review_event(candidate,'리플 결제망 출시',history,editor._call_openai)['status'],'new')
        self.assertEqual(self.client.responses.create.call_count,2)


if __name__ == '__main__':
    unittest.main()
