"""User examples from shared conversations; no live calls or Telegram sends."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import doorinews_editor as e
from news_quality import quantity_followup_reason


class ChannelPreferences(unittest.TestCase):
    def test_policy_and_services_without_portfolio_ticker(self):
        titles = [
            'Australia passes crypto licensing bill',
            'eToro wins New York BitLicense, expands crypto access to 48 states',
            'Bitget launches crypto payment card across APAC',
            'Fed proposes GENIUS Act rules for stablecoin issuers and banks',
            'Japan launches EJPY stablecoin payments pilot with Toshiba',
            "스테이블코인 속도내는 일본 - 도시바 등 26곳, 'EJPY' 실증 참여.",
            'Taiwan government considers Bitcoin reserve proposal',
            '케이뱅크, 업비트 연계 은행 계좌 서비스 출시',
            'Jack Dorsey says AI should replace corporate hierarchy at Block',
            'What does Australia crypto licensing bill approval mean?',
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(e.matches_keywords({'title':title}, [], [], []))

    def test_unrelated_ads_prices_and_failed_license_rehash_stay_excluded(self):
        titles = [
            'Mercado Libre shuts down Mercado Coin loyalty rewards',
            'Bitget partners with Mulerun to launch AI trading assistant',
            'Bitcoin price forecast: rally could reach $100000',
            'Bitcoin records a green monthly candle',
            'XRP wallet holdings rise to 5 billion tokens',
            'Sponsored content: Bitget launches crypto payment card',
            'Hong Kong has not issued a single stablecoin license',
            'Airline wins travel license',
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertFalse(e.matches_keywords({'title':title}, [], [], []))

    def test_exact_dcent_preview_is_now_blocked_before_ai(self):
        story = {'title':"XRPL 분석 플랫폼 xrpl.to가 D'CENT 앱 월렛 유출이 계속돼 9월 21일 이후 64만370 XRP 가 추가 탈취됐다고 공개함"}
        with patch.object(e, '_call_openai') as ai:
            self.assertEqual(e.build_message(story), '')
            ai.assert_not_called()
        self.assertTrue(quantity_followup_reason({'title':'Never send XRP to old app wallet: wallet drain continues'}))

    def test_recovery_arrest_and_patch_are_not_quantity_only(self):
        for title in ('Police arrest XRP wallet hackers after continuing theft',
                      'Exchange recovers additional Bitcoin stolen in hack',
                      'Dcent patches vulnerability behind ongoing XRP theft'):
            self.assertFalse(quantity_followup_reason({'title':title}))

    def test_fixed_tags_survive_inline_overlap_and_budget(self):
        selected = [e.EntitySpec('asset','비트코인',('Bitcoin',),'#BTC')]
        selected += [e.EntitySpec('person',f'사람{i}',(f'Person{i}',),f'#Person{i}') for i in range(20)]
        footer = e._build_footer_tags({}, selected)
        self.assertEqual(footer[-6:], list(e.FIXED_FOOTER_TAGS))
        self.assertEqual(len(footer), len(set(footer)))

    def test_person_law_and_country_bilingual_tags(self):
        story = {'title':'Michael Barr announces GENIUS Act stablecoin regulation in United States'}
        body, selected = e._inject_inline_tags('마이클 바가 미국 스테이블코인 지니어스법 규제를 공개함',story)
        for tag in ('#마이클바', '#미국', '#스테이블코인', '#지니어스법', '#규제'):
            self.assertIn(tag,body)
        footer = e._build_footer_tags(story,selected)
        for tag in ('#MichaelBarr','#UnitedStates','#GENIUS','#Stablecoin'):
            self.assertIn(tag,footer)

    def test_identical_inline_tags_not_repeated_but_korean_gets_english(self):
        story = {'title':'Jack Dorsey of Block announces AI organization change; XRP Ledger mentioned only in background'}
        body, selected = e._inject_inline_tags('잭 도시가 AI 조직 개편을 발표함',story)
        footer = e._build_footer_tags(story,selected)
        self.assertIn('#잭도시',body)
        self.assertIn('#JackDorsey',footer)
        for tag in ('#AI','#XRP','#XRPL'):
            self.assertNotIn(tag,footer)

    def test_empty_body_stays_unsent(self):
        with patch.object(e,'_rewrite_summary',return_value=''):
            self.assertEqual(e.build_message({'title':'Australia passes crypto licensing bill'}),'')


if __name__ == '__main__':
    unittest.main()
