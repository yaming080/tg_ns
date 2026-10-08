"""User-reported missing stories, Korean names, and bounded repair across cron runs."""
from datetime import datetime, timezone, timedelta
import json
import unittest
from unittest.mock import patch
import doorinews_editor as e
import news_quality as q
import news_review_cache as c

TITLES = (
    '이억원 "디지털자산 입법 속도"…취약층 지원·부채 관리 병행',
    'CFTC 위원장 "가상자산에도 기존 파생상품 증거금 기준 적용"',
    '미국 하원 금융위원장 "SEC·CFTC 가상자산 규제만으로 부족…클래리티법 처리 기대"',
    'French Hill says agency crypto rules cannot replace CLARITY Act',
    'Wells Fargo talks with Kraken parent about crypto trading',
    'Samsung Wallet to introduce USDC transfers across 82 million US Galaxy devices',
    '토스, 광주은행과 스테이블코인 QR결제 기술검증 완료',
)


def story(title=TITLES[4], **values):
    return dict(title=title, pub=max(datetime.now(timezone.utc), q.FEEDBACK_SCOPE_ENABLED_AT + timedelta(minutes=1)).isoformat(),
                url='https://example.com/new', **values)


def verdict(**changes):
    checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                           'new_substantive_fact', 'source_sufficient', 'understandable'), True)
    checks.update(changes)
    return json.dumps(dict(publish=all(checks.values()), reason='대상과 미정 조건을 보존해야 함', checks=checks))


