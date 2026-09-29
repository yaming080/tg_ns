"""Regressions for collected-but-excluded ECB and Brandt stories."""
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch
import doorinews_editor as e
from news_quality import (EDITORIAL_EXPANSION_ENABLED_AT, cbdc_scope_reason,
                          attributed_view_scope_reason)

BRANDT = 'Peter Brandt Names Stellar (XLM) as Long-Shot Crypto Pick'
ECB = 'ECB puts AI agent payments on the digital euro drawing board'


def story(title, **kw):
    return {'title': title, 'pub': datetime.now(timezone.utc).isoformat(), **kw}


def verdict(**kw):
    checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                            'new_substantive_fact', 'source_sufficient', 'understandable'), True)
    checks.update(kw)
    return json.dumps({'publish': True, 'reason': '원문 대조', 'checks': checks})


class IndustryAndViewsTests(unittest.TestCase):
    def test_collected_titles_and_equivalents_enter_review(self):
        for title in (BRANDT, ECB, 'ECB wants to test AI-powered digital euro payments',
                      'ECB, 디지털유로에 AI 에이전트 결제 도입 검토…내년 실증 착수',
                      'European Central Bank recruits firms for digital euro experiments',
                      'Bank of England invites firms to test digital pound payments',
                      '피터 브랜트, 스텔라를 장기 승부수로 지목',
                      'Jane Smith Names Bitcoin as Long-Term Crypto Pick'):
            with self.subTest(title=title):
                self.assertTrue(e.matches_keywords(story(title), [], [], []))

    def test_unrelated_ai_generic_explainers_and_price_calls_stay_out(self):
        for title in ('ECB introduces AI staff training', 'What is the digital euro?',
                      'Analysts name Stellar as long-term crypto pick',
                      'Peter Brandt names XLM as long-term pick with $10 price target',
                      'Peter Brandt says Bitcoin may hit $600K by 2029',
                      'Peter Brandt Names Stellar as Long-Shot Crypto Pick: 500% rally',
                      'Peter Brandt Names Stellar as Long-Shot Crypto Pick: presale',
                      'Arthur Hayes: Robinhood recognizes Ethereum security'):
            self.assertFalse(e.matches_keywords(story(title), [], [], []), title)

    def test_background_chart_does_not_bypass_source_or_ad_checks(self):
        self.assertFalse(e._is_hard_blocked(story(BRANDT, article_text=
            'Veteran trader Peter Brandt called Stellar a long-shot pick. He shared a monthly chart with a resistance level.'))[0])
        for source in ('Sponsored content. Peter Brandt long-shot pick.',
                       'Sign up using referral code ABC.'):
            self.assertTrue(e._is_hard_blocked(story(BRANDT, article_text=source))[0])
        with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai') as ai:
            self.assertEqual(e.build_message(story(BRANDT)), '')
            ai.assert_not_called()

    def test_cutover_does_not_revive_old_or_unknown_dates(self):
        for title in (ECB, BRANDT):
            for pub in ('', 'bad', '2099-01-01T00:00:00Z',
                        EDITORIAL_EXPANSION_ENABLED_AT.isoformat(),
                        (EDITORIAL_EXPANSION_ENABLED_AT-timedelta(seconds=1)).isoformat()):
                self.assertFalse(e.matches_keywords(story(title, pub=pub), [], [], []))

    def test_manual_urls_never_repost(self):
        for title, url in ((BRANDT, 'https://u.today/peter-brandt-names-stellar-xlm-as-long-shot-crypto-pick'),
                           (ECB, 'https://cointelegraph.com/news/ecb-private-firms-ai-agents-digital-euro'),
                           ('Arthur Hayes praises Ethereum', 'https://bloomingbit.io/feed/news/121125')):
            with patch.object(e, '_call_openai') as ai:
                self.assertEqual(e.build_message(story(title, url=url+'/?utm_source=rss')), '')
                ai.assert_not_called()

    def test_source_review_and_attribution_tags(self):
        cases = (
            (BRANDT, 'Veteran trader Peter Brandt newly called Stellar a long-shot crypto pick, a risky bet over the next several years.',
             '피터 브랜트가 스텔라를 향후 수년간의 투자 후보로 꼽으며 위험을 감수하는 선택이라는 개인 의견을 밝힘', '#피터브랜트'),
            (ECB, 'The ECB is inviting firms to explore AI agent payments with the digital euro. Issuance has not been decided.',
             '유럽중앙은행이 디지털유로의 AI 에이전트 결제 활용을 탐색할 참여 기업을 모집하며 발행 여부는 미정이라고 밝힘', '#유럽중앙은행'))
        for title, source, summary, tag in cases:
            with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[summary, verdict()]) as ai:
                caption = e.build_message(story(title, article_text=source))
                self.assertIn(tag, caption)
                self.assertTrue(caption.endswith(' '.join(e.FIXED_FOOTER_TAGS)))
                self.assertTrue(all(e.EDITORIAL_SCOPE_GUIDANCE in call.args[0] for call in ai.call_args_list))
            for check in ('faithful', 'allowed_category', 'new_substantive_fact', 'conditions_preserved'):
                with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[summary, verdict(**{check: False})]):
                    self.assertEqual(e.build_message(story(title, article_text=source)), '')

    def test_industry_adoption_keeps_existing_coverage(self):
        for title in ('Mirae Asset expands tokenization business',
                      'SWIFT connects banks through tokenized deposits',
                      '금융권, 해외 토큰화 실험', 'Circle gains Binance backing in stablecoin race'):
            self.assertTrue(e.matches_keywords(story(title), [], [], []))


if __name__ == '__main__':
    unittest.main()
