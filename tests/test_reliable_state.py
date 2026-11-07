import copy
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone

import news_state_guard as guard
import news_state_recovery as recovery
from news_resume import configure_resume_boundary, resume_exclusion_reason
import test_publication_state as lifecycle


class ReliableStateTests(unittest.TestCase):
    setUp = lifecycle.GuardLifecycleTests.setUp
    raw = lifecycle.GuardLifecycleTests.raw
    clone = lifecycle.GuardLifecycleTests.clone
    commit_push = lifecycle.GuardLifecycleTests.commit_push
    remote_json = lifecycle.GuardLifecycleTests.remote_json
    begin = lifecycle.GuardLifecycleTests.begin
    def sent_state(self):
        state = guard.read_json(self.worker/guard.STATE)
        state['posted']['sent'] = {'title': 'Already delivered'}
        state['ai_review'] = {'cost': 0.07}
        guard.write_json(self.worker/guard.STATE, state)
        return state

    def test_transient_push_and_lost_response_do_not_duplicate_commits(self):
        self.begin()
        self.sent_state()
        original = guard.git
        failures = []
        def flaky(root, *args):
            if args[0] == 'push' and not failures:
                failures.append(1)
                raise RuntimeError('temporary failure')
            return original(root, *args)
        before = int(self.raw(self.worker, 'rev-list', '--count', 'HEAD'))
        with patch.object(guard, 'git', side_effect=flaky), patch.object(guard.time, 'sleep'):
            guard.finish(self.worker, '100', '1')
        self.assertEqual(int(self.raw(self.worker, 'rev-list', '--count', 'HEAD')), before+1)
        self.begin(run='101')
        def lost(root, *args):
            result = original(root, *args)
            if args[0] == 'push': raise RuntimeError('response lost')
            return result
        with patch.object(guard, 'git', side_effect=lost):
            guard.finish(self.worker, '101', '1')
        self.assertEqual(self.remote_json(guard.MARKER)['status'], 'complete')

    def test_remote_state_change_is_never_overwritten(self):
        self.begin()
        self.sent_state()
        other = self.clone('other')
        state = guard.read_json(other/guard.STATE)
        state['posted']['other'] = {'title': 'Concurrent delivery'}
        guard.write_json(other/guard.STATE, state)
        self.commit_push(other)
        with self.assertRaisesRegex(ValueError, '자동 덮어쓰기 금지'):
            guard.finish(self.worker, '100', '1')
        self.assertIn('other', self.remote_json(guard.STATE)['posted'])
        self.assertEqual(self.remote_json(guard.MARKER)['status'], 'pending')
        self.assertIn('sent', guard.read_json(self.worker/guard.STATE)['posted'])

    def test_certified_backup_recovers_without_replaying_and_blocks_backlog(self):
        self.begin()
        expected = self.sent_state()
        recovery.checkpoint(self.worker, '100', '1')
        original = guard.git
        def blocked(root, *args):
            if args[0] == 'push': raise RuntimeError('outage')
            return original(root, *args)
        backup = self.root/'backup'; backup.mkdir()
        for name in (guard.STATE, guard.MARKER, recovery.RECEIPT):
            shutil.copyfile(self.worker/name, backup/name)
        with patch.object(guard, 'git', side_effect=blocked), patch.object(guard.time, 'sleep'), self.assertRaises(RuntimeError):
            guard.finish(self.worker, '100', '1')
        self.assertEqual(self.remote_json(guard.MARKER)['status'], 'pending')
        def fetch(repo, marker, target):
            for name in (guard.STATE, guard.MARKER, recovery.RECEIPT):
                shutil.copyfile(backup/name, Path(target)/name)
            return True
        next_worker = self.clone('next')
        with patch.dict(os.environ, {'GITHUB_REPOSITORY': 'owner/repo', 'GH_TOKEN': 'offline-test'}), patch.object(recovery, 'fetch_completed_snapshot', side_effect=fetch):
            self.begin(next_worker, run='101')
        saved = self.remote_json(guard.STATE)
        self.assertEqual(saved['posted'], expected['posted'])
        self.assertEqual(saved['ai_review'], expected['ai_review'])
        self.assertGreater(datetime.fromisoformat(saved['publish_not_before_utc']), datetime(2026, 11, 1, tzinfo=timezone.utc))
        self.assertEqual(self.remote_json(guard.MARKER)['run_id'], '101')

    def test_tampered_or_unrelated_backup_refused(self):
        self.begin()
        base = self.root/'base.json'
        shutil.copyfile(self.worker/guard.STATE, base)
        marker = guard.read_json(self.worker/guard.MARKER)
        self.sent_state()
        recovery.checkpoint(self.worker, '100', '1')
        self.assertIn('sent', recovery.validated_snapshot(self.worker, marker, base)['posted'])
        bad = copy.deepcopy(marker); bad['attempt'] = '2'
        with self.assertRaises(ValueError): recovery.validated_snapshot(self.worker, bad, base)
        state = guard.read_json(self.worker/guard.STATE); state['ai_review']['cost'] = 10
        guard.write_json(self.worker/guard.STATE, state)
        with self.assertRaisesRegex(ValueError, '검증값'): recovery.validated_snapshot(self.worker, marker, base)


