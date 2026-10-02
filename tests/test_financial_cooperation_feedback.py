"""Institutional business and payment demos; model decisions are mocked."""
from datetime import datetime, timezone, timedelta
import json
import unittest
from unittest.mock import patch

import doorinews_editor as e
import news_quality as q
from news_event_review import history_records, review_event


KY = '교보생명, 서클·SBI와 스테이블코인·RWA 사업화 추진'
XRPL = 'Confirmed: XRP Ledger Can Be Used to Send ISO 20022 Payments for Banks'
SBI = 'SBI wants stablecoin QR payments for Japan-Korea travel'
SBI_SOURCE = ('SBI DigiTrust, NICE and DSRV are testing stablecoin QR payments '
              'for Japanese travelers in South Korea, with results due by December.')


def story(title, **kw):
    return dict(title=title, pub=datetime.now(timezone.utc).isoformat(), **kw)


def verdict(**changes):
    checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                           'new_substantive_fact', 'source_sufficient', 'understandable'), True)
    checks.update(changes)
    return json.dumps(dict(publish=True, reason='stage checked', checks=checks))


class FinancialCooperationFeedback(unittest.TestCase):
    def test_new_institutions_and_payment_projects_qualify(self):
        for title in (KY, '한빛생명, 스테이블코인 결제 사업화 추진',
                      'Insurance company plans stablecoin settlement business',
                      'Example insurer announces RWA tokenization platform',
                      '금융기관, 스테이블코인 기술검증 협력 논의'):
            with self.subTest(title=title):
                self.assertTrue(e.matches_keywords(story(title), [], [], []))
        for title in (SBI, 'Example Bank wants stablecoin QR payments for travelers'):
            self.assertTrue(e.matches_keywords(story(title, desc=SBI_SOURCE), [], [], []))
        self.assertTrue(e.matches_keywords(story(XRPL, desc='A new video demonstrates XRPL accounting integration.'), [], [], []))

    def test_aspirations_ads_and_unrelated_finance_still_excluded(self):
        for candidate in (story(SBI), story(SBI, desc='Investors hope it could happen someday.'),
                          story('보험사, 여성리더 육성과정 실시'),
                          story('보험사, 스테이블코인 포럼 연사 참가'),
                          story('Example insurer predicts stablecoin price rally'),
                          story('Top ISO 20022 coins to buy now')):
            with self.subTest(title=candidate['title']):
                self.assertFalse(e.matches_keywords(candidate, [], [], []))

    def test_new_scope_does_not_release_old_queue(self):
        for title, desc in ((KY, ''), (SBI, SBI_SOURCE)):
            candidate = story(title, desc=desc)
            candidate['pub'] = (q.FINANCIAL_COOPERATION_ENABLED_AT-timedelta(seconds=1)).isoformat()
            self.assertIn('범위 확대 전', q.institutional_intake_reason(candidate))
            candidate['pub'] = (q.FINANCIAL_COOPERATION_ENABLED_AT+timedelta(seconds=1)).isoformat()
            self.assertEqual(q.institutional_intake_reason(candidate), '')
        # Existing institutional category retains its earlier cutoff.
        candidate = story('Morgan Stanley launches digital asset business')
        candidate['pub'] = (q.INSTITUTIONAL_ENABLED_AT+timedelta(seconds=1)).isoformat()
        self.assertEqual(q.institutional_intake_reason(candidate), '')

    def test_summary_keeps_demo_discussion_and_testing_stages(self):
        cases = (
            (KY, '교보생명은 서클·SBI·비댁스와 스테이블코인 및 실물연계자산 사업화와 기술검증 협력 방안을 논의했다.',
             '교보생명이 서클·SBI·비댁스와 스테이블코인 및 실물연계자산 사업화를 위한 기술검증 협력 방안을 논의했다고 밝힘', '논의'),
            (XRPL, 'A new video demonstrates XRPL accounting integration by converting payment data to ISO 20022 and importing it into accounting software.',
             'XRPL 결제 정보를 은행 결제 메시지 형식인 ISO 20022로 변환해 기존 회계 프로그램에 넣는 기술 시연이 공개됐다고 전함', '시연'),
            (SBI, SBI_SOURCE,
             'SBI가 NICE정보통신·DSRV와 방한 일본 여행객의 스테이블코인 QR 결제를 공동 검증 중이며 12월까지 결과를 낼 예정이라고 밝힘', '검증'),
        )
        for title, source, summary, stage in cases:
            with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[summary, verdict()]) as model:
                caption = e.build_message(story(title, article_text=source))
                self.assertIn(stage, caption)
                self.assertTrue(caption.endswith(' '.join(e.FIXED_FOOTER_TAGS)))
                self.assertEqual(model.call_count, 2)
                for call in model.call_args_list:
                    self.assertIn(e.ADOPTION_RESEARCH_GUIDANCE, call.args[0])
                if title == KY:
                    self.assertIn('#교보생명', caption)
            for check in ('faithful', 'conditions_preserved', 'source_sufficient', 'new_substantive_fact'):
                with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[summary, verdict(**{check: False})]):
                    self.assertEqual(e.build_message(story(title, article_text=source)), '')

    def test_confirmed_team_articles_only_are_remembered(self):
        urls = ('https://timestabloid.com/confirmed-xrp-ledger-can-be-used-to-send-iso-20022-payments-for-banks/',
                'https://bloomingbit.io/feed/news/121453')
        for url in urls:
            self.assertTrue(q.manual_post_reason(dict(url=url)))
            self.assertTrue(any(r.get('url') == url for r in history_records({})))
        self.assertFalse(q.manual_post_reason(dict(url='https://crypto.news/sbi-wants-stablecoin-qr-payments-for-japan-korea-travel/')))
        # A later real launch can be an update to the same demo, not a topic ban.
        row = next(r for r in history_records({}) if r['url'] == urls[0])
        def respond(prompt):
            if 'related_ids' in prompt:
                return json.dumps(dict(related_ids=[row['id']]))
            return json.dumps(dict(decision='update', matched_id=row['id'], reason='new deployment',
                                   new_fact='A named bank has now launched the previously demonstrated integration.'))
        result = review_event(story('Named bank launches XRPL accounting integration', url='https://example.test/new-launch'),
                              'A named bank launched the integration after the demonstration.', {}, respond)
        self.assertEqual(result['status'], 'update')

    def test_review_failures_are_diagnosable_and_fail_closed(self):
        logs = []
        for response in ('not json', '[]', verdict(conditions_preserved=False),
                         json.dumps(dict(publish=True, reason='missing checks'))):
            with patch.object(e, '_RUNTIME', {'log': logs.append}), patch.object(e, '_call_openai', return_value=response):
                self.assertFalse(e._validate_summary_against_source('title', 'source', 'summary'))
        self.assertTrue(any('conditions_preserved' in line for line in logs))
        self.assertTrue(any('JSON 응답 해석 실패' in line for line in logs))


if __name__ == '__main__':
    unittest.main()
