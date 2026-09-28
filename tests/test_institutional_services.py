"""Regressions from the September 29 manual channel corrections."""
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

import doorinews_editor as e
from news_quality import (institutional_scope_reason, institutional_intake_reason,
                          INSTITUTIONAL_SERVICES_ENABLED_AT, INSTITUTIONAL_ENABLED_AT)

ORACLE = 'Tech giant Oracle integrates with SWIFT blockchain ledger to connect banks tokenized deposits'
FRANKLIN = 'Breaking: Franklin Templeton Partners With Bybit To Offer Tokenized Money Market Funds'
COLLECTED = ('Franklin Templeton brings $687M tokenized fund to Bybit',
             'Bybit Adds Franklin Templeton Tokenized Money Market Fund Shares as Off-Exchange Collateral')

def story(title, **kw):
    return dict(title=title, pub=datetime.now(timezone.utc).isoformat(), **kw)


class InstitutionalServicesTests(unittest.TestCase):
    def test_reported_and_collected_headlines_enter_review(self):
        for title in (ORACLE, FRANKLIN, *COLLECTED,
                      '씨티그룹, 토큰화 예금 결제 서비스 지원',
                      '프랭클린템플턴, 토큰화 펀드 담보 활용 지원',
                      'SWIFT connects banks through tokenized deposits'):
            with self.subTest(title=title):
                self.assertTrue(institutional_scope_reason(story(title)))
                self.assertTrue(e.matches_keywords(story(title), [], [], []))

    def test_unrelated_products_and_speculation_stay_out(self):
        for title in ('Oracle launches a new database product',
                      '은행 신규 예금 상품 출시', 'Bybit adds RIN/USDT spot trading',
                      'Franklin Templeton tokenized fund price prediction',
                      'SWIFT network partners choose XFP Ledger',
                      'Oracle predicts tokenized deposits could boost prices'):
            with self.subTest(title=title):
                self.assertFalse(e.matches_keywords(story(title), [], [], []))

    def test_existing_backlog_for_new_matches_is_not_released(self):
        for title in (ORACLE, *COLLECTED):
            for delta in (-1, 0):
                item = story(title)
                item['pub'] = (INSTITUTIONAL_SERVICES_ENABLED_AT + timedelta(seconds=delta)).isoformat()
                self.assertIn('과거 대기열', institutional_intake_reason(item))
                self.assertFalse(e.matches_keywords(item, [], [], []))

    def test_old_supported_category_keeps_original_cutoff(self):
        item = story('Mirae Asset expands tokenization business')
        item['pub'] = (INSTITUTIONAL_ENABLED_AT + timedelta(seconds=1)).isoformat()
        self.assertEqual(institutional_intake_reason(item), '')

    def test_confirmed_manual_urls_never_repost_even_with_changed_date(self):
        paths = (('cryptobriefing.com', 'tech-giant-oracle-integrates-with-swift-blockchain-ledger-to-connect-banks-tokenized-deposits'),
                 ('coingape.com', 'breaking-franklin-templeton-partners-with-bybit-to-offer-tokenized-money-market-funds'))
        for host, path in paths:
            item = story(ORACLE if host == 'cryptobriefing.com' else FRANKLIN,
                         url=f'https://www.{host}/{path}/?utm_source=rss')
            with patch.object(e, '_call_openai') as ai:
                self.assertFalse(e.matches_keywords(item, [], [], []))
                self.assertEqual(e.build_message(item), '')
                ai.assert_not_called()

    def test_citi_aliases_tag_name_and_separate_particle(self):
        for alias in ('씨티그룹', '시티그룹', '씨티', 'Citi', 'Citigroup'):
            body, selected = e._inject_inline_tags(alias + '과 코인베이스가 결제를 지원함',
                                                  story('Citigroup and Coinbase support stablecoin payments'))
            self.assertIn('#씨티그룹 과', body)
            footer = e._build_footer_tags({}, selected)
            self.assertIn('#Citigroup', footer)
            self.assertNotIn('#City', footer)
            self.assertEqual(footer[-6:], list(e.FIXED_FOOTER_TAGS))

    def test_oracle_swift_and_bybit_aliases_are_tagged(self):
        body, selected = e._inject_inline_tags('오라클이 스위프트와 토큰화 예금을 연결함', story(ORACLE))
        self.assertIn('#오라클 이', body)
        self.assertIn('#스위프트 와', body)
        self.assertIn('#Oracle', e._build_footer_tags({}, selected))
        self.assertIn('#SWIFT', e._build_footer_tags({}, selected))
        for alias in ('바이빗', '바이비트', 'Bybit'):
            body, _ = e._inject_inline_tags('프랭클린템플턴이 ' + alias + '과 토큰화 펀드를 제공함', story(FRANKLIN))
            self.assertIn('#프랭클린템플턴 이', body)
            self.assertIn('#바이비트 과', body)

    def test_generic_words_are_not_company_tags(self):
        for title, summary in (('A price oracle delivers swift updates in the city', '오라클이 데이터를 제공함'),
                               ('Taylor Swift releases a song', '스위프트가 신곡을 공개함')):
            body, selected = e._inject_inline_tags(summary, story(title))
            self.assertNotIn('#Oracle', e._build_footer_tags({}, selected))
            self.assertNotIn('#SWIFT', e._build_footer_tags({}, selected))
            self.assertNotIn('#Citigroup', e._build_footer_tags({}, selected))

    def test_advertisements_still_fail(self):
        self.assertFalse(e.matches_keywords(story(FRANKLIN, article_text='Sponsored content. Claim referral rewards.'), [], [], []))

if __name__ == '__main__':
    unittest.main()
