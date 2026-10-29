"""User feedback regressions. Fake responses only: no API or Telegram calls."""
import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

import doorinews_editor as editor
import news_event_review as events
import news_images as images
import news_quality as quality
import news_review_cache as cache
from news_review_identity import canonical_scope, canonical_url
from news_team_oct29 import REJECTED, EVENTS
from test_unchanged_exclusions import answer, story


class TeamFeedbackTests(unittest.TestCase):
    def test_all_confirmed_removals_skip_without_paid_call_and_explain(self):
        for url, reason in REJECTED.items():
            with self.subTest(url=url), patch.object(editor, '_call_openai') as paid:
                item=story(url='https://'+url+'#source')
                self.assertEqual(editor.build_message(item), '')
                self.assertEqual(item['_preparation_reason'], reason)
                paid.assert_not_called()

    def test_removal_is_not_company_wide_or_keyword_ban(self):
        for url in ('https://cointelegraph.com/news/sofi-new-bank-partnership',
                    'https://crypto.news/google-custody-actually-launches-2027',
                    'https://bloomingbit.io/feed/news/999999',
                    'https://cryptobriefing.com/binance-final-brazil-approval'):
            self.assertEqual(quality.manual_post_reason({'url':url}), '')

    def test_feedback_history_preserves_real_articles_and_conditions(self):
        records=events.history_records({})
        for url,title,summary in EVENTS:
            record=next(r for r in records if events.url_key(r.get('url'))==events.url_key(url))
            self.assertEqual(record['summary'], summary)
        self.assertIn('미정', next(r['summary'] for r in records if '무반타이스' in r['summary']).replace('공개되지 않음','미정'))

    def test_actual_team_tag_examples_and_fixed_footer(self):
        cases=json.loads(Path(__file__).with_name('oct29_tag_examples.json').read_text('utf8'))
        for c in cases:
            with self.subTest(photo=c['photo']):
                body, selected=editor._inject_inline_tags(c['body'], {'title':c['title']})
                for tag in c['expected']:
                    self.assertIn(tag,body)
                self.assertLessEqual(len(selected),editor.MAX_INLINE_TAGS)
                footer=editor._build_footer_tags({'title':c['title']},selected)
                self.assertEqual(footer[-6:],list(editor.FIXED_FOOTER_TAGS))

    def test_long_product_name_is_not_split_into_parent_company(self):
        body,_=editor._inject_inline_tags('에테나 페이가 출시하고 코인베이스 프라임이 지원함',{'title':'EthenaPay Coinbase Prime'})
        self.assertIn('#에테나페이 가',body)
        self.assertIn('#코인베이스프라임 이',body)
        self.assertNotIn('#에테나 페이',body)

    def test_unmentioned_entities_are_never_added(self):
        body,_=editor._inject_inline_tags('새 서비스가 공개됨',{'title':'Ascend Markets Interpol Stellar Movantis'})
        self.assertEqual(body,'새 서비스가 공개됨')

    def test_reviewed_new_company_name_works_without_dictionary_or_paid_tag_call(self):
        item={'title':'새로운 금융기관 사업', '_review_body_entities':[
            {'name':'한빛디지털금융','kind':'org'}, {'name':'새 회사','kind':'org'},
            {'name':'BTC','kind':'org'}, {'name':'서비스','kind':'org'}]}
        with patch.object(editor,'_call_openai') as paid:
            body,_=editor._inject_inline_tags('한빛디지털금융이 BTC 수탁 서비스를 출시함',item)
        self.assertIn('#한빛디지털금융 이',body)
        self.assertNotIn('#BTC',body)
        self.assertNotIn('#서비스',body)
        self.assertNotIn('새 회사',body)
        paid.assert_not_called()

    def test_entity_hints_survive_source_summary_cache_restart(self):
        item=story(article_text='Hanbit Digital Finance launches XRP custody')
        summary='한빛디지털금융이 XRP 수탁 서비스를 출시함'
        decision={'publish':True,'reason':'source verified',
                  'checks':dict.fromkeys(('faithful','conditions_preserved','allowed_category',
                          'new_substantive_fact','source_sufficient','understandable'),True),
                  'body_entities':[{'name':'한빛디지털금융','kind':'org'}]}
        state={};client=Mock(); client.responses.create.side_effect=[answer(summary),answer(json.dumps(decision))]
        with patch.object(editor,'_RUNTIME',{'OPENAI_MODEL':'gpt-6-luna','openai_client':client}),patch.object(editor,'_is_hard_blocked',return_value=(False,'')):
            for i in range(2):
                candidate=dict(item)
                with cache.review_session(state,lambda:None,lambda x:None):
                    text=editor._rewrite_summary(candidate)
                tagged,_=editor._inject_inline_tags(text,candidate)
                self.assertIn('#한빛디지털금융 이',tagged)
                state=json.loads(json.dumps(state))
        self.assertEqual(client.responses.create.call_count,2)

    def test_sui_exclusion_and_portfolio_adverse_rules_remain(self):
        for title in ("Bitcoin treasury companies get two Anchorage routes into Sui's Hashi",
                      'XRP Ledger critical vulnerability could mint unlimited XRP'):
            with patch.object(editor,'_call_openai') as paid:
                self.assertEqual(editor.build_message(story(title=title)), '')
                paid.assert_not_called()


