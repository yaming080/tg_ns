"""Tax reporting intake and source-grounded explanations through formatting."""
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch

import doorinews_editor as e
from news_quality import TAX_REPORTING_ENABLED_AT

TITLE = 'Spain says self-custody crypto does not need Form 721 reporting'
URL = 'https://crypto.news/spain-says-self-custody-crypto-does-not-need-form-721-reporting/'
SOURCE = ('Spanish tax authorities clarified that crypto whose private keys are controlled '
          'by the user is excluded from Form 721, the declaration of virtual currencies '
          'held abroad. This does not remove other tax obligations.')
SUMMARY = ('스페인 세무당국이 개인키를 직접 관리하는 암호화폐는 해외 보관 암호화폐 신고 서식인 '
           '양식 721의 신고 대상에서 제외되며 다른 납세 의무는 유지된다고 설명함')


def story(title=TITLE, **extra):
    return dict(title=title, pub=datetime.now(timezone.utc).isoformat(), **extra)


def verdict(**overrides):
    checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                            'new_substantive_fact', 'source_sufficient', 'understandable'), True)
    checks.update(overrides)
    return json.dumps({'publish': True, 'reason': '원문 대조 결과', 'checks': checks})


class TaxReportingAndTermsTests(unittest.TestCase):
    def test_official_reporting_headlines_enter_review_without_portfolio_ticker(self):
        for title in (TITLE, 'Spanish tax authorities clarify cryptocurrency declaration requirements',
                      '스페인 세무당국, 개인키 직접 관리 암호화폐 신고 대상 제외 안내',
                      'Government announces digital asset tax reporting exemption'):
            with self.subTest(title=title):
                self.assertTrue(e.matches_keywords(story(title), [], [], []))

    def test_tax_tips_rumors_and_unrelated_reporting_do_not_expand_scope(self):
        for title in ('How to file crypto taxes in Spain', 'Spain crypto tax reporting guide',
                      'Analyst says crypto should be tax exempt', 'Spain could exempt crypto from tax',
                      'Spain says overseas property needs reporting', '스페인 암호화폐 절세 팁 안내'):
            with self.subTest(title=title):
                self.assertFalse(e.matches_keywords(story(title), [], [], []))

    def test_new_scope_does_not_release_old_or_undated_queue(self):
        for pub in ('', 'invalid', '2026-09-29T16:00:00', TAX_REPORTING_ENABLED_AT.isoformat(),
                    (TAX_REPORTING_ENABLED_AT - timedelta(hours=1)).isoformat()):
            item = story(); item['pub'] = pub
            self.assertFalse(e.matches_keywords(item, [], [], []))

    def test_user_confirmed_manual_article_never_calls_ai(self):
        for url in (URL, URL.replace('crypto.news', 'www.crypto.news') + '?utm_source=rss'):
            with patch.object(e, '_call_openai') as ai:
                self.assertEqual(e.build_message(story(url=url, article_text=SOURCE)), '')
                ai.assert_not_called()

    def test_explanation_and_key_conditions_survive_caption_formatting(self):
        with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai',
                side_effect=[SUMMARY, verdict()]):
            caption = e.build_message(story(url='https://example.com/new-ruling', article_text=SOURCE))
        self.assertIn('해외 보관 암호화폐 신고 서식인', caption)
        self.assertIn('개인키를 직접 관리', caption)
        self.assertIn('다른 납세 의무', caption)
        self.assertIn('#스페인', caption)
        self.assertIn('#BTC #비트코인 #dooridoori #도리도리 #doorinati #도리나티', caption)

    def test_compressed_summary_is_reviewed_with_definition_and_conditions(self):
        with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai',
                side_effect=[SUMMARY + ' 관련 배경 설명' * 30, SUMMARY, verdict()]) as ai:
            self.assertEqual(e._rewrite_summary(story(article_text=SOURCE)), SUMMARY)
            self.assertEqual(ai.call_count, 3)
            self.assertIn(SUMMARY, ai.call_args.args[0])

    def test_unclear_invented_or_overbroad_explanations_and_old_guidance_stay_held(self):
        for check, summary in (
                ('understandable', '스페인이 암호화폐 양식 721 제외를 안내함'),
                ('faithful', '스페인이 소득세 면제 증명서인 양식 721의 제외를 안내함'),
                ('conditions_preserved', '스페인이 개인 보유 암호화폐의 모든 납세 의무를 면제함'),
                ('new_substantive_fact', SUMMARY)):
            with self.subTest(check=check), patch.object(e, '_RUNTIME', {}), patch.object(
                    e, '_call_openai', side_effect=[summary, verdict(**{check: False})]):
                self.assertEqual(e.build_message(story(article_text=SOURCE)), '')


if __name__ == '__main__':
    unittest.main()
