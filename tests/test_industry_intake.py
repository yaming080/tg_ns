import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from pathlib import Path

import doorinews_editor as editor
import news_review_cache as cache
from news_industry_intake import industry_intake_scope, ENABLED_AT
from news_publication import prepare_publication


def story(title, **extra):
    return dict(title=title, url='https://example.com/new-industry-event',
                pub=datetime.now(timezone.utc).isoformat(), **extra)


MISSED = (
    'China calls for tougher crackdown on crypto bribes, corruption',
    '가상자산 이용 부패행위 단속 명시한 중국공산당 결정문 공개',
    'HTX Exits the UK After FCA Settlement Over Crypto Promotions',
    'Binance Withdrawals Reopened as Exchange Begins Recovery After $6.3B Hack',
    '바이낸스, 출금 서비스 재개 발표',
)


class IndustryIntakeTests(unittest.TestCase):
    def test_missed_headlines_reach_review_without_portfolio_ticker(self):
        for title in MISSED:
            with self.subTest(title=title):
                s = story(title)
                self.assertTrue(industry_intake_scope(s))
                self.assertFalse(editor._is_hard_blocked(s)[0])
                self.assertTrue(editor.matches_keywords(s, [], [], []))

    def test_prechange_rejections_do_not_reenter_queue(self):
        for title in MISSED:
            for stamp in ('', 'invalid', ENABLED_AT.isoformat(),
                          (ENABLED_AT-timedelta(seconds=1)).isoformat()):
                s = story(title); s['pub'] = stamp
                self.assertTrue(editor._is_hard_blocked(s)[0], (title, stamp))

    def test_no_blanket_exchange_or_policy_admission(self):
        for title in (
            'Binance withdrawal volume hits record high',
            'Binance could resume withdrawals next week',
            'How to withdraw crypto from Binance',
            'China crypto corruption annual losses report',
            'China crypto crackdown price prediction',
            'HTX sponsored giveaway after FCA settlement',
            'Binance hack losses rise to $7 billion',
            'Bank launches new mortgage service',
            'China announces road traffic crackdown',
        ):
            self.assertFalse(industry_intake_scope(story(title)), title)

    def test_existing_adverse_and_outside_project_blocks_win(self):
        for title in (
            'BNB network outage as Binance resumes withdrawals',
            'Sui launches crypto custody platform with New Harbor Bank',
            'XRP Ledger critical vulnerability patched',
        ):
            self.assertTrue(editor._is_hard_blocked(story(title))[0], title)

    def test_successful_donation_and_financial_service_examples_stay_eligible(self):
        for title in (
            '리플랩스와 크리스 라센, 캘리포니아 자산세 반대 위원회에 각각 500만달러 기부',
            'New Harbor Bank launches digital asset custody service',
        ):
            self.assertTrue(editor.matches_keywords(story(title), [], [], []), title)

    def test_new_intake_is_not_publication_approval(self):
        selector = Mock()
        result = prepare_publication(story(MISSED[0]), lambda _: '', None, 'unused', selector=selector)
        self.assertEqual(result['status'], 'held')
        selector.assert_not_called()
        required = ('faithful', 'conditions_preserved', 'allowed_category',
                    'new_substantive_fact', 'source_sufficient', 'understandable')
        for failed in required:
            checks = dict.fromkeys(required, True); checks[failed] = False
            answer = json.dumps({'publish': False, 'reason': '원문 검증 불충분', 'checks': checks})
            with patch.object(editor, '_call_openai', return_value=answer):
                self.assertFalse(editor._validate_summary_against_source(MISSED[0], 'source', 'summary'))

    def test_affected_exclusion_is_not_migrated_but_unrelated_result_is(self):
        manifest = json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text(encoding='utf8'))
        old = manifest['previous_identities'][0]
        with cache.review_session({}, lambda: None, logger=lambda _: None) as store:
            expiry = store.clock()+1000
            store.data['content_results_v1'] = {}
            for title in (MISSED[0], 'Unchanged XRP approval'):
                scope = {'title': title, 'source': 'same'}
                key = cache.fingerprint([cache.VERSION, old, 'source_summary', scope])
                store.data['content_results_v1'][key] = {'result': {'summary': ''}, 'expires': expiry}
            self.assertIsNone(cache.content_result('source_summary', {'title': MISSED[0], 'source': 'same'}))
            self.assertEqual(cache.content_result('source_summary', {'title': 'Unchanged XRP approval', 'source': 'same'}), {'summary': ''})
            self.assertTrue(all(v['expires'] == expiry for v in store.data['content_results_v1'].values()))
            self.assertEqual(store.calls, 0)