class LunaFeedbackTests(unittest.TestCase):
    def test_future_equivalent_stories_reach_review(self):
        for title in TITLES:
            with self.subTest(title=title):
                self.assertTrue(q.channel_scope_reason(story(title)))
                self.assertEqual(e._is_hard_blocked(story(title)), (False, ''))
                self.assertTrue(e.matches_keywords(story(title), [], [], []))

    def test_price_rumor_general_support_and_noncrypto_stay_excluded(self):
        for title in (
            'Wells Fargo talks about mortgage trading',
            'Wells Fargo crypto trading rumor could send BTC price higher',
            'Samsung forecasts $80 billion profit as AI demand surges',
            '토스, 광주은행과 일반 QR결제 마케팅 행사 개최',
            'Analyst urges Congress to pass the CLARITY Act',
            'French Hill predicts Bitcoin price target $200000',
            'RIN/USDC now supports settlement',
        ):
            with self.subTest(title=title):
                self.assertTrue(e._is_hard_blocked(story(title))[0])

    def test_expanded_scope_does_not_release_old_queue(self):
        for title in TITLES:
            old = story(title)
            old['pub'] = (q.FEEDBACK_SCOPE_ENABLED_AT - timedelta(seconds=1)).isoformat()
            self.assertIn('범위 확대 전', e._is_hard_blocked(old)[1])
            old['pub'] = ''
            self.assertTrue(e._is_hard_blocked(old)[0])

    def test_teammate_posts_remain_blocked_before_ai(self):
        urls = ['https://bloomingbit.io/feed/news/' + n for n in ('121817','121797','121790','121830')]
        urls += ['https://crypto.news/' + slug for slug in (
            'wells-fargo-talks-with-kraken-parent-about-crypto-trading/',
            'hashkey-bitgo-add-eth-and-sol-staking-for-institutions/',
            'samsung-wallet-to-introduce-usdc-transfers-across-82-million-us-galaxy-devices/')]
        with patch.object(e, '_call_openai') as api:
            for url in urls:
                s = story(); s['url'] = url + '?utm_source=rss'
                self.assertEqual(e.build_message(s), '')
            api.assert_not_called()

    def test_korean_project_names_preserve_versions_tickers_and_numbers(self):
        raw = ('Oneiro가 Revolution Network의 V2를 공개했으며 REVO 배분량은 2억5000만개로 '
               '유지하고 공개 테스트넷은 준비 단계라고 설명함')
        clean = e._clean_summary(raw)
        tagged, selected = e._inject_inline_tags(clean, story(raw))
        self.assertIn('#오네이로 가', tagged)
        self.assertIn('#레볼루션네트워크 의 V2', tagged)
        self.assertIn('REVO 배분량은 2억5000만개', tagged)
        self.assertIn('준비 단계', tagged)
        self.assertNotIn('Oneiro', tagged)
        self.assertNotIn('Revolution Network', tagged)
        footer = e._build_footer_tags(story(raw), selected)
        self.assertIn('#Oneiro', footer)
        self.assertIn('#RevolutionNetwork', footer)
        self.assertEqual(footer[-6:], list(e.FIXED_FOOTER_TAGS))

    def test_polygon_and_ripple_names_are_tagged_as_complete_names(self):
        raw = 'Polygon이 Open Money Stack에 TRON 기반 USDT와 TRC-20 결제를 추가했다고 밝힘'
        tagged, _ = e._inject_inline_tags(e._clean_summary(raw), story(raw))
        for term in ('#폴리곤 이', '#오픈머니스택 에', '#트론', 'USDT', 'TRC-20'):
            self.assertIn(term, tagged)
        raw = 'Ripple Prime이 Brevan Howard 펀드에 서비스를 제공하고 메리츠증권과 협력했다고 밝힘'
        tagged, _ = e._inject_inline_tags(e._clean_summary(raw), story(raw))
        for term in ('#리플프라임 이', '#브레반하워드', '#펀드', '#메리츠증권'):
            self.assertIn(term, tagged)
        self.assertNotIn('#리플 Prime', tagged)

    def test_fixed_bitcoin_tags_only_in_footer(self):
        tagged, selected = e._inject_inline_tags('폴리곤이 비트코인과 BTC 결제를 지원함', story())
        self.assertNotIn('#BTC', tagged); self.assertNotIn('#비트코인', tagged)
        footer = e._build_footer_tags(story(), selected)
        self.assertEqual(footer.count('#BTC'), 1); self.assertEqual(footer.count('#비트코인'), 1)

    def test_repair_reused_after_serialized_state_and_source_change_rechecks(self):
        s = story('HashKey, BitGo add ETH and SOL staking for institutions',
                  article_text='HashKey Capital and its funds are the custody customers. Staking access timing is unspecified.')
        bad = '해시키와 비트고가 모든 기관 고객에게 스테이킹을 출시했다고 밝힘'
        good = '해시키 캐피털과 관련 펀드를 수탁 대상으로 협력하며 스테이킹 접근 시점은 미정이라고 밝힘'
        state = {}
        with patch.object(e, '_RUNTIME', {'OPENAI_MODEL': 'gpt-6-luna'}), patch.object(
                e, '_call_openai', side_effect=[bad, verdict(faithful=False), good, verdict()]) as ai:
            with c.review_session(state, lambda: None, logger=lambda *_: None):
                self.assertEqual(e._rewrite_summary(s), good)
            self.assertEqual(ai.call_count, 4)
            state = json.loads(json.dumps(state))
            with c.review_session(state, lambda: None, logger=lambda *_: None):
                self.assertEqual(e._rewrite_summary(s), good)
            self.assertEqual(ai.call_count, 4)
        changed = dict(s, article_text=s['article_text'] + ' New launch details.')
        with patch.object(e, '_RUNTIME', {'OPENAI_MODEL': 'gpt-6-luna'}), patch.object(
                e, '_call_openai', side_effect=[good, verdict()]) as ai:
            with c.review_session(state, lambda: None, logger=lambda *_: None):
                self.assertEqual(e._rewrite_summary(changed), good)
            self.assertEqual(ai.call_count, 2)

    def test_failed_repair_is_not_paid_again_or_published(self):
        state = {}; s = story(article_text='A bank is discussing a specific crypto trading agreement.')
        with patch.object(e, '_RUNTIME', {'OPENAI_MODEL': 'gpt-6-luna'}), patch.object(
                e, '_call_openai', side_effect=['웰스파고가 거래를 시작함', verdict(conditions_preserved=False),
                                              '웰스파고가 거래를 시작함', verdict(conditions_preserved=False)]) as ai:
            for _ in range(3):
                with c.review_session(state, lambda: None, logger=lambda *_: None):
                    self.assertEqual(e.build_message(s), '')
            self.assertEqual(ai.call_count, 4)

    def test_unpublishable_or_invalid_decision_does_not_trigger_repair(self):
        for decision in (verdict(allowed_category=False), verdict(new_substantive_fact=False),
                         verdict(source_sufficient=False), 'broken JSON'):
            with self.subTest(decision=decision), patch.object(e, '_RUNTIME', {'OPENAI_MODEL': 'gpt-6-luna'}), patch.object(
                    e, '_call_openai', side_effect=['웰스파고가 거래를 협의한다고 밝힘', decision]) as ai:
                with c.review_session({}, lambda: None, logger=lambda *_: None):
                    self.assertEqual(e._rewrite_summary(story(article_text='Bank discusses crypto trading.')), '')
                self.assertEqual(ai.call_count, 2)

    def test_reserved_repair_survives_crash_without_retry(self):
        state = {}; s = story(article_text='Bank discusses crypto trading.')
        with patch.object(e, '_RUNTIME', {'OPENAI_MODEL': 'gpt-6-luna'}), patch.object(
                e, '_call_openai', side_effect=['웰스파고가 거래를 시작함', verdict(faithful=False), RuntimeError('offline failure')]):
            with self.assertRaises(RuntimeError), c.review_session(state, lambda: None, logger=lambda *_: None):
                e._rewrite_summary(s)
        with patch.object(e, '_RUNTIME', {'OPENAI_MODEL': 'gpt-6-luna'}), patch.object(e, '_call_openai') as ai:
            with c.review_session(state, lambda: None, logger=lambda *_: None):
                self.assertEqual(e._rewrite_summary(s), '')
            ai.assert_not_called()

    def test_policy_statement_stays_attributed_in_prompt(self):
        prompt = e._summary_prompt(TITLES[2], '새 발언 원문')
        self.assertIn('해당 인물의 발언으로 귀속', prompt)
        self.assertIn('법안 통과로 바꾸지 말라', prompt)
        summary = '프렌치 힐이 규제만으로 입법을 대체할 수 없다며 새 의회 출범 전 클래리티법 통과를 기대한다고 밝힘'
        with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[summary, verdict()]):
            caption = e.build_message(story(TITLES[2], article_text='French Hill says rules cannot replace legislation and hopes for passage before the new Congress.'))
        self.assertIn('기대한다고 밝힘', caption)
        self.assertIn('#프렌치힐', caption)


if __name__ == '__main__':
    unittest.main()
