"""Institutional business adoption is distinct from analyst price commentary."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import json
import unittest
from unittest.mock import patch

import doorinews_editor as e
from news_quality import (INSTITUTIONAL_ENABLED_AT, INSTITUTIONAL_SCOPE,
                          channel_scope_reason, institutional_intake_reason)

MIRAE_TITLE = '미래에셋, 디지털자산 산업 본격화…"모든 상품 온체인화 목표" [이스트포인트 : 서울 2026]'


def story(title=MIRAE_TITLE, **extra):
    return {'title': title, 'pub': datetime.now(timezone.utc).isoformat(), **extra}


class InstitutionalAdoptionTests(unittest.TestCase):
    def test_institutional_business_announcements_enter_review(self):
        for title in (MIRAE_TITLE,
                      '은행, 디지털자산 사업 진출 계획 발표',
                      '새빛증권, 금융상품 토큰화 사업 확대',
                      '블랙록, 온체인 금융상품 개발 전략 공개',
                      'Mirae Asset expands digital asset business and plans tokenization',
                      'A bank announces tokenized fund platform',
                      'Fidelity launches onchain investment products'):
            with self.subTest(title=title):
                item = story(title)
                self.assertEqual(channel_scope_reason(item), INSTITUTIONAL_SCOPE)
                self.assertTrue(e.matches_keywords(item, [], [], []))

    def test_unrelated_metrics_prices_and_listings_stay_out(self):
        for title in ('미래에셋 TIGER ETF 분배금 425원 지급',
                      '서울 통신비 주요 6개 도시 중 최고 수준',
                      '미래에셋 디지털자산 관련주 목표가 상향',
                      '블랙록, 디지털자산 시장 성장 전망',
                      '아서 헤이즈 "로빈후드, 이더리움 보안성 인정…목표가 5000弗"',
                      '은행, 새로운 모바일 앱 출시',
                      'RIN/USDT trading launches on XT',
                      '온도파이낸스 ONDO 목표가 상향 전망'):
            with self.subTest(title=title):
                self.assertFalse(e.matches_keywords(story(title), [], [], []))

    def test_background_adoption_does_not_rescue_lifestyle_story(self):
        item = story('서울 통신비 비교', article_text='미래에셋은 디지털자산 사업을 확대한다.')
        self.assertFalse(e.matches_keywords(item, [], [], []))

    def test_conference_context_does_not_block_business_announcement(self):
        item = story(article_text='미래에셋은 온도파이낸스와 협력해 ETF 토큰화를 확대한다. '
                     '컨퍼런스에 참석한 상무는 모든 상품의 온체인화를 목표로 추진한다고 밝혔다.')
        self.assertFalse(e._is_hard_blocked(item)[0])
        self.assertTrue(e.matches_keywords(item, [], [], []))
        english = story('Mirae Asset expands tokenization business',
                        article_text='The executive attended a conference and gave a speech about new tokenized products.')
        self.assertFalse(e._is_hard_blocked(english)[0])

    def test_event_promotion_and_ad_disclosures_still_blocked(self):
        for item in (
            story('미래에셋, 디지털자산 컨퍼런스 연사 참석'),
            story('Mirae Asset digital asset conference speaker appearance'),
            story(article_text='Sponsored content: Mirae Asset expands tokenization business.'),
            story(article_text='Register using referral code ABC to claim benefits.'),
            story(article_text='신규 사업과 함께 리워드 프로그램을 소개한다.'),
        ):
            with self.subTest(item=item):
                self.assertTrue(e._is_hard_blocked(item)[0])

    def test_confirmed_manual_article_not_republished(self):
        item = story(url='https://www.bloomingbit.io/feed/news/121132/?utm_source=rss')
        with patch.object(e, '_call_openai') as ai:
            self.assertFalse(e.matches_keywords(item, [], [], []))
            self.assertEqual(e.build_message(item), '')
            ai.assert_not_called()

    def test_old_queue_and_boundary_stay_silent(self):
        for seconds in (-60, 0):
            item = story(pub=(INSTITUTIONAL_ENABLED_AT + timedelta(seconds=seconds)).isoformat())
            self.assertIn('과거 대기열', institutional_intake_reason(item))
            self.assertFalse(e.matches_keywords(item, [], [], []))

    def test_new_dates_accept_iso_and_rss(self):
        date = INSTITUTIONAL_ENABLED_AT + timedelta(seconds=1)
        for value in (date.isoformat(), format_datetime(date),
                      date.astimezone(timezone(timedelta(hours=9))).isoformat()):
            self.assertEqual(institutional_intake_reason(story(pub=value)), '')

    def test_bad_missing_naive_and_future_dates_blocked(self):
        for value in ('', 'bad', '2026-09-28T19:00:00', '2099-01-01T00:00:00Z'):
            self.assertFalse(e.matches_keywords(story(pub=value), [], [], []))

    def test_existing_crypto_categories_not_rebaselined(self):
        for title in ('Circle gains Binance backing in USDC-Tether race',
                      '한국 원화 스테이블코인 유동성 규제 검토 중'):
            self.assertEqual(institutional_intake_reason({'title':title}), '')
            self.assertTrue(e.matches_keywords({'title':title}, [], [], []))

    def test_source_review_can_reject_plan_presented_as_completion(self):
        item = story(article_text='미래에셋은 ETF에 이어 다양한 상품 토큰화를 추진하겠다고 밝혔다.')
        checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                               'new_substantive_fact', 'source_sufficient', 'understandable'), True)
        checks['conditions_preserved'] = False
        with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[
            '미래에셋이 모든 금융상품의 온체인 전환을 완료함',
            json.dumps({'publish':False, 'reason':'계획을 완료로 왜곡', 'checks':checks})]):
            self.assertEqual(e.build_message(item), '')

    def test_reviewed_plan_keeps_company_tags_and_fixed_suffix(self):
        item = story(url='https://example.com/new-announcement',
                     article_text='미래에셋은 ETF에 이어 다양한 상품 토큰화를 추진하겠다고 밝혔다.')
        checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                               'new_substantive_fact', 'source_sufficient', 'understandable'), True)
        with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[
            '미래에셋이 ETF에 이어 다양한 금융상품의 토큰화를 추진한다고 밝힘',
            json.dumps({'publish':True, 'reason':'추진 단계 보존', 'checks':checks})]):
            caption = e.build_message(item)
        self.assertIn('#미래에셋 이', caption)
        self.assertIn('추진', caption)
        self.assertNotIn('완료', caption)
        self.assertTrue(caption.endswith(' '.join(e.FIXED_FOOTER_TAGS)))


if __name__ == '__main__':
    unittest.main()
