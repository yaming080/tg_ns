"""Offline paid-call and coverage regressions across serialized cron sessions."""
import json
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import news_event_review as events
import news_review_cache as cache
import doorinews_editor as editor
from test_unchanged_exclusions import answer, story


class IncrementalReviewTests(unittest.TestCase):
    def setUp(self):
        self.state = {}
        self.logs = []
        self.story = story(_review_source_sha256='body-v1')
        self.history = {str(i): dict(title=f'Company {i} launches product',
                                    url=f'https://old.example/{i}', summary=f'Evidence {i}')
                        for i in range(350)}
        self.searches = []
        self.decisions = []
        self.matches = set()
        self.decision = 'new'
        self.patch = patch.object(events, 'MANUAL_EVENTS', ())
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def respond(self, prompt):
        payload = json.loads(prompt.rsplit('\n', 1)[-1])
        if '"related_ids"' in prompt:
            rows = payload['history']
            if 'history_columns' in payload:
                rows = [dict(zip(payload['history_columns'], r)) for r in rows]
                expected = {r['title']: r['id'] for r in events.history_records(self.history)}
                ids = [r['id'] for r in rows if expected[r['title']] in self.matches]
                self.searches.append([dict(r, id=expected[r['title']]) for r in rows])
            else:
                ids = [r['id'] for r in rows if r['id'] in self.matches]
                self.searches.append(rows)
            return json.dumps({'related_ids': ids})
        self.decisions.append(payload['history'])
        return json.dumps({'decision': self.decision, 'matched_id': next(iter(self.matches), ''),
                           'reason': '근거 비교', 'new_fact': 'A separately confirmed launch'})

    def run_review(self, call=None, **options):
        with cache.review_session(self.state, lambda: None, self.logs.append):
            result = events.review_event(self.story, '새 기사 본문', self.history,
                                         call or self.respond, model=options.pop('model', 'gpt-6-luna'),
                                         **options)
        self.state = json.loads(json.dumps(self.state))
        return result

    def target(self, key):
        return events.history_records({key: self.history[key]})[0]['id']

    def test_full_initial_coverage_then_zero_searches_then_only_one_new_record(self):
        self.assertEqual(self.run_review()['status'], 'new')
        self.assertEqual(len(self.searches), 3)
        self.assertEqual(sum(map(len, self.searches)), 350)
        self.searches.clear()
        self.assertEqual(self.run_review()['status'], 'new')
        self.assertEqual(self.searches, [])
        self.history['new'] = dict(title='새 회사 출시', url='https://old.example/new')
        self.run_review()
        self.assertEqual([len(batch) for batch in self.searches], [1])

    def test_new_duplicate_still_blocks_previously_new_candidate(self):
        self.run_review()
        self.history['new'] = dict(title='같은 사건 번역 보도', url='https://old.example/new')
        self.matches = {self.target('new')}
        self.decision = 'duplicate'
        self.assertEqual(self.run_review()['status'], 'duplicate')
        self.assertEqual(len(self.searches[-1]), 1)

    def test_edited_title_summary_date_rechecks_each_changed_record(self):
        self.run_review()
        self.searches.clear()
        self.history['1']['title'] = 'Corrected title'
        self.history['2']['summary'] = 'Corrected evidence'
        self.history['3']['source_pub'] = '2026-10-21'
        self.run_review()
        self.assertEqual([len(x) for x in self.searches], [3])

    def test_deleted_match_is_not_retained_in_decision(self):
        self.matches = {self.target('2')}
        self.decision = 'uncertain'
        self.assertEqual(self.run_review()['status'], 'hold')
        del self.history['2']
        self.searches.clear()
        self.decisions.clear()
        self.assertEqual(self.run_review()['status'], 'new')
        self.assertEqual(self.searches, [])
        self.assertEqual(self.decisions, [])

    def test_source_model_and_policy_changes_require_complete_new_search(self):
        self.run_review()
        self.searches.clear()
        self.story['_review_source_sha256'] = 'changed'
        self.run_review()
        self.assertEqual(sum(map(len, self.searches)), 350)
        self.searches.clear()
        self.run_review(model='another-model')
        self.assertEqual(sum(map(len, self.searches)), 350)
        self.searches.clear()
        with patch.object(cache, 'editorial_identity', return_value='changed-policy'):
            self.run_review()
        self.assertEqual(sum(map(len, self.searches)), 350)

    def test_invalid_batch_keeps_successful_batches_but_never_skips_unchecked(self):
        calls = [0]
        def broken(prompt):
            calls[0] += 1
            if calls[0] == 2:
                return '{"related_ids":["nonexistent-id"]}'
            return self.respond(prompt)
        self.assertEqual(self.run_review(broken)['status'], 'hold')
        completed = sum(map(len, self.searches))
        self.assertGreater(completed, 0)
        self.searches.clear()
        self.assertEqual(self.run_review()['status'], 'new')
        self.assertEqual(sum(map(len, self.searches)), 350 - completed)

    def test_timeout_does_not_mark_records_compared(self):
        with self.assertRaises(TimeoutError):
            self.run_review(Mock(side_effect=TimeoutError))
        self.run_review()
        self.assertEqual(sum(map(len, self.searches)), 350)

    def test_uncertain_cheap_search_requires_primary_success(self):
        cheap = Mock(return_value='{"related_ids":[],"uncertain":true,"checked_count":1}')
        self.history = {'1': self.history['1']}
        self.assertEqual(self.run_review(Mock(return_value=''), search_model=cheap)['status'], 'hold')
        self.assertEqual(self.run_review(search_model=cheap)['status'], 'new')
        self.assertEqual(len(self.searches), 1)
        self.assertEqual(cheap.call_count, 2)

    def test_changed_full_evidence_beyond_search_excerpt_reaches_decision(self):
        self.history = {'1': dict(self.history['1'], summary='a' * 600 + ' old')}
        self.matches = {self.target('1')}
        self.decision = 'uncertain'
        self.run_review()
        self.searches.clear()
        self.history['1']['summary'] = 'a' * 600 + ' newly corrected full evidence'
        self.run_review()
        self.assertEqual(self.searches, [])
        self.assertIn('newly corrected', self.decisions[-1][0]['summary'])

    def test_unidentified_model_never_reuses_incremental_memory(self):
        self.run_review(model=None)
        self.run_review(model=None)
        self.assertEqual(sum(map(len, self.searches)), 700)

    def test_old_title_only_records_are_all_compared(self):
        for row in self.history.values():
            row.pop('summary')
        self.run_review()
        self.assertEqual(sum(map(len, self.searches)), 350)

    def test_expired_search_memory_requires_full_review(self):
        self.run_review()
        for entry in self.state['ai_review']['content_results_v1'].values():
            entry['expires'] = time.time() - 1
        self.searches.clear()
        self.run_review()
        self.assertEqual(sum(map(len, self.searches)), 350)


