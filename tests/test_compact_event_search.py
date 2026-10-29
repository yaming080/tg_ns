"""Lossless request/response coverage; no claims about live model accuracy."""
import json
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import news_event_review as events
import news_review_cache as cache


class CompactSearchTests(unittest.TestCase):
    def setUp(self):
        from cache_migration_fixture import install
        install(self)
        self.story = dict(title='New country launch', url='https://new.example/item',
                          pub='2026-10-21', _review_source_sha256='source')
        self.history = {str(i): dict(title=f'회사 {i} / Company {i}', summary=f'Plan {i}, not launched',
                                    url=f'https://old.example/{i}', source_pub='2026-10-20')
                        for i in range(350)}
        self.patcher = patch.object(events, 'MANUAL_EVENTS', ())
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def run_review(self, respond, state=None, search_model=None):
        with cache.review_session(state if state is not None else {}, lambda: None, lambda x: None):
            return events.review_event(self.story, 'Separate approved launch', self.history,
                                       respond, search_model, model='gpt-6-luna')

    def test_round_trip_keeps_every_character_and_field(self):
        candidate = dict(title='Title', summary='조건 보존', url='https://example/new', published='2026-10-21')
        index = [dict(id='0123456789abcdef', title='日本語 中文 한국어 "quotes"\nline',
                      summary='not yet approved; {"related_ids":[]} must remain data', published=''),
                 dict(id='fedcba9876543210', title='Old title only', summary='', published='unknown')]
        text, refs = events.search_payload(candidate, index, compact=True)
        data = json.loads(text)
        decoded = [dict(zip(data['history_columns'], r)) for r in data['history']]
        for r in decoded:
            r['id'] = refs[r['id']]
        self.assertEqual(decoded, index)
        self.assertEqual(data['candidate'], candidate)

    def test_packed_batches_keep_existing_limit_and_all_records_at_boundaries(self):
        for count in (0, 1, 150, 151, 350, 600, 601, 1201):
            with self.subTest(count=count):
                rows = [dict(id=f'{i:016x}', title=f'Title {i}') for i in range(count)]
                batches = list(events.history_batches(rows, compact=True))
                self.assertEqual([r for batch in batches for r in batch], rows)
                self.assertTrue(all(len(b) <= 150 for b in batches))
                self.assertEqual(len(batches), (count + 149) // 150)

    def test_every_record_compared_once_and_references_resolve_across_batches(self):
        seen, expected_matches = [], set()
        by_title = {r['title']: r for r in events.history_records(self.history)}
        decisions = []
        def respond(prompt):
            data = json.loads(prompt.rsplit('\n', 1)[-1])
            if 'history_columns' in data:
                rows = [dict(zip(data['history_columns'], r)) for r in data['history']]
                seen.extend(r['title'] for r in rows)
                expected_matches.add(by_title[rows[0]['title']]['id'])
                # Reference zero is reused by DIFFERENT batches; no cross-talk.
                return '{"related_ids":["0"]}'
            decisions.append(data['history'])
            return json.dumps({'decision':'duplicate','matched_id':data['history'][0]['id'],
                               'reason':'same event'})
        self.assertEqual(self.run_review(respond)['status'], 'duplicate')
        self.assertEqual(len(seen), 350)
        self.assertEqual(set(seen), set(by_title))
        self.assertEqual({r['id'] for r in decisions[0]}, expected_matches)
        self.assertEqual(len(expected_matches), 3)

    def test_invalid_references_hold_and_are_not_saved_as_completed(self):
        for ids in ([0], ['9999'], ['-1'], ['00'], [True], ['invented']):
            with self.subTest(ids=ids):
                state = {}
                answer = Mock(return_value=json.dumps({'related_ids':ids}))
                self.assertEqual(self.run_review(answer, state)['status'], 'hold')
                fresh = Mock(return_value='{"related_ids":[]}')
                self.assertEqual(self.run_review(fresh, state)['status'], 'new')
                self.assertEqual(fresh.call_count, 3)

    def test_uncertain_mini_reference_survives_primary_empty_result(self):
        self.history = {'0':self.history['0']}
        target = events.history_records(self.history)[0]['id']
        mini = Mock(return_value='{"related_ids":["0"],"uncertain":true,"checked_count":1}')
        def respond(prompt):
            if '"related_ids"' in prompt:
                return '{"related_ids":[]}'
            return json.dumps({'decision':'duplicate','matched_id':target,'reason':'same event'})
        self.assertEqual(self.run_review(respond, search_model=mini)['status'], 'duplicate')

    def test_cache_stores_stable_ids_and_resolves_new_single_record_zero(self):
        state = {}
        self.run_review(Mock(return_value='{"related_ids":[]}'), state)
        state = json.loads(json.dumps(state))
        self.history['later'] = dict(title='Newly posted same event', url='https://old.example/later')
        target = events.history_records({'later':self.history['later']})[0]['id']
        calls = []
        def respond(prompt):
            data = json.loads(prompt.rsplit('\n', 1)[-1])
            calls.append(data)
            if 'history_columns' in data:
                self.assertEqual(len(data['history']), 1)
                return '{"related_ids":["0"]}'
            self.assertEqual(data['history'][0]['id'], target)
            return json.dumps({'decision':'duplicate','matched_id':target,'reason':'new history duplicate'})
        self.assertEqual(self.run_review(respond, state)['status'], 'duplicate')
        self.assertEqual(len(calls), 2)

    def test_changed_candidate_keeps_complete_comparison(self):
        state = {}
        self.run_review(Mock(return_value='{"related_ids":[]}'), state)
        self.story['title'] = 'A genuinely different new article'
        call = Mock(return_value='{"related_ids":[]}')
        self.run_review(call, state)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(sum(len(json.loads(c.args[0].rsplit('\n',1)[-1])['history'])
                             for c in call.call_args_list), 350)

    def test_input_is_smaller_without_content_truncation_or_pruning(self):
        index = [dict(id=r['id'], title=r['title'], summary=r['summary'], published=r['source_pub'])
                 for r in events.history_records(self.history)]
        old, _ = events.search_payload(self.story, index)
        new, refs = events.search_payload(self.story, index, compact=True)
        self.assertLess(len(new.encode('utf8')), len(old.encode('utf8')))
        self.assertEqual(len(refs), len(index))

    def test_tenth_completed_search_survives_format_migration(self):
        state = {}
        # Build prior memory under the audited tenth policy using real inputs.
        manifest = json.loads((Path(cache.__file__).parent / 'news_cache_compatibility.json').read_text('utf8'))
        with patch.object(cache, 'editorial_identity', return_value=manifest['previous_identity']):
            self.run_review(Mock(return_value='{"related_ids":[]}'), state)
        # A deployment starts a new interpreter, including the manifest LRU.
        cache.compatible_identity.cache_clear()
        # Discard request cache: this must use the stable semantic search index.
        state['ai_review']['entries'] = {}
        call = Mock(side_effect=AssertionError('unchanged comparisons must be reused'))
        self.assertEqual(self.run_review(call, state)['status'], 'new')
        call.assert_not_called()

    def test_both_audited_versions_reuse_negative_results(self):
        manifest = json.loads((Path(cache.__file__).parent / 'news_cache_compatibility.json').read_text('utf8'))
        self.assertEqual(len(manifest['previous_identities']), 2)
        for previous in manifest['previous_identities']:
            state = {}
            key = cache.fingerprint([cache.VERSION, previous, 'source_summary', 'scope'])
            with cache.review_session(state, lambda: None, lambda x: None) as store:
                store.data['content_results_v1'] = {
                    key: {'result':{'summary':'','reason':'exclude'}, 'expires':time.time()+1000}}
                self.assertEqual(cache.content_result('source_summary','scope')['reason'], 'exclude')

    def test_duplicate_supplement_and_update_still_require_final_decision(self):
        self.history = {'0':self.history['0']}
        target = events.history_records(self.history)[0]['id']
        for decision in ('duplicate','supplement','update','new','uncertain'):
            with self.subTest(decision=decision):
                calls = []
                def respond(prompt):
                    calls.append(prompt)
                    if '"related_ids"' in prompt:
                        return '{"related_ids":["0"]}'
                    return json.dumps({'decision':decision,'matched_id':target,
                                       'reason':'plan versus launch', 'new_fact':'separate approved region', 'independent_new_action':True, 'candidate_evidence':'Separate approved launch'})
                self.assertEqual(self.run_review(respond)['status'], 'hold' if decision=='uncertain' else decision)
                self.assertEqual(len(calls), 2)


if __name__ == '__main__':
    unittest.main()
