"""Actual missed headlines and sponsorship/word-boundary regressions."""
from datetime import datetime, timedelta, timezone
import json
import re
import unittest
from unittest.mock import patch
import doorinews_editor as e
from news_quality import source_promotion_reason, REGULATORY_PAYMENT_ENABLED_AT

TETHER = 'Tether faces Senate scrutiny over Iran-linked USDT'
COINBASE = 'Coinbase can now settle derivatives 24/7 with USDC'
CARDANO = 'Cardano Foundation, UCLA partner on blockchain education'

def story(title, **kw):
    return {'title':title,'pub':datetime.now(timezone.utc).isoformat(),**kw}

class OversightSettlementEducationTests(unittest.TestCase):
    def test_real_and_equivalent_headlines_enter_review(self):
        for title in (TETHER, COINBASE,
                      'US senator urges Treasury and DOJ to investigate Tether over Iran-linked USDT',
                      'Coinbase gets CFTC approval for US derivatives clearinghouse',
                      '테더 USDT 관련 상원 조사 요청',
                      'Exchange enables USDC settlement for derivatives'):
            with self.subTest(title=title):
                self.assertTrue(e.matches_keywords(story(title),[],[],[]))

    def test_actual_education_source_passes_without_disabling_ad_review(self):
        text=('The Cardano Foundation has announced a multi-year partnership with UCLA. '
              'Five companies will receive Cardano-sponsored fellowships. '
              'The interactive session will cover enterprise Web3 applications. '
              'Students will receive a certification sponsored by the Cardano Foundation.')
        self.assertFalse(e._is_hard_blocked(story(CARDANO,article_text=text))[0])

    def test_sponsored_education_at_start_is_not_an_ad_label(self):
        for text in ('Sponsored fellowships will fund five founders.',
                     'Scholarships sponsored by the foundation support students.',
                     'Research grants are sponsored by the foundation.'):
            self.assertFalse(source_promotion_reason({'article_text':text}))

    def test_paid_labels_and_referrals_stay_blocked_alongside_education(self):
        for text in ('Sponsored', 'Sponsored by Example.', 'Sponsored content: education news.',
                     'Paid advertisement. A foundation sponsors scholarships.',
                     'Cardano-sponsored fellowships. This is sponsored content.',
                     'Certification sponsored by Cardano. Sign up with referral code ABC.'):
            with self.subTest(text=text):
                self.assertTrue(e._is_hard_blocked(story(CARDANO,article_text=text))[0])

    def test_price_forecasts_still_match_whole_words(self):
        pattern=next(p for p in e.HARD_BLOCK_PATTERNS if 'break\\s+out' in p)
        self.assertIsNone(re.search(pattern,'The session will cover enterprise applications',re.I))
        for text in ('Bitcoin will rise tomorrow', 'ETH will recover next month', 'XRP will rally soon'):
            self.assertIsNotNone(re.search(pattern,text,re.I))
            self.assertTrue(e._is_hard_blocked(story(text))[0])

    def test_unrelated_tokens_metrics_and_rumors_remain_excluded(self):
        for title in ('RIN/USDT trading launches on XT', 'RIN/USDC now supports settlement',
                      'Tether USDT market cap reaches record', 'USDC derivatives trading volume rises',
                      'Rumors suggest Senate could investigate Tether',
                      'Senate investigates a retail company',
                      'A senator predicts Bitcoin price target of $200000'):
            with self.subTest(title=title):
                self.assertFalse(e.matches_keywords(story(title),[],[],[]))

    def test_new_scope_keeps_old_queue_silent(self):
        for title in (TETHER, COINBASE):
            for pub in ('', 'invalid', REGULATORY_PAYMENT_ENABLED_AT.isoformat(),
                        (REGULATORY_PAYMENT_ENABLED_AT-timedelta(hours=1)).isoformat()):
                self.assertFalse(e.matches_keywords(story(title,pub=pub),[],[],[]))

    def test_three_manual_urls_cannot_call_summary_or_post(self):
        for slug,title in (('tether-faces-senate-scrutiny-over-iran-linked-usdt',TETHER),
                           ('cardano-foundation-ucla-partner-blockchain-education',CARDANO),
                           ('coinbase-can-now-settle-derivatives-24-7-with-usdc',COINBASE)):
            with patch.object(e,'_call_openai') as ai:
                self.assertEqual(e.build_message(story(title,url=f'https://www.crypto.news/{slug}/?utm_source=rss')),'')
                ai.assert_not_called()

    def test_request_for_investigation_cannot_become_conviction(self):
        checks=dict.fromkeys(('faithful','conditions_preserved','allowed_category','new_substantive_fact','source_sufficient','understandable'),True)
        checks['conditions_preserved']=False
        with patch.object(e,'_RUNTIME',{}),patch.object(e,'_call_openai',side_effect=[
            '테더가 이란 관련 자금 세탁 혐의로 유죄 판결을 받았다고 밝힘',
            json.dumps({'publish':False,'reason':'의원의 조사 요청을 유죄 확정으로 왜곡','checks':checks})]):
            self.assertEqual(e.build_message(story(TETHER,article_text='A senator asked Treasury and DOJ to investigate Tether. No conviction was announced.')),'')

    def test_ucla_tag_and_educational_sponsorship_survive_formatting(self):
        body,_=e._inject_inline_tags('카르다노 재단과 UCLA가 교육 협약을 체결함',story(CARDANO))
        self.assertIn('#UCLA 가',body)
        self.assertIn('sponsored by',e._clean_summary('A certification sponsored by Cardano supports education'))

    def test_official_report_wallet_claims_enter_attribution_review(self):
        source=('The Senate subcommittee staff released a preliminary report. '
                'Wallets associated by investigators with an exchange received funds. '
                'Tether disputed the portrayal. These are minority staff findings.')
        self.assertFalse(e._is_hard_blocked(story(TETHER,article_text=source))[0])
        rumor=story('Tether wallet linked to Iran received funds',article_text=source)
        self.assertTrue(e._is_hard_blocked(rumor)[0])
        unsupported=story(TETHER,article_text='Wallets associated with Iran received funds, according to an anonymous post.')
        self.assertTrue(e._is_hard_blocked(unsupported)[0])

if __name__=='__main__': unittest.main()