class SourceReuseTests(unittest.TestCase):
    def setUp(self):
        from cache_migration_fixture import install
        install(self)

    def test_legacy_source_scope_migrates_then_teaser_change_costs_zero(self):
        s = story(desc='Original teaser')
        scope = {k: str(s.get(k, '')) for k in ('url', 'title', 'pub')}
        scope.update(source_sha256=cache.fingerprint(s['article_text']),
                     page_published_at='', source_kind='provided_text',
                     description_sha256=cache.fingerprint(s['desc']),
                     model='gpt-6-luna', options=cache.request_options('gpt-6-luna'))
        manifest = json.loads((Path(cache.__file__).parent / 'news_cache_compatibility.json').read_text('utf8'))
        key = cache.fingerprint([cache.VERSION, manifest['previous_identity'], 'source_summary', scope])
        state = {}
        client = Mock()
        runtime = dict(OPENAI_MODEL='gpt-6-luna', openai_client=client)
        with patch.object(editor, '_RUNTIME', runtime), patch.object(
                editor, '_is_hard_blocked', return_value=(False, '')):
            with cache.review_session(state, lambda: None, lambda x: None) as store:
                store.data['content_results_v1'] = {
                    key: {'expires': time.time() + 1000, 'result': {'summary': '', 'reason': '기존 제외'}}}
                self.assertEqual(editor._rewrite_summary(s), '')
            state = json.loads(json.dumps(state))
            s['desc'] = 'A different RSS teaser, unchanged fetched article'
            with cache.review_session(state, lambda: None, lambda x: None):
                self.assertEqual(editor._rewrite_summary(s), '')
        client.responses.create.assert_not_called()

    def test_actual_rss_fallback_change_rechecks_and_explains_input_change(self):
        state, logs = {}, []
        client = Mock()
        client.responses.create.return_value = answer('SKIP')
        s = story(article_text='', desc='Full RSS source evidence', _source_kind='rss_description')
        runtime = dict(OPENAI_MODEL='gpt-6-luna', openai_client=client)
        with patch.object(editor, '_RUNTIME', runtime), patch.object(
                editor, '_is_hard_blocked', return_value=(False, '')):
            for desc in ('Full RSS source evidence', 'Full RSS source evidence', 'Changed RSS evidence'):
                s['desc'] = desc
                with cache.review_session(state, lambda: None, logs.append):
                    editor._rewrite_summary(s)
        self.assertEqual(client.responses.create.call_count, 2)
        self.assertTrue(any('source_sha256' in line for line in logs))
        self.assertNotIn('Changed RSS evidence', json.dumps(state['ai_review']['source_identity_v1']))

    def test_release_migration_reuses_prior_outcome_without_extending_expiry(self):
        manifest = json.loads((Path(cache.__file__).parent / 'news_cache_compatibility.json').read_text('utf8'))
        self.assertEqual(cache.editorial_identity(), manifest['current_identity'])
        state = {}
        scope = {'source': 'same'}
        expires = time.time() + 1000
        oldkey = cache.fingerprint([cache.VERSION, manifest['previous_identity'], 'source_summary', scope])
        with cache.review_session(state, lambda: None, lambda x: None) as store:
            store.data['content_results_v1'] = {
                oldkey: {'expires': expires, 'result': {'summary': '', 'reason': '제외'}}}
            self.assertEqual(cache.content_result('source_summary', scope)['reason'], '제외')
            self.assertNotIn(oldkey, store.data['content_results_v1'])
            self.assertEqual(next(iter(store.data['content_results_v1'].values()))['expires'], expires)

    def test_future_policy_cannot_migrate_prior_outcome(self):
        manifest = json.loads((Path(cache.__file__).parent / 'news_cache_compatibility.json').read_text('utf8'))
        state = {}
        scope = {'source': 'same'}
        oldkey = cache.fingerprint([cache.VERSION, manifest['previous_identity'], 'source_summary', scope])
        with cache.review_session(state, lambda: None, lambda x: None) as store:
            store.data['content_results_v1'] = {
                oldkey: {'expires': time.time() + 1000, 'result': {'summary': '', 'reason': '제외'}}}
            with patch.object(cache, 'editorial_identity', return_value='future-or-mixed-release'):
                self.assertIsNone(cache.content_result('source_summary', scope))


if __name__ == '__main__':
    unittest.main()
