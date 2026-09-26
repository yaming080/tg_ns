import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import news_sources as n
import doorinews_editor as e

NOW = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)
URL = 'https://example.com/feed/'


def story(slug, offset=0):
    return {'title': 'XRP payments launch', 'url': 'https://example.com/' + slug,
            'pub': (NOW + timedelta(seconds=offset)).isoformat()}


class SourceTests(unittest.TestCase):
    def test_first_run_suppresses_all_and_persists_across_restart(self):
        state = {'posted': {'keep': {'title': 'already posted'}}}
        self.assertEqual(n.after_baseline(state, URL, [story('old', -10), story('future', 90)], NOW), [])
        state = json.loads(json.dumps(state))
        result = n.after_baseline(state, URL, [story('old', 10), story('future', 90), story('new', 30)], NOW + timedelta(seconds=100))
        self.assertEqual([s['url'] for s in result], ['https://example.com/new'])
        self.assertIn('keep', state['posted'])

    def test_rotating_old_missing_invalid_equal_future_dates_cannot_publish(self):
        state = {};n.after_baseline(state, URL, [story('old', -10)], NOW)
        candidates = [story('unseen-old', -20), story('equal'), story('future', 200),
                      dict(story('missing'), pub=''), dict(story('bad'), pub='not a date'),
                      dict(story('naive'), pub='2026-09-26T12:00:01')]
        self.assertEqual(n.after_baseline(state, URL, candidates, NOW + timedelta(seconds=100)), [])

    def test_empty_or_failed_first_fetch_does_not_arm_source(self):
        state = {};self.assertEqual(n.after_baseline(state, URL, [], NOW), [])
        self.assertNotIn(URL, state['source_baselines'])
        with patch.object(n, 'NEW_FEEDS', [('test', URL)]):
            self.assertEqual(n.collect_new_sources(state, Mock(side_effect=TimeoutError), Mock(), lambda x: None, NOW), [])
        self.assertNotIn(URL, state['source_baselines'])
        self.assertEqual(n.after_baseline(state, URL, [story('old')], NOW), [])

    def test_new_source_is_initialized_independently_and_storage_failure_stops(self):
        state = {};n.after_baseline(state, URL, [story('old')], NOW)
        self.assertEqual(n.after_baseline(state, URL + 'second', [story('new', 1)], NOW + timedelta(seconds=3)), [])
        xml = '<rss><channel><item><title>BTC</title><link>https://example.com/a</link></item></channel></rss>'
        with patch.object(n, 'NEW_FEEDS', [('test', URL)]), self.assertRaises(OSError):
            n.collect_new_sources({}, lambda u: xml, Mock(side_effect=OSError), lambda x: None, NOW)

    def test_corrupt_baseline_is_fail_closed(self):
        for record in ({}, {'activated_at':'broken','baseline_urls':[]}, 'bad'):
            with self.subTest(record=record), self.assertRaises(ValueError):
                n.after_baseline({'source_baselines': {URL:record}}, URL, [story('new', 1)], NOW)

    def test_parser_reads_whole_feed_and_deduplicates_tracking_links(self):
        xml = '<rss><channel>' + ''.join(f'<item><title>XRP {i}</title><link>https://example.com/{i}</link><pubDate>Sat, 26 Sep 2026 13:00:00 +0000</pubDate></item>' for i in range(20)) + '</channel></rss>'
        self.assertEqual(len(n.parse_feed(xml)), 20)
        state = {};n.after_baseline(state, URL, [story('old')], NOW)
        rows = [story('new?utm_source=a', 1),story('new?utm_source=b', 1)]
        self.assertEqual(len(n.after_baseline(state, URL, rows, NOW + timedelta(seconds=2))), 1)

    def test_exact_rin_and_unknown_quote_currency_listings_never_reach_ai(self):
        titles = ['RIN, 엑스티 거래소 상장…실물 기기 연결하는 리앤체인 기반',
                  'RIN/USDT trading launches on XT', 'RIN 상장, USDT 마켓 거래 지원',
                  'RIN-USDC spot trading starts', 'ABC launches on Ethereum network']
        # Ethereum infrastructure is an actual title subject in the last case;
        # the listing cases must not gain relevance from source background.
        for title in titles[:-1]:
            s={'title':title,'desc':'RIN is a token on Ethereum. RIN/USDT trading begins.',
               'article_text':'RIN token listing. Background: Bitcoin and Ethereum markets.'}
            with self.subTest(title=title), patch.object(e, '_call_openai') as ai:
                self.assertFalse(e.matches_keywords(s, [], [], []))
                self.assertEqual(e.build_message(s), '')
                ai.assert_not_called()
        self.assertTrue(e.matches_keywords({'title':'XRP/USDT trading launches on new exchange'}, [], [], []))

    def test_first_live_main_run_does_not_send_new_source_backlog(self):
        import ast, os
        code = (Path(__file__).resolve().parents[1]/'doorinews_bot.py').read_text(encoding='utf-8')
        nodes = ast.parse(code).body
        selected = [next(x for x in reversed(nodes) if isinstance(x, ast.FunctionDef) and x.name == name) for name in ('main','load_state','save_state')]
        xml = '<rss><channel><item><title>Bitcoin payment service launches</title><link>https://example.com/old</link><pubDate>Sat, 26 Sep 2026 10:00:00 +0000</pubDate></item></channel></rss>'
        with tempfile.TemporaryDirectory() as tmp:
            state_file = str(Path(tmp)/'state.json')
            prepare = Mock();send = Mock()
            ns = {'os':os,'json':json,'STATE_FILE':state_file,'log':lambda x:None,
                  'prune_posted_older_than':lambda p,days:p,'FEEDS':[],
                  'collect_new_sources':n.collect_new_sources,'http_get':lambda u:xml,
                  'INITIAL_RUN':False,'POST_ENABLED':True,'prepare_publication':prepare,
                  'send_reviewed_photo':send}
            exec(compile(ast.Module(body=selected,type_ignores=[]),'<live main>','exec'),ns)
            with patch.object(n,'NEW_FEEDS',[('test',URL)]):
                ns['main']()
            prepare.assert_not_called();send.assert_not_called()
            self.assertIn(URL,json.loads(Path(state_file).read_text(encoding='utf-8'))['source_baselines'])



if __name__ == '__main__':
    unittest.main()