class RecoveryMetadataTests(unittest.TestCase):
    def test_only_failed_completed_certified_run_downloads(self):
        marker = {'run_id': '100', 'attempt': '1'}
        run = dict(id=100, head_branch='main', repository={'full_name': 'owner/repo'}, status='completed', conclusion='failure', run_attempt=1)
        jobs = {'jobs': [{'status': 'completed', 'steps': [{'name': recovery.CHECKPOINT_STEP, 'conclusion': 'success'}]}]}
        artifacts = {'artifacts': [{'name': 'publication-state-100-1', 'expired': False, 'workflow_run': {'id': 100}}]}
        with patch.object(recovery, 'gh', side_effect=[json.dumps(run), json.dumps(jobs), json.dumps(artifacts), '']) as gh:
            self.assertTrue(recovery.fetch_completed_snapshot('owner/repo', marker, 'unused'))
            self.assertEqual(gh.call_count, 4)
        for field, value in [('status', 'in_progress'), ('conclusion', 'cancelled'), ('head_branch', 'other'), ('run_attempt', 2)]:
            with patch.object(recovery, 'gh', return_value=json.dumps(dict(run, **{field: value}))) as gh:
                self.assertFalse(recovery.fetch_completed_snapshot('owner/repo', marker, 'unused'))
                self.assertEqual(gh.call_count, 1)
        jobs['jobs'][0]['steps'][0]['conclusion'] = 'skipped'
        with patch.object(recovery, 'gh', side_effect=[json.dumps(run), json.dumps(jobs)]):
            self.assertFalse(recovery.fetch_completed_snapshot('owner/repo', marker, 'unused'))

    def test_resume_boundary_can_only_advance(self):
        with patch.dict(os.environ, {'NEWS_PUBLISH_NOT_BEFORE_UTC': '2026-11-07T06:00:00Z'}):
            configure_resume_boundary({'publish_not_before_utc': '2026-11-07T07:00:00Z'})
            self.assertTrue(resume_exclusion_reason({'pub': '2026-11-07T06:59:59Z'}))
            self.assertFalse(resume_exclusion_reason({'pub': '2026-11-07T07:00:01Z'}))
            configure_resume_boundary({'publish_not_before_utc': '2026-11-01T00:00:00Z'})
            self.assertTrue(resume_exclusion_reason({'pub': '2026-11-07T06:59:59Z'}))
            with self.assertRaises(ValueError): configure_resume_boundary({'publish_not_before_utc': 'bad'})

    def test_all_workflows_certify_before_snapshot(self):
        for name in ('news-bot.yml', 'news-single-test.yml', 'news-source-baseline.yml'):
            text = (guard.ROOT/'.github/workflows'/name).read_text('utf8')
            self.assertLess(text.index('python news_state_guard.py checkpoint'), text.index('uses: actions/upload-artifact'))
            self.assertIn(recovery.RECEIPT, text)
            self.assertIn('GH_TOKEN: ${{ github.token }}', text)
