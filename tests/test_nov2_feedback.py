import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, Mock

import doorinews_editor as e
import news_nov2_scope as scope
import news_manual_nov2 as manual
import news_event_review as events
import news_review_cache as cache
from news_publication import prepare_publication


def story(title, **kw):
    return dict(title=title, url='https://example.com/future-story',
                pub=max(datetime.now(timezone.utc), scope.ENABLED_AT + timedelta(seconds=1)).isoformat(), **kw)


class Nov2FeedbackTests(unittest.TestCase):
    def test_future_equivalents_reach_review(self):
        for _, title, _ in manual.EVENTS:
            with self.subTest(title=title):
                s = story(title)
                self.assertTrue(scope.scope(s))
                self.assertFalse(e._is_hard_blocked(s)[0], e._is_hard_blocked(s)[1])
                self.assertTrue(e.matches_keywords(s, [], [], []))

    def test_actual_titles_and_bilingual_variants(self):
        for title in (
            '사전투표 마친 머스크 “민주당 이기면 영원한 일당독재 국가 들어서”',
            'China’s Communist Party Vows Crackdown on Corruption via Crypto and Blockchain',
            'BTCPay Server issues emergency shutdown warning amid hot wallet attacks',
            'AWS unveils cloud architecture for crypto exchange custody',
            'South Korean lawmaker introduces crypto tax deferral bill',
            '인도, 비자·마스터카드·리닷페이 연계 역외 암호화폐 카드 조사',
            'CZ, 바이낸스 사용자 98%가 머물기 선택했다고 밝힘',
        ):
            self.assertTrue(scope.scope(story(title)), title)
            self.assertTrue(e.matches_keywords(story(title), [], [], []), title)

    def test_background_metrics_do_not_block_emergency_notice(self):
        s = story('BTCPay Server urges server shutdowns amid wallet attacks',
                  article_text='BTCPay warns operators to shut down affected servers during investigation. '
                               'Exchange outflows and trading volume are discussed in background.')
        self.assertFalse(e._is_hard_blocked(s)[0])
        for title in ('BTCPay annual losses report', 'BTCPay wallet losses rise to $50m',
                      'Binance withdrawal volume hits record high',
                      'Trump election price prediction for Bitcoin', 'AWS sponsored crypto exchange blueprint',
                      'How to use BTCPay wallet', 'XRP technical analysis by SWIFT expert'):
            self.assertFalse(scope.scope(story(title)), title)

    def test_portfolio_and_outside_project_exclusions_still_win(self):
        for title in ('XRP Ledger critical vulnerability patched',
                      'BNB network outage as CZ says Binance users remain',
                      'Sui launches crypto exchange platform using AWS blueprint',
                      'Ethereum security flaw discussed by former SWIFT expert in interview'):
            self.assertTrue(e._is_hard_blocked(story(title))[0], title)

    def test_no_old_queue_release(self):
        from news_coverage import coverage_scope
        from news_industry_intake import industry_intake_scope
        for _, title, _ in manual.EVENTS:
            if coverage_scope({'title': title}, team_feedback=False) or industry_intake_scope({'title': title}):
                continue  # Already-eligible categories retain their earlier cutoff.
            for pub in ('', 'invalid', scope.ENABLED_AT.isoformat()):
                s = story(title); s['pub'] = pub
                self.assertTrue(e._is_hard_blocked(s)[0], (title, pub))

    def test_manual_posts_block_before_paid_review_and_enter_history(self):
        with patch.object(e, '_call_openai') as api:
            for url, title, _ in manual.EVENTS:
                for variant in (url, url.split('?')[0] + '?utm_source=rss'):
                    s = story(title); s['url'] = variant
                    self.assertIn('게시', e._is_hard_blocked(s)[1])
                    self.assertEqual(e.build_message(s), '')
        api.assert_not_called()
        history = events.history_records({})
        for url, _, _ in manual.EVENTS:
            self.assertTrue(any(events.url_key(r['url']) == events.url_key(url) for r in history))
        self.assertEqual(len(manual.EVENTS), 10)

    def test_scope_does_not_approve_source_or_publish(self):
        title = manual.EVENTS[3][1]
        selector = Mock()
        result = prepare_publication(story(title), lambda _: '', None, 'unused', selector=selector)
        self.assertEqual(result['status'], 'held')
        selector.assert_not_called()
        required = ('faithful', 'conditions_preserved', 'allowed_category',
                    'new_substantive_fact', 'source_sufficient', 'understandable')
        for failed in required:
            checks = dict.fromkeys(required, True); checks[failed] = False
            with patch.object(e, '_call_openai', return_value=json.dumps({
                    'publish': False, 'reason': '미확인 조건', 'checks': checks})):
                self.assertFalse(e._validate_summary_against_source(title, 'source', 'summary'))

    def test_selective_guidance_and_entity_tags(self):
        unrelated = 'XRP institutional payment service launch'
        self.assertEqual(e._scope_guidance(unrelated), e._scope_guidance())
        for _, title, _ in manual.EVENTS:
            self.assertIn(scope.GUIDANCE, e._summary_prompt(title, 'article source'))
        s = story('AWS와 톰 알라에르츠 및 최은석')
        tagged, _ = e._inject_inline_tags('AWS가 설계안을 공개함\n\n톰 알라에르츠와 최은석이 설명함', s)
        for tag in ('#AWS', '#톰알라에르츠', '#최은석'):
            self.assertIn(tag, tagged)
        tagged, _ = e._inject_inline_tags('톰 알라에르츠가 ISO 20022와 은행 통합에 관해 설명함', story(manual.EVENTS[3][1]))
        self.assertNotIn('#XRP', tagged)

    def test_cache_reuse_preserves_unaffected_rejections_and_ttl(self):
        manifest = json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text('utf8'))
        # This fixture predates Nov 2 intake, independent of manifest order.
        old = 'd871bb990fee31a713a3a472bec514c1ccb0797f47262f317b40f167d00d1974'
        self.assertIn(old, manifest['previous_identities'])
        with cache.review_session({}, lambda: None, logger=lambda _: None) as store:
            expiry = store.clock() + 1000
            scopes = [{'title': manual.EVENTS[9][1]}, {'title': 'Unchanged excluded article'}]
            for s in scopes:
                key = cache.fingerprint([cache.VERSION, old, 'source_summary', s])
                store.data.setdefault('content_results_v1', {})[key] = {
                    'result': {'summary': '', 'reason': 'excluded'}, 'expires': expiry}
            self.assertIsNone(cache.content_result('source_summary', scopes[0]))
            self.assertEqual(cache.content_result('source_summary', scopes[1])['reason'], 'excluded')
            self.assertTrue(all(r['expires'] == expiry for r in store.data['content_results_v1'].values()))
            self.assertEqual(store.calls, 0)
