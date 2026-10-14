import copy
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
import doorinews_editor as editor
import news_state_guard as guard
from news_event_review import history_records

NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)
RECORDS = json.loads((guard.ROOT/'news_confirmed_sends.json').read_text(encoding='utf8'))['records']


class RecoveryTests(unittest.TestCase):
    def test_confirmed_sends_recovered_once_without_changing_cost_or_old_posts(self):
        state = {'posted': {'old': {'title': 'existing'}}, 'ai_review': {'cost': 1.23}}
        self.assertEqual(guard.recover_confirmed(state, NOW), len(RECORDS))
        self.assertEqual(state['posted']['old'], {'title': 'existing'})
        self.assertEqual(state['ai_review'], {'cost': 1.23})
        saved = copy.deepcopy(state)
        self.assertEqual(guard.recover_confirmed(state, NOW), 0)
        self.assertEqual(state, saved)

    def test_hash_uses_actual_runtime_editor_override_including_korean(self):
        state = {'posted': {}}
        guard.recover_confirmed(state, NOW)
        for record in RECORDS:
            key = editor.story_hash(record['title'])
            self.assertEqual(len(key), 16)
            self.assertEqual(state['posted'][key]['title'], record['title'])

    def test_existing_richer_entry_is_never_overwritten(self):
        record = {**RECORDS[0], 'summary': 'complete caption', 'url': 'https://example.com/original'}
        state = {'posted': {'legacy-key': record}}
        guard.recover_confirmed(state, NOW)
        self.assertEqual(state['posted']['legacy-key'], record)
        self.assertNotIn(editor.story_hash(record['title']), state['posted'])

    def test_recovered_titles_without_urls_are_searchable_history(self):
        state = {'posted': {}}
        guard.recover_confirmed(state, NOW)
        titles = {r['title'] for r in history_records(state['posted'])}
        for record in RECORDS:
            self.assertIn(record['title'], titles)
            self.assertIn('actions/runs/', record['recovery_evidence'])

    def test_bad_state_fails_closed(self):
        for value in ([], {}, {'posted': []}, {'posted': {'bad': None}}, {'posted': {'bad': {}}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                guard.recover_confirmed(value, NOW)

    def test_recovery_does_not_resurrect_expired_or_future_posts(self):
        for now in (NOW-timedelta(days=5), NOW+timedelta(days=31)):
            state = {'posted': {}}
            self.assertEqual(guard.recover_confirmed(state, now), 0)


class GuardLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root/'remote.git'
        self.raw(self.root, 'init', '--bare', '--initial-branch=main', str(self.remote))
        self.seed = self.clone('seed')
        guard.write_json(self.seed/guard.STATE, {'posted': {'old': {'title': 'Existing article'}}})
        self.commit_push(self.seed)
        self.worker = self.clone('worker')

    def raw(self, root, *args):
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                                text=True, encoding='utf8')
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout.strip()

    def clone(self, name):
        target = self.root/name
        self.raw(self.root, 'clone', str(self.remote), str(target))
        self.raw(target, 'config', 'user.name', 'Offline test')
        self.raw(target, 'config', 'user.email', 'test@example.invalid')
        return target

    def commit_push(self, root):
        self.raw(root, 'add', '.')
        self.raw(root, 'commit', '-m', 'offline fixture')
        self.raw(root, 'push', 'origin', 'HEAD:main')

    def remote_json(self, name):
        return json.loads(self.raw(self.remote, 'show', 'main:'+name))

    def begin(self, root=None, run='100', attempt='1'):
        guard.begin(root or self.worker, run, attempt, NOW, records=[])

    def test_pending_is_remote_before_send_and_completion_saves_state_atomically(self):
        self.begin()
        self.assertEqual(self.remote_json(guard.MARKER)['status'], 'pending')
        state = guard.read_json(self.worker/guard.STATE)
        state['posted']['new'] = {'title': 'Newly sent article'}
        guard.write_json(self.worker/guard.STATE, state)
        guard.finish(self.worker, '100', '1')
        self.assertEqual(self.remote_json(guard.MARKER)['status'], 'complete')
        self.assertIn('new', self.remote_json(guard.STATE)['posted'])
        self.begin(self.clone('next'), run='101')

    def test_interrupt_after_send_blocks_next_run_and_same_run_retry(self):
        self.begin()
        for name, run, attempt in (('next', '101', '1'), ('retry', '100', '2')):
            with self.assertRaisesRegex(RuntimeError, '저장 미완료'):
                self.begin(self.clone(name), run, attempt)

    def test_failed_final_push_leaves_remote_pending_and_retains_local_backup_state(self):
        self.begin()
        other = self.clone('other')
        (other/'README.txt').write_text('concurrent code edit', encoding='utf8')
        self.commit_push(other)
        state = guard.read_json(self.worker/guard.STATE)
        state['posted']['sent'] = {'title': 'Send succeeded but save failed'}
        guard.write_json(self.worker/guard.STATE, state)
        with self.assertRaisesRegex(RuntimeError, 'Git push'):
            guard.finish(self.worker, '100', '1')
        self.assertEqual(self.remote_json(guard.MARKER)['status'], 'pending')
        self.assertIn('sent', guard.read_json(self.worker/guard.STATE)['posted'])
        with self.assertRaisesRegex(RuntimeError, '저장 미완료'):
            self.begin(self.clone('next'), run='101')

    def test_failed_initial_push_does_not_arm_publication(self):
        original = guard.git
        def rejected(root, *args):
            if args[0] == 'push': raise RuntimeError('push rejected')
            return original(root, *args)
        with patch.object(guard, 'git', side_effect=rejected), self.assertRaises(RuntimeError):
            self.begin()
        self.assertNotIn(guard.MARKER, self.raw(self.remote, 'ls-tree', '--name-only', 'main').splitlines())

    def test_old_queued_checkout_is_rejected_before_publish(self):
        self.begin()
        stale = self.clone('queued')
        state = guard.read_json(self.worker/guard.STATE)
        state['posted']['base'] = {'title': 'Base Earn & Borrow'}
        guard.write_json(self.worker/guard.STATE, state)
        guard.finish(self.worker, '100', '1')
        with self.assertRaisesRegex(RuntimeError, 'main이 변경'):
            self.begin(stale, run='101')
        fresh = self.clone('fresh')
        self.begin(fresh, run='102')
        self.assertIn('base', guard.read_json(fresh/guard.STATE)['posted'])

    def test_missing_state_is_never_treated_as_first_run(self):
        (self.worker/guard.STATE).unlink()
        with self.assertRaises(FileNotFoundError): self.begin()

    def test_invalid_pending_marker_blocks_even_when_state_is_valid(self):
        guard.write_json(self.worker/guard.MARKER, {'status': 'complete'})
        with self.assertRaises(ValueError): self.begin()

    def test_finish_cannot_clear_another_run_or_attempt(self):
        self.begin()
        for run, attempt in (('101', '1'), ('100', '2')):
            with self.assertRaisesRegex(RuntimeError, '다른 실행'):
                guard.finish(self.worker, run, attempt)
        self.assertEqual(self.remote_json(guard.MARKER)['status'], 'pending')

    def test_corrupt_state_prevents_completion(self):
        self.begin()
        (self.worker/guard.STATE).write_text('{bad', encoding='utf8')
        with self.assertRaises(json.JSONDecodeError): guard.finish(self.worker, '100', '1')
        self.assertEqual(self.remote_json(guard.MARKER)['status'], 'pending')


class WorkflowSafetyTests(unittest.TestCase):
    def test_all_state_writers_use_current_branch_and_guarded_persistence(self):
        for name in ('news-bot.yml', 'news-single-test.yml', 'news-source-baseline.yml'):
            text = (guard.ROOT/'.github/workflows'/name).read_text(encoding='utf8')
            with self.subTest(name=name):
                self.assertIn('group: telegram-news-bot', text)
                self.assertIn('cancel-in-progress: false', text)
                self.assertIn('ref: main', text)
                self.assertLess(text.index('python news_state_guard.py begin'), text.index('id: run_bot'))
                self.assertLess(text.index('uses: actions/upload-artifact@v4'), text.index('python news_state_guard.py finish'))
                self.assertIn("steps.publication_guard.outcome == 'success' && steps.run_bot.outcome == 'success'", text)
                self.assertNotIn('git pull --rebase', text)
