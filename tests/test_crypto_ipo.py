from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch

import doorinews_editor as e
from news_quality import CRYPTO_IPO_ENABLED_AT, crypto_ipo_scope_reason, crypto_ipo_intake_reason

TITLE = '블록체인닷컴, 연내 美 증시 상장 추진…최대 5억달러 조달 목표'

def story(title=TITLE, **kw):
    return {'title': title, 'pub': datetime.now(timezone.utc).isoformat(), **kw}

class CryptoIpoTests(unittest.TestCase):
    def test_concrete_corporate_ipo_steps_enter_review(self):
        for title in (TITLE, 'Blockchain.com eyes $500M IPO as crypto capital markets thaw: Report',
                      'Kraken files confidential IPO application',
                      '가상자산 수탁사, 기업공개 신청서 제출',
                      'Crypto exchange files for initial public offering',
                      'Gemini postpones IPO', '빗고, 기업공개 철회 발표'):
            with self.subTest(title=title):
                self.assertTrue(crypto_ipo_scope_reason(story(title)))
                self.assertTrue(e.matches_keywords(story(title), [], [], []))

    def test_prices_token_listings_rumors_and_unrelated_ipos_stay_out(self):
        for title in ('블록체인닷컴 주가 상승 전망', 'Blockchain.com IPO stock price target raised',
                      'Kraken IPO rumors fuel speculation', '크라켄 상장설 확산',
                      'Coinbase adds RIN/USDT trading', 'RIN 코인 신규 상장',
                      '일반 제조업체, 증시 상장 추진', 'A retailer files for an IPO'):
            with self.subTest(title=title):
                self.assertFalse(e.matches_keywords(story(title), [], [], []))

    def test_background_competitor_prices_do_not_block_ipo_report(self):
        item = story(article_text='블룸버그는 기업공개 추진을 보도했다. 조건은 변경될 수 있다. '
                     '대변인은 논평을 거부했다. 제미니 주가는 상장 이후 80% 하락했다.')
        self.assertFalse(e._is_hard_blocked(item)[0])
        self.assertTrue(e.matches_keywords(item, [], [], []))

    def test_title_price_card_and_advertisements_still_block(self):
        for item in (story('Blockchain.com shares surged after IPO plans'),
                     story(article_text='Sponsored content. Sign up with a referral code.')):
            self.assertTrue(e._is_hard_blocked(item)[0])

    def test_old_missing_and_invalid_dates_do_not_release_backlog(self):
        for value in ('', 'invalid', '2026-09-29T15:00:00',
                      CRYPTO_IPO_ENABLED_AT.isoformat(),
                      (CRYPTO_IPO_ENABLED_AT-timedelta(days=1)).isoformat()):
            item=story(pub=value)
            self.assertTrue(crypto_ipo_intake_reason(item))
            self.assertFalse(e.matches_keywords(item, [], [], []))

    def test_manual_ipo_and_removed_circle_urls_remain_blocked(self):
        for url in ('https://www.bloomingbit.io/feed/news/121184/?utm_source=rss',
                    'https://news.bitcoin.com/stablecoins/un-circle-foundation-partner-to-speed-aid-via-stablecoins/'):
            with patch.object(e, '_call_openai') as ai:
                self.assertEqual(e.build_message(story(url=url)), '')
                ai.assert_not_called()

    def test_company_name_tag_keeps_particle_separate(self):
        body, selected=e._inject_inline_tags('블록체인닷컴이 미국 증시 상장을 추진한다고 보도됨',story())
        self.assertIn('#블록체인닷컴 이',body)
        self.assertIn('#BlockchainCom',e._build_footer_tags({},selected))

    def test_false_completion_fails_source_review(self):
        checks=dict.fromkeys(('faithful','conditions_preserved','allowed_category','new_substantive_fact','source_sufficient','understandable'),True)
        checks['conditions_preserved']=False
        with patch.object(e,'_RUNTIME',{}),patch.object(e,'_call_openai',side_effect=[
            '블록체인닷컴이 미국 상장을 완료하고 5억달러를 조달했다고 발표함',
            json.dumps({'publish':False,'reason':'보도된 목표를 공식 완료로 왜곡','checks':checks})]):
            self.assertEqual(e.build_message(story(article_text='블룸버그는 상장 추진과 조달 목표를 보도했다. 회사는 논평을 거부했다.')),'')

if __name__=='__main__':
    unittest.main()
