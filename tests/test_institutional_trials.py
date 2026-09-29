"""Institutional trial headlines, stage preservation, and silent cutover."""
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch

import doorinews_editor as e
from news_quality import (institutional_intake_reason, institutional_scope_reason,
                          INSTITUTIONAL_TRIALS_ENABLED_AT, INSTITUTIONAL_SERVICES_ENABLED_AT,
                          INSTITUTIONAL_ENABLED_AT)

TITLE = "'규제에 발목잡힌' 韓 금융권, 해외서 토큰화 실험…\"뒤처지기 싫었다\""
SOURCE = ('금융사 관계자들이 행사에 참석해 실제 사업 현황을 설명했다. '
          '미래에셋자산운용은 기존 제휴로 해외 ETF 토큰화 사업을 운영 중이며 '
          '한화자산운용은 국내 ETF 토큰화를 준비하고 미국 자산 토큰화에 참여하고 있다고 밝혔다.')


def story(title=TITLE, **kw):
    return {'title': title, 'pub': datetime.now(timezone.utc).isoformat(), **kw}


def verdict(**overrides):
    checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                            'new_substantive_fact', 'source_sufficient', 'understandable'), True)
    checks.update(overrides)
    return json.dumps({'publish': True, 'reason': '원문 검수', 'checks': checks})


class InstitutionalTrialsTests(unittest.TestCase):
    def test_real_headline_and_equivalent_stages_enter_review(self):
        for title in (TITLE, '국내 금융사, 해외 토큰화 실험', '은행, 토큰화 시범사업 준비',
                      '금융권, 디지털자산 플랫폼 실증', '금융사, 토큰화 사업 확대',
                      '한화자산운용, ETF 토큰화 준비',
                      'Financial firms test tokenized funds',
                      'Financial sector prepares tokenization pilot',
                      'Banks experiment with tokenized deposits'):
            with self.subTest(title=title):
                self.assertTrue(e.matches_keywords(story(title), [], [], []))

    def test_event_source_does_not_mask_real_business_or_bypass_ad_rules(self):
        self.assertFalse(e._is_hard_blocked(story(article_text=SOURCE))[0])
        for title, source in (
                ('금융권, 토큰화 컨퍼런스 연사 참석', ''),
                ('Financial firms attend tokenization conference as speakers', ''),
                (TITLE, 'Sponsored content: tokenization trials.'),
                (TITLE, 'Sign up using referral code ABC.')):
            self.assertTrue(e._is_hard_blocked(story(title, article_text=source))[0])

    def test_unrelated_trials_and_speculative_headlines_stay_out(self):
        for title in ('금융권, 신규 예금 상품 실험', '제조업체, 토큰화 실험 준비',
                      '금융권, 토큰화 시범사업 가능성 전망', '금융사는 토큰화를 준비해야 한다',
                      'Financial firms could prepare tokenization products',
                      'Financial firms test tokenized funds: price prediction',
                      '은행 토큰화 컨퍼런스 개최 준비'):
            self.assertFalse(e.matches_keywords(story(title), [], [], []))

    def test_new_matches_keep_past_queue_silent(self):
        for pub in ('', 'bad', '2026-09-29T20:00:00', '2099-01-01T00:00:00Z',
                    INSTITUTIONAL_TRIALS_ENABLED_AT.isoformat(),
                    (INSTITUTIONAL_TRIALS_ENABLED_AT - timedelta(seconds=1)).isoformat()):
            self.assertFalse(e.matches_keywords(story(pub=pub), [], [], []))

    def test_previous_categories_keep_their_existing_cutoffs(self):
        for title, cutoff in (
                ('Mirae Asset expands tokenization business', INSTITUTIONAL_ENABLED_AT),
                ('SWIFT connects banks through tokenized deposits', INSTITUTIONAL_SERVICES_ENABLED_AT)):
            self.assertEqual(institutional_intake_reason(
                story(title, pub=(cutoff + timedelta(seconds=1)).isoformat())), '')
        self.assertFalse(institutional_scope_reason(story(), trials=False))

    def test_manual_article_never_calls_ai_even_with_changed_date(self):
        for url in ('https://bloomingbit.io/feed/news/121214',
                    'https://www.bloomingbit.io/feed/news/121214/?utm_source=rss'):
            with patch.object(e, '_call_openai') as ai:
                self.assertEqual(e.build_message(story(url=url, article_text=SOURCE)), '')
                ai.assert_not_called()

    def test_stage_and_substantive_fact_review_still_controls_publication(self):
        summary = '미래에셋이 해외 ETF 토큰화 사업을 운영 중이며 한화자산운용은 국내 ETF 토큰화를 준비하고 있다고 밝힘'
        with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[summary, verdict()]):
            caption = e.build_message(story(article_text=SOURCE))
        self.assertIn('해외 ETF', caption.replace('#', ''))
        self.assertIn('준비', caption)
        self.assertTrue(caption.endswith(' '.join(e.FIXED_FOOTER_TAGS)))
        for failed_check in ('conditions_preserved', 'new_substantive_fact', 'allowed_category'):
            with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai',
                    side_effect=[summary, verdict(**{failed_check: False})]):
                self.assertEqual(e.build_message(story(article_text=SOURCE)), '')


if __name__ == '__main__':
    unittest.main()
