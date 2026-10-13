import unittest
from unittest.mock import patch
import doorinews_editor as e


SCREENSHOT = ('KB국민카드와 일본 SBI홀딩스가 이버스핀, SBI이버스핀과 업무협약을 맺고 '
              '일본인 관광객의 한국 가맹점 스테이블코인 결제와 사용자를 대신해 거래하는 '
              'AI 에이전트의 신원·권한 확인을 시험하기로 했다. '
              '상용 출시일과 지원 스테이블코인은 정해지지 않았다')


class KbSummaryStyleTests(unittest.TestCase):
    def test_reported_caption_is_tagged_and_both_sentences_are_styled(self):
        story = {'title': 'KB국민카드 SBI stablecoin payment pilot', 'url': 'https://example.com/kb'}
        with patch.object(e, '_is_hard_blocked', return_value=(False, '')), \
             patch.object(e, '_rewrite_summary', return_value=SCREENSHOT):
            caption = e.build_message(story)
        body = caption.split('🌐')[0]
        self.assertIn('#KB국민카드 와', body)
        self.assertIn('시험하기로 했음\n\n', body)
        self.assertIn('정해지지 않았음', body)
        self.assertNotIn('했다', body)
        self.assertNotIn('않았다', body)
        self.assertNotIn('밝힘', body)
        self.assertTrue(caption.endswith(' '.join(e.FIXED_FOOTER_TAGS)))

    def test_card_aliases_are_one_entity_and_not_bank(self):
        for alias in ('KB국민카드', 'KB 국민카드', 'KB 국민 카드', '국민카드', 'KB Kookmin Card', 'Kookmin Card'):
            with self.subTest(alias=alias):
                body, selected = e._inject_inline_tags(alias + '와 결제 실험을 진행함', {'title': alias})
                self.assertIn('#KB국민카드 와', body)
                self.assertNotIn('#KB국민은행', body)
                self.assertEqual([s.label for s in selected].count('KB국민카드'), 1)
        body, _ = e._inject_inline_tags('KB국민은행과 협약함', {'title': 'KB국민은행'})
        self.assertNotIn('#KB국민카드', body)

    def test_quotes_decimals_versions_and_attribution_survive(self):
        raw = '기관은 "출시하지 않았다. 조건은 같다"고 밝혔다. 2.7%와 V2.1 조건은 정해지지 않았다.'
        out = e._clean_summary(raw)
        self.assertIn('"출시하지 않았다. 조건은 같다"고 밝힘', out)
        self.assertIn('2.7%와 V2.1 조건은 정해지지 않았음', out)
        self.assertEqual(out.count('\n\n'), 1)
        self.assertEqual(e._clean_summary(out), out)

    def test_negation_tense_and_indirect_speech_are_preserved(self):
        for raw, wanted in (
            ('출시했다고 설명했다.', '출시했다고 설명함'),
            ('출시할 수 있다고 밝혔다.', '출시할 수 있다고 밝힘'),
            ('승인되지 않았다.', '승인되지 않았음'),
            ('출시하지 않는다.', '출시하지 않음'),
            ('승인 조건이 있습니다.', '승인 조건이 있음'),
            ('계획은 미정이다.', '계획은 미정임'),
            ('서비스를 제공한다.', '서비스를 제공함'),
        ):
            self.assertEqual(e._clean_summary(raw), wanted)
        self.assertEqual(e._clean_summary('• 시험하기로 했다.\n• 출시일은 정해지지 않았다.'),
                         '• 시험하기로 했음\n\n• 출시일은 정해지지 않았음')


if __name__ == '__main__':
    unittest.main()
