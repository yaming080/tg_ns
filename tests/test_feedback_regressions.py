import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import doorinews_editor as e
from news_quality import freshness_reason, source_promotion_reason, valid_caption


class FeedbackRegressions(unittest.TestCase):
    def setUp(self):
        self.runtime=e._RUNTIME
        e._RUNTIME={}
    def tearDown(self):
        e._RUNTIME=self.runtime

    def test_person_bilingual_tags(self):
        story={'title':'Justin Sun launches Bitcoin payment service'}
        body, selected=e._inject_inline_tags('저스틴선이 비트코인 결제 서비스를 공개함',story)
        self.assertIn('#저스틴선',body)
        self.assertIn('#JustinSun',e._build_footer_tags(story,selected))

    def test_preliminary_then_final_is_new_progress(self):
        a={'title':'Ripple receives preliminary approval for XRP payments license in Singapore'}
        b={'title':'Ripple receives final approval for XRP payments license in Singapore'}
        sa,sb=e.build_story_signature(a),e.build_story_signature(b)
        self.assertNotEqual(sa,sb)
        self.assertFalse(e.is_canonical_duplicate(sb,{sa}))
        self.assertFalse(e.is_semantically_duplicate(b,[sa],[a['title']]))

    def test_same_final_approval_stays_duplicate(self):
        a={'title':'Ripple receives final approval for XRP payments license in Singapore'}
        sig=e.build_story_signature(a)
        self.assertTrue(e.is_canonical_duplicate(sig,{sig}))

    def test_changed_purchase_quantity_does_not_earn_another_post(self):
        a={'title':'Strategy purchases 1000 Bitcoin for its corporate treasury'}
        b={'title':'Strategy purchases 2000 Bitcoin for its corporate treasury'}
        self.assertTrue(e.is_semantically_duplicate(b,[e.build_story_signature(a)],[a['title']]))
        self.assertTrue(e.is_canonical_duplicate(e.build_story_signature(b),{e.build_story_signature(a)}))

    def test_old_publication_is_held(self):
        self.assertTrue(freshness_reason({'pub':'Wed, 01 Sep 2021 00:00:00 GMT'},datetime(2026,9,26,tzinfo=timezone.utc)))

    def test_new_report_about_old_event_is_not_age_blocked(self):
        self.assertFalse(freshness_reason({'pub':'2026-09-26T00:00:00Z','desc':'New court ruling about a 2021 incident'},datetime(2026,9,26,tzinfo=timezone.utc)))

    def test_full_source_sponsored_disclosure(self):
        self.assertTrue(source_promotion_reason({'title':'Bitcoin payments launch','article_text':'Sponsored content\nA new service is launching.'}))

    def test_advertising_in_background_is_not_disclosure(self):
        self.assertFalse(source_promotion_reason({'article_text':'The regulator investigated misleading sponsored content in an enforcement case.'}))

    def test_long_korean_caption_keeps_links(self):
        caption='가'*350+'\n<a href="https://example.com/'+('x'*1000)+'">출처</a>'
        self.assertGreater(len(caption.encode('utf-8')),1000)
        self.assertTrue(valid_caption(caption))
        self.assertFalse(valid_caption('가'*1025))
        self.assertFalse(valid_caption('<a href="https://example.com">출처'))

    def test_summary_preserves_second_sentence_condition(self):
        story={'title':'A launches Bitcoin pilot','desc':'A started a Bitcoin payments pilot. No public launch date has been set.'}
        summary='A사가 비트코인 결제 시험을 시작했다고 밝힘\n\n공식 출시일은 정해지지 않았다고 전함'
        verdict=json.dumps({'publish':True,'reason':'사실 일치','checks':dict.fromkeys(('faithful','conditions_preserved','allowed_category','new_substantive_fact','source_sufficient'),True)})
        with patch.object(e,'_call_openai',side_effect=[summary,verdict]):
            self.assertEqual(e._rewrite_summary(story),summary)

    def test_unfaithful_summary_is_held(self):
        story={'title':'Bitcoin pilot','desc':'The firm started a pilot; no launch date.'}
        with patch.object(e,'_call_openai',side_effect=['회사가 비트코인 결제 서비스를 정식 출시함','{"publish":false,"reason":"시험을 정식 출시로 변경"}']):
            self.assertEqual(e._rewrite_summary(story),'')

    def test_malformed_review_is_held(self):
        with patch.object(e,'_call_openai',return_value='```json\n{"publish":true}\n```'):
            self.assertFalse(e._validate_summary_against_source('a','b','c'))

    def test_publish_true_without_completed_checks_is_held(self):
        with patch.object(e,'_call_openai',return_value='{"publish":true,"reason":"괜찮음"}'):
            self.assertFalse(e._validate_summary_against_source('a','b','c'))

    def test_disallowed_or_uncertain_check_cannot_be_overridden(self):
        for value in (False,None,'true'):
            checks=dict.fromkeys(('faithful','conditions_preserved','allowed_category','new_substantive_fact','source_sufficient'),True)
            checks['allowed_category']=value
            with patch.object(e,'_call_openai',return_value=json.dumps({'publish':True,'reason':'검사','checks':checks})):
                self.assertFalse(e._validate_summary_against_source('a','b','c'))

    def test_excluded_content_only_in_full_source_is_held_before_summary(self):
        e._RUNTIME={'get_best_source_text':lambda story:'Bitcoin price prediction: technical analysis and support levels.'}
        with patch.object(e,'_call_openai') as model:
            self.assertEqual(e._rewrite_summary({'title':'Bitcoin network report'}),'')
            model.assert_not_called()

    def test_title_only_is_held_without_model_call(self):
        e._RUNTIME={'get_best_source_text':lambda story:story['title']}
        with patch.object(e,'_call_openai') as model:
            self.assertEqual(e._rewrite_summary({'title':'Bitcoin launch'}),'')
            model.assert_not_called()

    def test_sponsored_source_is_held_before_summary(self):
        e._RUNTIME={'get_best_source_text':lambda story:'Paid press release.\nRegister with referral code.'}
        with patch.object(e,'_call_openai') as model:
            self.assertEqual(e._rewrite_summary({'title':'Bitcoin service launch'}),'')
            model.assert_not_called()

    def test_state_corruption_does_not_become_empty_history(self):
        # Isolate the two functions without importing the runnable/network bot.
        root=Path(__file__).resolve().parents[1]
        tree=ast.parse((root/'doorinews_bot.py').read_text(encoding='utf-8'))
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('load_state','save_state')]
        ns={'os':os,'json':json}
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'<isolated state functions>','exec'),ns)
        with tempfile.TemporaryDirectory() as temp:
            path=str(Path(temp)/'state.json')
            ns['save_state'](path,{'posted':{'a':{'title':'news'}}})
            self.assertIn('a',ns['load_state'](path)['posted'])
            self.assertFalse(Path(path+'.tmp').exists())
            Path(path).write_text('{broken',encoding='utf-8')
            with self.assertRaises(RuntimeError):ns['load_state'](path)


if __name__=='__main__':unittest.main()
