"""All-source comparison pipeline; model decisions mocked, no live posting."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import news_event_review as n
from news_publication import prepare_publication


class GeneralEventReview(unittest.TestCase):
    def setUp(self):
        self.story = dict(title='새로운 알파 결제망 출시', url='https://new.example/alpha',pub='2026-09-30T00:00:00Z')
        self.caption = '알파 기업이 결제망을 출시했다고 밝힘'
        self.history = {'old':dict(title='Alpha launches payments network',url='https://old.example/a',summary='Alpha launched payment network')}

    def model(self, decision, new_fact=''):
        def respond(prompt):
            payload = json.loads(prompt[prompt.index('{"candidate"'):])
            if 'related_ids' in prompt:
                ids = [r['id'] for r in payload['history'] if 'Alpha launches' in r['title']]
                return json.dumps({'related_ids':ids})
            return json.dumps(dict(decision=decision,matched_id=payload['history'][0]['id'],reason='사건과 진행 단계 대조',new_fact=new_fact))
        return Mock(side_effect=respond)

    def test_unlisted_topic_and_cross_language_uses_general_review(self):
        for decision in ('duplicate','supplement','new','uncertain'):
            result = n.review_event(self.story,self.caption,self.history,self.model(decision))
            self.assertEqual(result['status'],'hold' if decision == 'uncertain' else decision)

    def test_every_history_entry_scanned_even_with_empty_signatures(self):
        history = {str(i):dict(title=f'Other topic {i}',url=f'https://old.example/{i}',signature='') for i in range(321)}
        prompts=[]
        def model(prompt):
            prompts.append(prompt)
            return '{"related_ids":[]}'
        self.assertEqual(n.review_event(self.story,self.caption,history,model)['status'],'new')
        entries=[]
        for prompt in prompts:
            payload=json.loads(prompt[prompt.index('{"candidate"'):])
            entries.extend(r['title'] for r in payload['history'])
        self.assertEqual(len([t for t in entries if t.startswith('Other topic')]),321)
        self.assertIn(n.MANUAL_EVENTS[0][1],entries)

    def test_update_requires_valid_old_record_and_concrete_new_fact(self):
        self.assertEqual(n.review_event(self.story,self.caption,self.history,self.model('update'))['status'],'hold')
        self.assertEqual(n.review_event(self.story,self.caption,self.history,self.model('update','별도 지역에서 실제 출시'))['status'],'update')

    def test_invalid_or_unavailable_search_cannot_publish(self):
        for answer in ('', 'SKIP', '{}', '{"related_ids":["invented-id"]}', '{"related_ids":"bad"}'):
            self.assertEqual(n.review_event(self.story,self.caption,self.history,lambda p:answer)['status'],'hold')

    def test_invalid_final_decision_cannot_publish(self):
        for answer in ('{}','not json','{"decision":"duplicate","matched_id":"fake","reason":"x"}'):
            calls=0
            def model(prompt):
                nonlocal calls
                calls+=1
                if calls==1:
                    index=json.loads(prompt[prompt.index('{"candidate"'):])['history']
                    return json.dumps({'related_ids':[index[0]['id']]})
                return answer
            self.assertEqual(n.review_event(self.story,self.caption,self.history,model)['status'],'hold')

    def test_manual_examples_are_evidence_not_topic_bans(self):
        candidate=dict(self.story,title='Spain amends Form 721 deadline')
        # No static Spain/721 ban: an unrelated/fresh event can reach new verdict.
        self.assertEqual(n.review_event(candidate,self.caption,{},lambda p:'{"related_ids":[]}')['status'],'new')
        first=n.MANUAL_EVENTS[0]
        same=dict(self.story,url=first[0]+'?utm_source=rss')
        model=Mock()
        self.assertEqual(n.review_event(same,self.caption,{},model)['status'],'duplicate')
        model.assert_not_called()

    def test_duplicate_supplement_and_uncertainty_stop_before_image(self):
        caption='뉴스 본문\n\n🌐 <a href="https://t.me/Doorinews">도리뉴스</a>\n\n<a href="https://example.com/a">출처</a>\n\n#BTC #비트코인 #dooridoori #도리도리 #doorinati #도리나티'
        for status in ('duplicate','supplement','hold'):
            image=Mock()
            result=prepare_publication(self.story,lambda s:caption,None,'model',selector=image,event_review=lambda c:dict(status=status,reason='비교 결과'))
            self.assertEqual(result['status'],'held')
            image.assert_not_called()

    def test_new_and_update_can_reach_image_review(self):
        caption='뉴스 본문\n\n🌐 <a href="https://t.me/Doorinews">도리뉴스</a>\n\n<a href="https://example.com/a">출처</a>\n\n#BTC #비트코인 #dooridoori #도리도리 #doorinati #도리나티'
        for status in ('new','update'):
            result=prepare_publication(self.story,lambda s:caption,None,'model',selector=lambda *a:(object(),[]),event_review=lambda c:dict(status=status))
            self.assertEqual(result['status'],'ready')

    def test_context_retained_for_future_cross_source_comparison(self):
        posted={'id':dict(self.story)}
        n.remember_context(posted,self.story,self.caption+'\n🌐 footer')
        self.assertEqual(posted['id']['summary'],self.caption)
        self.assertEqual(posted['id']['source_pub'],self.story['pub'])
        self.assertEqual(n.history_records(posted)[0]['summary'],self.caption)

    def test_live_main_uses_review_and_saves_only_after_send(self):
        source=(Path(__file__).resolve().parents[1]/'doorinews_bot.py').read_text(encoding='utf-8')
        main=[node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='main'][-1]
        part=ast.get_source_segment(source,main)
        self.assertIn('event_review=lambda caption: review_article_event(story, caption, posted)',part)
        self.assertGreater(part.index('remember_context('),part.index('if ok:'))

    def test_live_batch_reviews_against_successful_delivery_and_holds_repeat(self):
        source=(Path(__file__).resolve().parents[1]/'doorinews_bot.py').read_text(encoding='utf-8')
        main=[node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='main'][-1]
        stories=[dict(title='Alpha launches payments network',url='https://first.example/a'),self.story]
        caption=self.caption+'\n\n🌐 <a href="https://t.me/Doorinews">도리뉴스</a>\n\n<a href="https://example.com/a">출처</a>\n\n#BTC #비트코인 #dooridoori #도리도리 #doorinati #도리나티'
        for delivered in (True,False):
            state={'posted':{}}
            sender=Mock(return_value=delivered)
            reviewed=[]
            def review(story,body,posted):
                reviewed.append([r.get('summary') for r in posted.values()])
                return n.review_event(story,body,posted,self.model('duplicate'))
            def register(title,posted,url,*args):
                posted[url]=dict(title=title,url=url)
            def prepare(story,build,client,model,**kwargs):
                return prepare_publication(story,build,client,model,selector=lambda *a:(object(),[]),**kwargs)
            ns={'log':Mock(),'load_state':lambda p:state,'STATE_FILE':'unused',
                'prune_posted_older_than':lambda p,days:p,'save_state':Mock(),
                'collect_new_sources':lambda *a:[], 'http_get':Mock(),
                'FEEDS':[('feed','url',False)],'_feed_unpack_final':lambda f:f,
                'fetch_rss':lambda *a,**k:stories,'MAX_ITEMS_PER_FEED':2,
                'matches_keywords':lambda *a:True,'PORTFOLIO_COINS':[],'ECON_KEYWORDS':[],'KOREAN_KEYWORDS':[],
                'build_story_signature':lambda s:'','build_canonical_topic_key':lambda s:'',
                'normalize_for_duplicate':lambda t:t,'is_canonical_duplicate':lambda *a:False,
                'is_duplicate':lambda *a:False,'is_semantically_duplicate':lambda *a:False,
                'INITIAL_RUN':False,'POST_ENABLED':True,'DRY_RUN_RECORD':False,
                'prepare_publication':prepare,'build_message':lambda s:caption,
                'review_article_event':review,'remember_context':n.remember_context,
                'openai_client':None,'OPENAI_MODEL':'m','send_reviewed_photo':sender,
                'TELEGRAM_BOT_TOKEN':'t','TELEGRAM_CHANNEL_ID':'c','update_posted':register,
                'time':SimpleNamespace(sleep=lambda *a:None)}
            exec(compile(ast.Module(body=[main],type_ignores=[]),'<live main>','exec'),ns)
            ns['main']()
            self.assertEqual(sender.call_count,1 if delivered else 2)
            self.assertEqual(len(state['posted']),1 if delivered else 0)
            self.assertEqual(reviewed[0],[])
            self.assertEqual(reviewed[1],[self.caption] if delivered else [])


if __name__ == '__main__':
    unittest.main()
