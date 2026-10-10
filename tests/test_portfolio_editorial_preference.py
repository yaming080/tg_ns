import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import doorinews_editor as e
import news_portfolio_policy as p
import news_review_cache as cache


def story(title, **extra):
    return dict(title=title, url='https://example.com/new-portfolio-event',
                pub=datetime.now(timezone.utc).isoformat(), **extra)


class PortfolioPreferenceTests(unittest.TestCase):
    def test_screenshot_is_blocked_even_with_patch_and_no_exploitation(self):
        s=story('XRP Ledger critical vulnerability could create XRP beyond total supply',
                desc='RippleX rated the issue critical. xrpld 3.4.1 was deployed; no exploitation evidence.')
        with patch.object(e,'_call_openai') as api:
            self.assertFalse(e.matches_keywords(s,[],[],[]))
            self.assertEqual(e.build_message(s),'')
            api.assert_not_called()

    def test_korean_caption_as_title_also_blocked(self):
        s=story('XRP 레저에서 결제 계산 오류로 총공급량을 넘는 XRP가 생성될 수 있는 취약점 공개')
        self.assertIn('포트폴리오',e._is_hard_blocked(s)[1])

    def test_negative_all_portfolio_networks_not_just_xrp(self):
        for asset in ('Bitcoin','Ethereum','XRP Ledger','Stellar','Cardano','TRON',
                      'BNB','Bitcoin Cash','Shibarium','Ethereum Classic','Flare',
                      'Ethena','ATHENA','USDC','USDT'):
            with self.subTest(asset=asset):
                self.assertTrue(p.adverse_portfolio_reason(story(asset+' critical security flaw patched'),e.target_assets))
        for title in ('USDC depegs after reserve crisis','리플, 소송 패소','ETH network outage'):
            self.assertTrue(p.adverse_portfolio_reason(story(title),e.target_assets))

    def test_positive_adoption_and_normal_upgrade_not_blocked(self):
        for title in ('Ripple Custody completes Canton integration','XRP Ledger launches new payment tools',
                      'Cardano adds preventive security features','USDC expands bank payment access',
                      'XRP Ledger introduces vulnerability detection tools',
                      'Ripple debunks false security flaw claim'):
            with self.subTest(title=title):
                self.assertFalse(p.adverse_portfolio_reason(story(title),e.target_assets))

    def test_background_and_fixed_footer_do_not_define_subject(self):
        for title in ('France advances crypto tax bill','DOJ scrutinizes Binance settlement compliance',
                      'Coldcard 취약점으로 비트코인 지갑 탈취 위험',
                      'Ledger investigates CryptoBilis hardware wallet Bitcoin losses'):
            s=story(title,desc='Bitcoin is mentioned in background. #BTC #비트코인')
            self.assertFalse(p.adverse_portfolio_reason(s,e.target_assets))

    def test_source_policy_rejects_negative_article_not_just_negative_wording(self):
        captured=[]
        response=json.dumps(dict(publish=False,reason='포트폴리오 네트워크 악재 중심',checks={
            k:k!='allowed_category' for k in ('faithful','conditions_preserved','allowed_category',
                  'new_substantive_fact','source_sufficient','understandable')}))
        with patch.object(e,'_call_openai',side_effect=lambda prompt:captured.append(prompt) or response):
            self.assertFalse(e._validate_summary_against_source('XRPL announces update','Critical flaw patched','보안 업데이트 공개함'))
        self.assertIn('부정적인 내용을 삭제하여',captured[0])
        self.assertIn('allowed_category=false',captured[0])
        self.assertIn('고정 하단 BTC 태그',captured[0])

    def test_editorial_exclusion_does_not_trigger_paid_repair(self):
        s=story('XRP Ledger announces protocol update',article_text='Critical flaw reported; patch deployed.')
        response=json.dumps(dict(publish=False,reason='포트폴리오 악재 중심',checks={
            k:k!='allowed_category' for k in ('faithful','conditions_preserved','allowed_category',
                  'new_substantive_fact','source_sufficient','understandable')}))
        with patch.object(e,'_RUNTIME',{'OPENAI_MODEL':'gpt-6-luna'}), patch.object(e,'_call_openai',
                side_effect=['XRP레저가 새 버전을 공개했다고 밝힘',response]) as api:
            with cache.review_session({},lambda:None,logger=lambda *_:None):
                self.assertEqual(e._rewrite_summary(s),'')
            self.assertEqual(api.call_count,2)

    def test_policy_change_invalidates_old_repair_cache(self):
        captured=[]
        s=story('XRP Ledger announces protocol update',article_text='New release notes.')
        with patch.object(e,'repair_memory',side_effect=lambda scope:captured.append(scope) or {'summary':''}):
            self.assertEqual(e._rewrite_summary(s),'')
        self.assertIn(p.POLICY,captured[0]['policy'])


if __name__=='__main__':
    unittest.main()
