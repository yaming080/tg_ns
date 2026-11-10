import json
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import doorinews_editor as editor
import news_card_payment_scope as card
import news_review_cache as cache

TITLE = '신한카드 "스테이블코인 결제, 초기에는 기존 카드망 활용할 수도"'


def story(title=TITLE):
    return {'title': title, 'url': 'https://example.com/new-card-proposal',
            'pub': (card.ENABLED_AT + timedelta(minutes=1)).isoformat()}


class CardPaymentIntakeTests(unittest.TestCase):
    def test_concrete_named_issuer_proposal_reaches_review(self):
        for title in (TITLE, 'Shinhan Card says stablecoin payments could use existing card rails'):
            s = story(title)
            self.assertTrue(card.scope(s))
            self.assertFalse(editor._is_hard_blocked(s)[0], editor._is_hard_blocked(s))
            self.assertTrue(editor.matches_keywords(s, [], [], []))

    def test_old_or_unknown_date_does_not_replay(self):
        for pub in ('', 'bad', card.ENABLED_AT.isoformat(), '2026-11-10T08:21:00'):
            s = story(); s['pub'] = pub
            self.assertTrue(editor._is_hard_blocked(s)[0], pub)

    def test_generic_forecasts_and_ads_do_not_gain_new_scope(self):
        for title in ('스테이블코인 카드 결제 전망',
                      '신한카드 스테이블코인 결제 산업 전망',
                      TITLE + ' sponsored', TITLE + ' 목표가 분석',
                      '신한카드 기존 카드망 혜택 제안'):
            self.assertFalse(card.scope(story(title)), title)

    def test_nonportfolio_and_sponsored_source_still_blocked(self):
        s = story('Sui launches payment platform with ' + TITLE)
        self.assertTrue(editor._is_hard_blocked(s)[0])
        s = story(); s['article_text'] = 'This is sponsored content.'
        self.assertIn('협찬', editor._is_hard_blocked(s)[1])

    def test_proposal_is_not_launch_and_requires_source_checks(self):
        prompt = editor._summary_prompt(TITLE, 'source')
        self.assertIn('서비스 출시·실증 완료·현재 결제 지원·확정 계획으로 바꾸지 않는다', prompt)
        self.assertIn('이미 스테이블코인을 받는 가맹점 수가 아니며', prompt)
        required = ('faithful', 'conditions_preserved', 'allowed_category',
                    'new_substantive_fact', 'source_sufficient', 'understandable')
        for failed in required:
            checks = dict.fromkeys(required, True); checks[failed] = False
            with patch.object(editor, '_call_openai', return_value=json.dumps(
                    {'publish': False, 'reason': 'not verified', 'checks': checks})):
                self.assertFalse(editor._validate_summary_against_source(TITLE, 'source', 'summary'))

    def test_only_changed_type_invalidates_prior_semantic_cache(self):
        manifest = json.loads((Path(cache.__file__).parent / 'news_cache_compatibility.json').read_text('utf8'))
        old = '97d6474ca42d9a824a6709362a4735d36592fb70076b70346427b3dbd1e4db74'
        self.assertIn(old, manifest['previous_identities'])
        with cache.review_session({}, lambda: None, logger=lambda _: None) as store:
            expiry = store.clock() + 1000
            for title, changed in ((TITLE, True), ('Unchanged rejected article', False),
                                   ('Coinbase secures national trust bank charter from OCC', False)):
                s = {'title': title, 'source': 'unchanged'}
                key = cache.fingerprint([cache.VERSION, old, 'source_summary', s])
                store.data.setdefault('content_results_v1', {})[key] = {
                    'result': {'summary': '', 'reason': 'excluded'}, 'expires': expiry}
                result = cache.content_result('source_summary', s)
                if changed:
                    self.assertIsNone(result)
                else:
                    self.assertEqual(result['reason'], 'excluded')
            self.assertTrue(all(row['expires'] == expiry for row in store.data['content_results_v1'].values()))


if __name__ == '__main__':
    unittest.main()