class IndependentUpdateTests(unittest.TestCase):
    def test_old_dtcc_update_response_is_held_in_full_pipeline(self):
        candidate={'title':'Major Banks Sign on as DTCC Launches Tokenized Securities Service',
                   'url':'https://example.test/repeated-dtcc'}
        history={'first':{'title':'DTCC launches tokenization service','url':'https://example.test/first',
                          'summary':'DTCC가 증권 34종 대상 토큰화 서비스를 출시함'}}
        def respond(prompt):
            data=json.loads(prompt.rsplit('\n',1)[-1])
            if 'related_ids' in prompt:
                return json.dumps({'related_ids':[data['history'][0]['id']]})
            return json.dumps({'decision':'update','matched_id':data['history'][0]['id'],
                'reason':'같은 출시지만 참여사 계약 조치가 추가됨',
                'new_fact':'JP모건·뱅크오브아메리카 등 20개 DTC 참여사가 서비스 이용 계약을 체결했다.'})
        with patch.object(events,'MANUAL_EVENTS',()):
            result=events.review_event(candidate,'DTCC 출시와 20개 참여사의 서비스 이용 계약',history,respond)
        self.assertEqual(result['status'],'hold')

    def test_dtcc_old_fluent_new_fact_is_not_enough(self):
        candidate={'title':'DTCC launches tokenized securities service',
                   'summary':'JP모건 등 20개 참여사가 서비스 이용 계약을 체결함'}
        old={'decision':'update','new_fact':candidate['summary']}
        self.assertFalse(events.valid_update_evidence(old,candidate))
        old.update(independent_new_action=False,candidate_evidence=candidate['summary'])
        self.assertFalse(events.valid_update_evidence(old,candidate))

    def test_invented_quote_or_non_boolean_cannot_pass(self):
        candidate={'summary':'리플이 예비 승인 후 싱가포르에서 서비스를 실제 출시함'}
        for flag,quote in ((True,'원문에 없는 별도 계약이 실제 체결됨'),('true',candidate['summary']), (True,'')):
            self.assertFalse(events.valid_update_evidence({'independent_new_action':flag,'candidate_evidence':quote},candidate))
        self.assertTrue(events.valid_update_evidence({'independent_new_action':True,'candidate_evidence':candidate['summary']},candidate))

    def test_same_launch_conditions_have_explicit_prompt_rule(self):
        prompts=[]
        candidate={'title':'DTCC launches securities service','url':'https://example.test/new'}
        old={'old':{'title':'DTCC securities service launch','url':'https://example.test/old','summary':'DTCC launched securities service'}}
        def respond(prompt):
            prompts.append(prompt)
            data=json.loads(prompt.rsplit('\n',1)[-1])
            if 'related_ids' in prompt:
                return json.dumps({'related_ids':[r['id'] for r in data['history'] if 'DTCC securities' in r['title']]})
            return json.dumps({'decision':'supplement','matched_id':data['history'][0]['id'],'reason':'같은 출시 참여사 설명'})
        result=events.review_event(candidate,'DTCC launched securities service with 20 participants',old,respond)
        self.assertEqual(result['status'],'supplement')
        self.assertIn('옛 계획 기사',prompts[-1])
        self.assertIn('20개 이용 기관',prompts[-1])


