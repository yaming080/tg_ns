import contextlib
import importlib
import io
import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import doorinews_editor as e
import news_intake_audit as audit
import news_review_cache as cache
from news_quality import source_promotion_reason


def story(title, **kwargs):
    return dict(title=title, url='https://example.com/new', pub=max(
        datetime.now(timezone.utc), audit.ENABLED_AT+timedelta(seconds=1)).isoformat(), **kwargs)


class LiveIntakeAudit(unittest.TestCase):
    def test_hashed_request_cache_scopes_are_not_article_dicts(self):
        for value in ('request-hash', None, [], 5):
            self.assertEqual(audit.scope(value), '')

    def test_all_collectible_team_examples_reach_review_except_unverified_claims(self):
        tested = 0
        for name in ('nov2', 'nov7', 'nov8', 'nov10', 'nov12', 'nov15', 'nov25', 'nov27'):
            for url, title, _ in importlib.import_module('news_manual_'+name).EVENTS:
                if any(host in url for host in ('x.com', 'coingape.com')):
                    continue
                tested += 1
                candidate = story(title)
                with contextlib.redirect_stdout(io.StringIO()):
                    blocked, reason = e._is_hard_blocked(candidate)
                    eligible = e.matches_keywords(candidate, [], [], [])
                if 'simpsons' in title.lower() or title.startswith('Rumor: Nvidia'):
                    self.assertTrue(blocked, title)
                else:
                    self.assertFalse(blocked, (title, reason))
                    self.assertTrue(eligible, title)
        self.assertEqual(tested, 87)

    def test_unrelated_actors_are_not_merged_by_asset_country_and_infrastructure(self):
        cardano = 'action_develop | action_expand | action_integrate | action_secure | asset_stablecoin | entity_usfinancialmarkethere | entity_카르다노 | geo_us | object_infrastructure | object_network'
        anchorage = 'action_expand | action_partner | action_support | asset_eth | asset_stablecoin | entity_앵커리지디지털 | geo_us | object_custody | object_infrastructure | object_payment'
        self.assertFalse(e._same_event(cardano, anchorage))
        self.assertFalse(e._same_event(anchorage, cardano))
        self.assertTrue(e._same_event(cardano, cardano))
        generic_a = 'action_launch | entity_firm_a | geo_us | asset_stablecoin | object_payment'
        generic_b = 'action_launch | entity_firm_b | geo_us | asset_stablecoin | object_payment'
        self.assertFalse(e._same_event(generic_a, generic_b))

    def test_sponsored_bill_is_not_a_sponsored_article(self):
        for text in ('The bill was sponsored by a senator.',
                     'A representative sponsored the legislation.',
                     'The amendment is co-sponsored by two lawmakers.'):
            self.assertEqual(source_promotion_reason({'article_text':text}), '', text)
            self.assertTrue(source_promotion_reason({'article_text':text+' Sponsored content.'}))

    def test_explicitly_approved_release_is_narrow_and_requires_attribution(self):
        title = 'TRON Network Integrates with Backpack Wallet, Expanding Access to Its Multichain Ecosystem'
        candidate = story(title, article_text='Sponsored content. TRON announced wallet integration.')
        self.assertFalse(e._is_hard_blocked(candidate)[0])
        candidate['article_text'] += ' Sign up with referral code BUY.'
        self.assertTrue(e._is_hard_blocked(candidate)[0])
        unrelated = story('HTX launches tokenized stocks', article_text='Sponsored content.')
        self.assertTrue(e._is_hard_blocked(unrelated)[0])
        self.assertIn('트론 측 발표로 귀속', e._summary_prompt(title, 'source'))

    def test_political_story_with_background_stock_prices_reaches_review(self):
        candidate = story('Maxine Waters vows Trump crypto probe as Democrats prepare to take Congress',
                          article_text='A new oversight statement names a bill. Background: stock prices fell yesterday.')
        self.assertFalse(e._is_hard_blocked(candidate)[0])
        self.assertTrue(e.matches_keywords(candidate, [], [], []))

    def test_approved_korean_style_is_explicit_in_actual_fact_review_prompt(self):
        with patch.object(e, '_call_openai', return_value='{}') as api:
            e._validate_summary_against_source('나스닥 EU 토큰화 증권 규제 촉구', 'source', '나스닥이 규제 도입을 촉구함')
        prompt = api.call_args.args[0]
        for term in ('촉구함', '상태임', '종결형만으로', '사전식 정의 부재만으로', '조건 검증'):
            self.assertIn(term, prompt)

    def test_style_cache_invalidation_preserves_unrelated_decisions_and_expiry(self):
        m = json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text('utf8'))
        old = m['audit_only_previous_identities'][0]
        with cache.review_session({}, lambda:None, logger=lambda _:None) as store:
            expiry = store.clock()+1000
            for i, (kind, reason, changed) in enumerate((
                ('source_summary', '완결된 문장 기준을 충족하지 못함', True),
                ('source_summary', '핵심 용어의 설명이 없어 이해하기 어렵다', True),
                ('source_summary', '원문과 수치 불일치', False),
                ('source_summary', '이전과 동일한 사건', False),
                ('image_held', '핵심 용어의 설명이 없음', False))):
                scope = {'title':f'Unchanged topic {i}'}
                key = cache.fingerprint([cache.VERSION, old, kind, scope])
                store.data.setdefault('content_results_v1', {})[key] = {'result':{'summary':'', 'reason':reason}, 'expires':expiry}
                result = cache.content_result(kind, scope)
                if changed:self.assertIsNone(result)
                else:self.assertEqual(result['reason'], reason)
            self.assertTrue(all(row['expires']==expiry for row in store.data['content_results_v1'].values()))

    def test_new_scope_does_not_release_old_backlog(self):
        candidate = story('Ethena goes live on Stellar with USDe and sUSDe')
        for date in ('', 'bad', audit.ENABLED_AT.isoformat()):
            candidate['pub'] = date
            self.assertTrue(e._is_hard_blocked(candidate)[0], date)


if __name__ == '__main__':
    unittest.main()
