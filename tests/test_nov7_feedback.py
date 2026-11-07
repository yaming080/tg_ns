import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
import doorinews_editor as e
import news_nov7_scope as scope
import news_manual_nov7 as manual
import news_event_review as events
import news_review_cache as cache


def story(title, url='https://example.com/future-news'):
    return dict(title=title, url=url, pub=max(datetime.now(timezone.utc), datetime(2026,11,7,7,tzinfo=timezone.utc)).isoformat())


class Nov7FeedbackTests(unittest.TestCase):
    def test_article_types_reach_review(self):
        for i, (_, title, _) in enumerate(manual.EVENTS):
            if i in (4, 6): continue  # X direct intake remains excluded.
            s = story(title)
            with self.subTest(title=title):
                self.assertFalse(e._is_hard_blocked(s)[0], e._is_hard_blocked(s)[1])
                self.assertTrue(e.matches_keywords(s, [], [], []))

    def test_confirmed_posts_block_without_paid_review_and_are_history(self):
        with patch.object(e, '_call_openai') as api:
            for url, title, _ in manual.EVENTS:
                s = story(title, url+'?utm_source=rss')
                self.assertIn('게시', e._is_hard_blocked(s)[1])
                self.assertEqual(e.build_message(s), '')
        api.assert_not_called()
        history = events.history_records({})
        for url, _, _ in manual.EVENTS:
            self.assertTrue(any(events.url_key(r['url']) == events.url_key(url) for r in history))

    def test_bilingual_candidate_titles(self):
        for title in ('Ukraine central bank opposes crypto bill',
                      '고팍스, 해킹 위협에 거래 중단',
                      '러시아, 개인 투자자 비트코인·이더리움·USDT 거래 허용',
                      '미국 재무부·연준, 소액 암호화폐 송금 추적 계획 철회',
                      'NYSE, 토큰화 증권 명의개서기관과 계약',
                      'JPMorgan Bitcoin long-term expected returns 10%',
                      '암호화폐 거래소들, 콜드월렛 비율 강조',
                      'Iran refuses Hormuz reopening before conditions met',
                      'Iran willing to discuss nuclear issues'):
            self.assertTrue(scope.scope(story(title)), title)

    def test_exclusions_and_selective_guidance_remain(self):
        for title in ('XRP Ledger critical vulnerability patched',
                      'Sui launches new Bitcoin lending platform',
                      'JPMorgan Bitcoin price target technical analysis'):
            self.assertTrue(e._is_hard_blocked(story(title))[0], title)
        for title in ('Anonymous analyst Bitcoin expected return 10%', 'Bitcoin long-term price prediction'):
            self.assertFalse(scope.scope(story(title)))
        self.assertEqual(scope.guidance('Unrelated service launch'), '')
        self.assertIn('직접 XRP/XLM 채택', e._summary_prompt(manual.EVENTS[2][1], 'source'))
        self.assertIn('보장 수익률', e._summary_prompt(manual.EVENTS[5][1], 'source'))

    def test_unaffected_exclusions_keep_cached_expiry(self):
        manifest = json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text('utf8'))
        previous = manifest['nov7_only_previous_identities'][0]
        with cache.review_session({}, lambda: None, logger=lambda _: None) as store:
            expiry = store.clock()+1000
            for title, affected in [('Unchanged excluded article', False),
                                    ('AWS unveils cloud architecture for crypto exchange custody', False),
                                    ('Binance resumes withdrawals after hack', False),
                                    (manual.EVENTS[7][1], True)]:
                s = {'title': title}
                key = cache.fingerprint([cache.VERSION, previous, 'source_summary', s])
                store.data.setdefault('content_results_v1', {})[key] = {'result': {'summary': '', 'reason': 'excluded'}, 'expires': expiry}
                result = cache.content_result('source_summary', s)
                if affected: self.assertIsNone(result)
                else: self.assertEqual(result['reason'], 'excluded')
            self.assertEqual(store.calls, 0)
            self.assertTrue(all(r['expires']==expiry for r in store.data['content_results_v1'].values()))
