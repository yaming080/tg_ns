"""Company/person tags do not create editorial exceptions for metric stories."""
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

import doorinews_editor as e
from news_quality import staking_queue_metric_reason


def story(title, **kw):
    return dict(title=title, pub=datetime.now(timezone.utc).isoformat(), **kw)


class ActorTagsAndQueueMetrics(unittest.TestCase):
    def test_fidelity_inline_tag_preserves_fund_conditions_and_fixed_suffix(self):
        candidate = story('Fidelity explores wider access to its Ethereum tokenized money market fund')
        summary = '피델리티가 이더리움 기반 토큰화 머니마켓펀드의 투자자 자격 확대를 검토 중이며 현재 전문·기관 투자자에 한정되고 최소 투자금은 10만달러라고 밝힘'
        tagged, selected = e._inject_inline_tags(summary, candidate)
        self.assertIn('#피델리티 가', tagged)
        for term in ('검토 중', '전문·기관 투자자', '10만달러'):
            self.assertIn(term, tagged)
        footer = e._build_footer_tags(candidate, selected)
        self.assertIn('#Fidelity', footer)
        self.assertEqual(footer[-6:], list(e.FIXED_FOOTER_TAGS))

    def test_jiang_actor_tag_preserves_particle_and_source_role(self):
        candidate = story('Jiang Zhuoer announces new Bitcoin mining service')
        summary = 'BTC.TOP 설립자 장줘얼이 비트코인 채굴 서비스를 출시했다고 밝힘'
        tagged, selected = e._inject_inline_tags(summary, candidate)
        self.assertIn('BTC.TOP 설립자 #장줘얼 이', tagged)
        self.assertNotIn('#비트코인 ', tagged)
        self.assertIn('#JiangZhuoer', e._build_footer_tags(candidate, selected))
        for alias in ('Jiang Zhuoer', 'Zhuoer Jiang', "Jiang Zhuo'er"):
            tagged, _ = e._inject_inline_tags(alias + ' announced a new mining service', candidate)
            self.assertIn('#장줘얼', tagged)

    def test_staking_queue_counts_are_blocked_regardless_of_speaker(self):
        for title in ('이더리움 출구 대기 85만개…장줘얼 “2026년 최고”',
                      '이더리움 스테이킹 종료 대기 물량 90만 ETH, 예상 대기 기간 15일',
                      'Jiang Zhuoer: ETH exit queue rises to 850,000, 14.77 days',
                      'Ethereum Foundation: ETH withdrawal queue reaches yearly high',
                      'ETH tokens queuing to exit staking surge to 900,000'):
            candidate = story(title, article_text='A founder said the waiting time increased and the exit queue hit a yearly high.')
            with self.subTest(title=title):
                self.assertTrue(staking_queue_metric_reason(candidate))
                self.assertFalse(e.matches_keywords(candidate, [], [], []))
                with patch.object(e, '_call_openai') as model:
                    self.assertEqual(e.build_message(candidate), '')
                    model.assert_not_called()

    def test_real_actions_and_institutional_business_not_blocked_by_metric_rule(self):
        for title in ('이더리움 업그레이드 적용, 출구 대기 처리 한도 2배 확대',
                      'Ethereum protocol upgrade activated to double exit queue capacity',
                      'Ethereum platform resumes withdrawals after 2-day exit queue halt',
                      '피델리티, 이더리움 토큰화 펀드 투자자 자격 확대 검토',
                      '장줘얼, 새 비트코인 채굴 서비스 출시'):
            self.assertEqual(staking_queue_metric_reason(story(title)), '')

    def test_no_fidelity_or_jiang_tags_from_unrelated_text(self):
        text = '이더리움 재단이 새 기술을 발표했다고 밝힘'
        tagged, selected = e._inject_inline_tags(text, story(text))
        self.assertNotIn('#피델리티', tagged)
        self.assertNotIn('#장줘얼', tagged)


if __name__ == '__main__':
    unittest.main()
