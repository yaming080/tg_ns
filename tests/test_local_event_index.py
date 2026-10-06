"""Cross-language recall and bounded cost without live OpenAI calls."""
import json
import unittest
from unittest.mock import Mock, patch
import doorinews_editor as editor
import news_event_index as index
import news_event_review as events


class LocalEventIndexTests(unittest.TestCase):
    def select(self,title,summary,old):
        records=[dict(id=str(i),title=t,summary=s,url=f'https://old.example/{i}') for i,(t,s) in enumerate(old)]
        return index.select_related(dict(title=title,summary=summary,url='https://new.example/a'),
                                    records,editor.local_event_tokens,editor.event_index_version())

    def test_bilingual_actor_and_product_matches_without_shared_words(self):
        examples=[
            ('리플, 싱가포르 결제 라이선스 승인','리플이 결제 서비스 인가를 받았다',
             'Ripple receives payments license approval in Singapore','Full license approved'),
            ('코인베이스, 파생상품 결제 지원','코인베이스가 결제 서비스를 제공한다',
             'Coinbase enables derivatives settlement','Coinbase supports payments'),
            ('피델리티, 펀드 투자자 확대 검토','피델리티의 펀드 사업',
             'Fidelity considers expanding fund access','Fidelity fund investor eligibility'),
            ('메타마스크 지갑 서비스 출시','메타마스크가 지갑을 공개했다',
             'MetaMask launches wallet service','New wallet service'),
        ]
        for title,summary,old_title,old_summary in examples:
            with self.subTest(title=title):
                result=self.select(title,summary,[(old_title,old_summary)])
                self.assertEqual(result['status'],'ok'); self.assertEqual(len(result['records']),1)

    def test_plan_and_actual_launch_are_compared_not_automatically_blocked(self):
        story=dict(title='리플, 한국 결제망 실제 출시',url='https://new.example/a')
        history={'old':dict(title='Ripple plans payment network',summary='Earlier plan for Korea',url='https://old.example/a')}
        def verdict(prompt):
            rows=json.loads(prompt[prompt.index('{"candidate"'):])['history']
            return json.dumps(dict(decision='update',matched_id=rows[0]['id'],reason='Plan became actual launch',new_fact='Confirmed actual launch in Korea'))
        with patch.object(events,'MANUAL_EVENTS',()):
            model=Mock(side_effect=verdict)
            self.assertEqual(events.review_event(story,'리플의 한국 결제 서비스가 출시됐다',history,model)['status'],'update')
            model.assert_called_once()

    def test_cloudflare_is_not_flare(self):
        result=self.select('Cloudflare launches AI payments','클라우드플레어 결제 서비스',
                           [('플레어, 기밀 컴퓨팅 출시','플레어가 비공개 데이터 검증을 지원')])
        self.assertEqual(result['status'],'ok'); self.assertEqual(result['records'],[])
        self.assertFalse(any('플레어'==t.removeprefix('entity_') for t in editor.local_event_tokens({'title':'클라우드플레어'})))

    def test_same_coin_different_actors_and_business_not_a_duplicate(self):
        result=self.select('MetaMask launches ETH wallet','MetaMask wallet for Ethereum',
                           [('Fidelity expands ETH fund','Fidelity fund uses Ethereum')])
        self.assertEqual(result['status'],'ok'); self.assertEqual(result['records'],[])

    def test_generic_action_and_entity_alone_are_not_enough(self):
        result=self.select('Ripple launches payment network','Ripple payment rollout',
                           [('Ripple unveils wallet recovery','Ripple wallet restoration')])
        self.assertEqual(result['status'],'ok'); self.assertEqual(result['records'],[])

    def test_overflow_holds_without_full_history_api_fallback(self):
        history={str(i):dict(title=f'Ripple payment agreement {i}',summary='Ripple payments',url=f'https://old.example/{i}') for i in range(13)}
        with patch.object(events,'MANUAL_EVENTS',()):
            model=Mock()
            result=events.review_event(dict(title='Ripple payments launch',url='https://new.example/a'),'Ripple payments in Korea',history,model)
        self.assertEqual(result['status'],'hold'); model.assert_not_called()

    def test_long_evidence_not_silently_truncated(self):
        result=self.select('Ripple payments','Ripple payments',
                           [('Ripple payment plan','Ripple payments '+('word '*4000))])
        self.assertEqual(result['status'],'hold')

    def test_unidentified_subject_holds_when_retrieval_cannot_verify(self):
        result=self.select('Unknown new undertaking','Something has happened',
                           [('다른 언어의 미확인 사업','기존 기록')])
        self.assertEqual(result['status'],'hold')

    def test_same_title_cross_url_retrieved_even_without_known_alias(self):
        result=self.select('Zypher rolls out privacy network','New encrypted private transfers',
                           [('Zypher rolls out privacy network','Encrypted transfers')])
        self.assertEqual(result['status'],'ok'); self.assertEqual(len(result['records']),1)

    def test_local_failure_never_falls_back_to_paid_full_history_scan(self):
        model=Mock()
        with patch.object(events,'select_related',side_effect=ValueError('broken index')):
            result=events.review_event(dict(title='Ripple payments',url='https://new.example/a'),'Ripple payments',{},model)
        self.assertEqual(result['status'],'hold'); model.assert_not_called()