class ImageFeedbackTests(unittest.TestCase):
    def test_tokenpost_defaults_removed_without_removing_article_photos(self):
        for url in ('https://www.tokenpost.kr/assets/logo.png', 'https://f1.tokenpost.kr/no_image.webp',
                    'https://tokenpost.kr/static/default-image.jpg'):
            self.assertTrue(images.publisher_placeholder_url(url))
        for url in ('https://f1.tokenpost.kr/2026/10/article123.webp','https://company.example/logo.png'):
            self.assertFalse(images.publisher_placeholder_url(url))
        urls=images.image_candidates({'url':'https://tokenpost.kr/news/1', 'image_url':'https://tokenpost.kr/assets/logo.png'},
                                    lambda *a: b'<article><img src="/article-photo.jpg"></article>')
        self.assertEqual(urls,['https://tokenpost.kr/article-photo.jpg'])

    def test_publisher_logo_check_is_required_and_fail_closed(self):
        for mode in ('missing','false','true'):
            checks=dict.fromkeys(images.IMAGE_CHECKS,True)
            if mode=='missing':checks.pop('not_publisher_placeholder')
            elif mode=='false':checks['not_publisher_placeholder']=False
            client=Mock()
            client.responses.create.return_value=answer(json.dumps({'approved':True,'reason':'image check','checks':checks}))
            approved,_=images.review_image(client,'gpt-6-luna',{'title':'Stellar custody'},'스텔라 수탁',b'fake','image/png')
            self.assertEqual(approved,mode=='true')


class CostBoundaryTests(unittest.TestCase):
    def test_tracking_and_equivalent_time_reuse_across_restart(self):
        state={}; client=Mock();client.responses.create.return_value=answer('SKIP')
        item=story(pub='Thu, 29 Oct 2026 00:00:00 +0000',url='https://example.com/article?id=9&utm_source=rss')
        with patch.object(editor,'_RUNTIME',{'OPENAI_MODEL':'gpt-6-luna','openai_client':client}), patch.object(editor,'_is_hard_blocked',return_value=(False,'')):
            for pub,url in [('Thu, 29 Oct 2026 00:00:00 +0000','https://example.com/article?id=9&utm_source=rss'),
                            ('2026-10-29T09:00:00+09:00','https://example.com/article?id=9&utm_source=telegram#article')]:
                item.update(pub=pub,url=url)
                with cache.review_session(state,lambda:None,lambda x:None):editor._rewrite_summary(item)
                state=json.loads(json.dumps(state));state['ai_review']['entries']={}
            self.assertEqual(client.responses.create.call_count,1)
            item['article_text']+=' New actual source facts.'
            with cache.review_session(state,lambda:None,lambda x:None):editor._rewrite_summary(item)
            self.assertEqual(client.responses.create.call_count,2)

    def test_article_ids_and_unknown_dates_cannot_collide(self):
        self.assertNotEqual(canonical_url('https://x.test/read?id=1'),canonical_url('https://x.test/read?id=2'))
        self.assertNotEqual(canonical_scope({'pub':'2026-10-29'}),canonical_scope({'pub':'2026-10-29T00:00:00Z'}))
        self.assertEqual(canonical_url('https://x.test/read?tag=one&tag=two'),'https://x.test/read?tag=one&tag=two')

    def test_policy_change_does_not_inherit_previous_editorial_decisions(self):
        cache.compatible_identity.cache_clear()
        self.assertFalse(cache.compatible_identity())
        scope={'source':'old'};key=cache.fingerprint([cache.VERSION,'8e16077f3b63ea3c01b110d1b5d87e2fd50ae4ecba9036d49b3841e55116169d','source_summary',scope])
        with cache.review_session({},lambda:None,lambda x:None) as store:
            store.data['content_results_v1']={key:{'result':{'summary':'old approval'},'expires':time.time()+1000}}
            self.assertIsNone(cache.content_result('source_summary',scope))

    def test_scope_guidance_precedes_article_and_is_present_once(self):
        prompt=editor._summary_prompt('UNIQUE_TITLE','UNIQUE_SOURCE')
        self.assertEqual(prompt.count(editor.PORTFOLIO_GUIDANCE),1)
        self.assertLess(prompt.index(editor.PORTFOLIO_GUIDANCE),prompt.index('UNIQUE_TITLE'))
        self.assertIn('수이 이름을 지우고',prompt)
        self.assertIn('기관 전체 관리규모',prompt)


if __name__=='__main__':unittest.main()
