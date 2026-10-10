import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import doorinews_editor as e
import news_asset_scope as a
import news_review_cache as cache

def story(title, **extra):
    return dict(title=title,url='https://example.com/new-story',
                pub=datetime.now(timezone.utc).isoformat(),**extra)

class OutsideScopeTests(unittest.TestCase):
    def test_actual_post_title_rejected_before_model(self):
        s=story("Bitcoin treasury companies get two Anchorage routes into Sui's Hashi",
                desc='BTC collateral financing through Sui. Anchorage joins the mainnet.')
        with patch.object(e,'_call_openai') as api:
            self.assertFalse(e.matches_keywords(s,[],[],[]))
            self.assertEqual(e.build_message(s),'')
            self.assertIn('SUI',e._is_hard_blocked(s)[1])
            api.assert_not_called()

    def test_collateral_or_stablecoin_keyword_does_not_bypass(self):
        for title in ("Anchorage joins Sui’s Hashi Bitcoin collateral platform",
                      '앵커리지, 수이의 비트코인 금융망 해시 참여',
                      'Sui partners with bank for USDC treasury service',
                      'USDC launches on Sui network',
                      'Aptos launches USDT collateral platform'):
            with self.subTest(title=title):
                self.assertTrue(e._is_hard_blocked(story(title))[0])
                self.assertTrue(a.outside_project_reason(story(title)))

    def test_parallel_eth_sol_support_still_reviewed(self):
        s=story('HashKey, BitGo add ETH and SOL staking for institutions')
        self.assertFalse(a.outside_project_reason(s))
        self.assertTrue(e.matches_keywords(s,[],[],[]))

    def test_background_names_and_common_words_are_not_blacklist(self):
        for title in ('Bitcoin service launches near major bank',
                      'SEC custody rules cite Bitcoin and Sui as examples',
                      'XRP Ledger adds new features; Solana mentioned in comparison',
                      'Ethereum upgrades its settlement with Solana tools'):
            self.assertFalse(a.outside_project_reason(story(title)),title)

    def test_industry_news_without_coin_still_reviewed(self):
        s=story('프랑스, 스테이블코인 과세 추진…투자 손실은 10년 공제')
        self.assertTrue(e.matches_keywords(s,[],[],[]))

    def test_neutral_title_but_outside_project_body_uses_existing_review(self):
        s=story('Bitcoin treasury companies access new financing routes',
                article_text="Anchorage joined Sui's Hashi platform as an initial partner. BTC is the collateral.")
        response=json.dumps(dict(publish=False,reason='수이 플랫폼 채택이 핵심',checks={
            k:k!='allowed_category' for k in ('faithful','conditions_preserved','allowed_category',
                'new_substantive_fact','source_sufficient','understandable')}))
        prompts=[]
        results=iter(['앵커리지가 수이의 해시 BTC 담보 플랫폼에 참여했다고 밝힘',response])
        with patch.object(e,'_RUNTIME',{'OPENAI_MODEL':'gpt-6-luna'}),patch.object(e,'_call_openai',
                side_effect=lambda text:prompts.append(text) or next(results)) as api:
            with cache.review_session({},lambda:None,logger=lambda *_:None):
                self.assertEqual(e._rewrite_summary(s),'')
            self.assertEqual(api.call_count,2)
        for prompt in prompts:
            self.assertIn('수이 이름을 지우고',prompt)
            self.assertIn('allowed_category=false',prompt)

    def test_previous_repair_cache_cannot_bypass_new_policy(self):
        scopes=[]
        s=story('Bitcoin treasury companies access financing',article_text='New institutional service evidence.')
        with patch.object(e,'repair_memory',side_effect=lambda scope:scopes.append(scope) or {'summary':''}):
            self.assertEqual(e._rewrite_summary(s),'')
        self.assertIn(a.POLICY,scopes[0]['policy'])

    def test_third_pass_adverse_filter_remains_active(self):
        self.assertIn('포트폴리오 악재',e._is_hard_blocked(story('XRP Ledger critical vulnerability patched'))[1])

    def test_final_summary_cannot_hide_outside_platform_under_btc_title(self):
        s=story('Bitcoin treasury companies launch financing service')
        with patch.object(e,'_rewrite_summary',return_value='앵커리지가 수이의 비트코인 금융망 해시에 참여했다고 밝힘'):
            self.assertEqual(e.build_message(s),'')

if __name__=='__main__': unittest.main()
