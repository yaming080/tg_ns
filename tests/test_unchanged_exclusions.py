"""Persisted cron-run regressions. Fake Responses only; never sends or fetches."""
from datetime import datetime, timezone
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import doorinews_editor as editor
import news_event_review as events
import news_images as images
import news_review_cache as cache
from news_publication import prepare_publication

FIELDS = ('faithful', 'conditions_preserved', 'allowed_category',
          'new_substantive_fact', 'source_sufficient', 'understandable')
SUMMARY = '리플이 싱가포르에서 XRP 결제 서비스 정식 라이선스를 취득했다고 밝힘'


def matching_reference(prompt, title):
    data = json.loads(prompt.rsplit('\n', 1)[-1])
    rows = data['history']
    if 'history_columns' in data:
        rows = [dict(zip(data['history_columns'], r)) for r in rows]
    return [r['id'] for r in rows if r['title'] == title]


def answer(text, status='completed'):
    return SimpleNamespace(output_text=text, status=status, usage=None)


def verdict(flag='publish', fields=FIELDS, approved=True):
    return json.dumps({flag: approved, 'reason': '원문과 핵심 대상 대조',
                       'checks': dict.fromkeys(fields, approved)})


def story(**updates):
    result = dict(title='Ripple receives final approval for XRP payments license in Singapore',
                  url='https://example.com/new', pub=datetime.now(timezone.utc).isoformat(),
                  article_text='Ripple received final approval for an XRP payments license in Singapore.')
    result.update(updates)
    return result


class UnchangedExclusionsTests(unittest.TestCase):
    def setUp(self):
        self.state = {'posted': {}}
        self.client = Mock()
        self.runtime = {'OPENAI_MODEL': 'gpt-6-luna', 'openai_client': self.client}
        self.now = datetime.now(timezone.utc).timestamp()
        self.logs = []
        self.s = story()

    def run_editor(self, source=None):
        with patch.object(editor, '_RUNTIME', self.runtime), patch.object(
                editor, '_is_hard_blocked', return_value=(False, '')):
            with cache.review_session(self.state, lambda: None, self.logs.append) as store:
                store.clock = lambda: self.now
                result = editor._rewrite_summary(source or self.s)
        self.state = json.loads(json.dumps(self.state))  # A new Actions process.
        return result

    def test_explicit_skip_survives_next_day_and_request_cache_eviction(self):
        self.client.responses.create.return_value = answer('SKIP')
        self.assertEqual(self.run_editor(), '')
        self.state['ai_review']['entries'] = {}
        self.now += 25 * 3600
        self.assertEqual(self.run_editor(), '')
        self.assertEqual(self.client.responses.create.call_count, 1)
        self.assertTrue(any('명시적 제외' in line for line in self.logs))
        self.assertEqual(self.state['posted'], {})

    def test_valid_source_rejection_survives_changed_date(self):
        self.client.responses.create.side_effect = [answer(SUMMARY), answer(verdict(approved=False))]
        self.assertEqual(self.run_editor(), '')
        self.state['ai_review']['entries'] = {}
        self.now += 2 * 86400
        self.assertEqual(self.run_editor(), '')
        self.assertEqual(self.client.responses.create.call_count, 2)
        self.assertIn('원문 대조 제외', self.s['_preparation_reason'])

    def test_changed_evidence_rechecks_but_redundant_description_does_not(self):
        self.client.responses.create.return_value = answer('SKIP')
        self.run_editor()
        for changes in ({'article_text': self.s['article_text'] + ' A new country was added.'},
                        {'title': self.s['title'] + ' updated'}, {'pub': '2026-10-21T01:00:00Z'},
                        {'page_published_at': '2026-10-21'}, {'_source_kind': 'rss_fallback'},
                        {'desc': 'Different source evidence'}):
            self.run_editor(dict(self.s, **changes))
        self.runtime['OPENAI_MODEL'] = 'gpt-5.4'
        self.run_editor()
        self.assertEqual(self.client.responses.create.call_count, 7)

    def test_changed_policy_does_not_reuse_completed_source_summary(self):
        self.client.responses.create.return_value = answer('SKIP')
        self.run_editor()
        # Clear only exact requests to isolate the outcome's policy boundary.
        self.state['ai_review']['entries'] = {}
        with patch.object(cache, 'editorial_identity', return_value='new policy'):
            self.run_editor()
        self.assertEqual(self.client.responses.create.call_count, 2)

    def test_whitespace_only_changes_do_not_rebill(self):
        self.client.responses.create.return_value = answer('SKIP')
        self.run_editor()
        self.run_editor(dict(self.s, article_text=self.s['article_text'].replace(' ', '\n  ')))
        self.assertEqual(self.client.responses.create.call_count, 1)

    def test_source_is_fetched_before_memory_and_updated_body_rechecked(self):
        self.client.responses.create.return_value = answer('SKIP')
        getter = Mock(side_effect=['First full body.', 'First full body.', 'New full body.'])
        self.runtime['get_best_source_text'] = getter
        s = dict(self.s)
        del s['article_text']
        for _ in range(3):
            self.run_editor(s)
        self.assertEqual(getter.call_count, 3)
        self.assertEqual(self.client.responses.create.call_count, 2)

    def test_incomplete_empty_and_invalid_responses_are_not_permanent_rejections(self):
        for bad in (answer('SKIP', 'incomplete'), answer('')):
            with self.subTest(bad=bad):
                self.state = {'posted': {}}
                self.client.responses.create.reset_mock()
                self.client.responses.create.side_effect = [bad, answer('SKIP')]
                self.assertEqual(self.run_editor(), '')
                self.assertEqual(self.run_editor(), '')
                self.assertEqual(self.client.responses.create.call_count, 2)
        self.state = {'posted': {}}
        self.client.responses.create.reset_mock()
        self.client.responses.create.side_effect = [answer(SUMMARY), answer('invalid JSON'),
                                                   answer(verdict(approved=False))]
        self.run_editor()
        self.run_editor()
        self.assertEqual(self.client.responses.create.call_count, 3)

    def test_network_error_does_not_blacklist_source(self):
        self.client.responses.create.side_effect = [TimeoutError(), answer('SKIP')]
        self.run_editor()
        self.run_editor()
        self.assertEqual(self.client.responses.create.call_count, 2)

    def test_completed_oversized_summary_does_not_restart_paid_compression(self):
        self.client.responses.create.return_value = answer('리플이 새로운 결제 서비스를 발표했다고 밝힘. ' * 100)
        self.assertEqual(self.run_editor(), '')
        calls = self.client.responses.create.call_count
        self.state['ai_review']['entries'] = {}
        self.now += 86400
        self.assertEqual(self.run_editor(), '')
        self.assertEqual(self.client.responses.create.call_count, calls)
        self.assertIn('길이 제한', self.s['_preparation_reason'])

    def test_approved_summary_still_obeys_current_hard_filters(self):
        self.client.responses.create.side_effect = [answer(SUMMARY), answer(verdict())]
        self.assertEqual(self.run_editor(), SUMMARY)
        with patch.object(editor, '_RUNTIME', self.runtime), patch.object(
                editor, '_is_hard_blocked', return_value=(True, '오래된 발행 기사')):
            with cache.review_session(self.state, lambda: None, self.logs.append):
                self.assertEqual(editor.build_message(self.s), '')
        self.assertEqual(self.client.responses.create.call_count, 2)

    def test_image_held_story_makes_zero_paid_calls_next_day_despite_history_growth(self):
        history = {}
        current_image = [b'old-image']
        def respond(**kwargs):
            prompt = kwargs['input']
            if isinstance(prompt, list):
                return answer(verdict('approved', images.IMAGE_CHECKS, current_image[0] == b'new-image'))
            if '"related_ids"' in prompt:
                return answer('{"related_ids": []}')
            if '"publish"' in prompt:
                return answer(verdict())
            return answer(SUMMARY)
        self.client.responses.create.side_effect = respond
        selector_calls = []
        def selector(s, caption, client, model):
            selector_calls.append(current_image[0])
            approved, reason = images.review_image(client, model, s, caption, current_image[0], 'image/png')
            return (object() if approved else None), [{'reason': reason, 'accepted': approved}]
        def run():
            with patch.object(editor, '_RUNTIME', self.runtime), patch.object(
                    editor, '_is_hard_blocked', return_value=(False, '')):
                with cache.review_session(self.state, lambda: None, self.logs.append) as store:
                    store.clock = lambda: self.now
                    return prepare_publication(self.s, editor.build_message, self.client, 'gpt-6-luna',
                                               selector, lambda c: editor.review_article_event(self.s, c, history))
        self.assertEqual(run()['status'], 'held')
        calls = self.client.responses.create.call_count
        self.state = json.loads(json.dumps(self.state))
        self.state['ai_review']['entries'] = {}  # Heavy event-request churn.
        self.now += 25 * 3600
        history['unrelated'] = {'title': 'Other bank launches a different product', 'url': 'https://old.example/2'}
        self.assertEqual(run()['status'], 'held')
        self.assertEqual(self.client.responses.create.call_count, calls)
        self.assertEqual(len(selector_calls), 2)  # Still checks for replacement bytes.
        current_image[0] = b'new-image'
        self.assertEqual(run()['status'], 'ready')
        self.assertGreater(self.client.responses.create.call_count, calls)
        self.assertEqual(self.state['posted'], {})  # Preparing never sends or records a post.

    def test_replacement_image_still_requires_current_duplicate_check(self):
        s = dict(self.s, _review_source_sha256='source')
        selector = Mock(side_effect=[(None, []), (object(), [])])
        event = Mock(side_effect=[{'status': 'new'}, {'status': 'duplicate', 'reason': '새 게시 이력'}])
        with cache.review_session(self.state, lambda: None, self.logs.append):
            first = prepare_publication(s, lambda s: '뉴스 본문', None, 'gpt-6-luna', selector, event)
            second = prepare_publication(s, lambda s: '뉴스 본문', None, 'gpt-6-luna', selector, event)
        self.assertEqual((first['status'], second['status']), ('held', 'held'))
        self.assertEqual(event.call_count, 2)
        self.assertIn('duplicate', second['reason'])

    def test_image_download_failure_is_retried_and_can_recover(self):
        selector = Mock(side_effect=[(None, [{'reason': 'download: TimeoutError'}]), (object(), [])])
        with cache.review_session(self.state, lambda: None, self.logs.append):
            for status in ('held', 'ready'):
                result = prepare_publication(self.s, lambda s: '뉴스 본문', None, 'gpt-6-luna', selector,
                                             lambda c: {'status': 'new'})
                self.assertEqual(result['status'], status)
        self.assertEqual(selector.call_count, 2)

    def test_event_rejection_survives_unrelated_history_but_evidence_change_rechecks(self):
        history = {'a': {'title': 'Ripple receives approval', 'url': 'https://old.example/a', 'summary': 'Old evidence'}}
        target = events.history_records(history)[0]['id']
        calls = []
        def model(prompt):
            calls.append(prompt)
            if '"related_ids"' in prompt:
                return json.dumps({'related_ids': matching_reference(prompt, history['a']['title'])})
            return json.dumps({'decision': 'duplicate', 'reason': '동일한 승인 사건', 'matched_id': target})
        s = dict(self.s, _review_source_sha256='body-one')
        def run():
            with cache.review_session(self.state, lambda: None, self.logs.append) as store:
                store.clock = lambda: self.now
                return events.review_event(s, SUMMARY, history, model, model='gpt-6-luna')
        self.assertEqual(run()['status'], 'duplicate')
        before = len(calls)
        self.state = json.loads(json.dumps(self.state))
        self.now += 86400
        history['b'] = {'title': 'Another company', 'url': 'https://old.example/b'}
        self.assertEqual(run()['status'], 'duplicate')
        self.assertEqual(len(calls), before)
        history['a']['summary'] = 'Corrected supporting evidence'
        run()
        self.assertGreater(len(calls), before)
        before = len(calls)
        s['_review_source_sha256'] = 'body-two'
        run()
        self.assertGreater(len(calls), before)

    def test_deleted_event_evidence_and_new_model_do_not_keep_rejection(self):
        history = {'a': {'title': 'Original', 'url': 'https://old.example/a'}}
        target = events.history_records(history)[0]['id']
        def model(prompt):
            if '"related_ids"' in prompt:
                return json.dumps({'related_ids': matching_reference(prompt, history['a']['title'])})
            return json.dumps({'decision': 'supplement', 'matched_id': target, 'reason': '보충 보도'})
        with cache.review_session(self.state, lambda: None, self.logs.append):
            events.review_event(self.s, SUMMARY, history, model, model='gpt-6-luna')
            fresh = Mock(return_value='{"related_ids": []}')
            self.assertEqual(events.review_event(self.s, SUMMARY, {}, fresh, model='gpt-6-luna')['status'], 'new')
            fresh.assert_not_called()  # Remaining history was already compared.
            self.assertEqual(events.review_event(self.s, SUMMARY, history, fresh, model='gpt-5.4')['status'], 'new')
            self.assertEqual(fresh.call_count, 1)

    def test_uncertain_event_is_not_pinned_when_history_changes(self):
        history = {'a': {'title': 'Original', 'url': 'https://old.example/a'}}
        target = events.history_records(history)[0]['id']
        def model(prompt):
            if '"related_ids"' in prompt:
                return json.dumps({'related_ids': matching_reference(prompt, history['a']['title'])})
            return json.dumps({'decision': 'uncertain', 'matched_id': target, 'reason': '근거 부족'})
        with cache.review_session(self.state, lambda: None, self.logs.append):
            self.assertEqual(events.review_event(self.s, SUMMARY, history, model, model='gpt-6-luna')['status'], 'hold')
            history['a']['summary'] = 'New evidence'
            fresh = Mock(return_value='{"related_ids": []}')
            self.assertEqual(events.review_event(self.s, SUMMARY, history, fresh, model='gpt-6-luna')['status'], 'new')
            fresh.assert_called_once()

    def test_valid_old_negative_request_is_promoted_without_paid_call(self):
        self.client.responses.create.return_value = answer('SKIP')
        with cache.review_session(self.state, lambda: None, self.logs.append) as store:
            store.clock = lambda: self.now
            cache.request_text(self.client, 'gpt-6-luna', 'same')
        self.state['ai_review']['content_results_v1'] = {}
        with cache.review_session(self.state, lambda: None, self.logs.append) as store:
            store.clock = lambda: self.now
            cache.request_text(self.client, 'gpt-6-luna', 'same')
        self.state['ai_review']['entries'] = {}
        self.now += 8 * 3600
        with cache.review_session(self.state, lambda: None, self.logs.append) as store:
            store.clock = lambda: self.now
            cache.request_text(self.client, 'gpt-6-luna', 'same')
        self.assertEqual(self.client.responses.create.call_count, 1)

    def test_content_records_expire_are_bounded_and_do_not_store_image_bytes(self):
        with patch.object(cache, 'MAX_CONTENT_RESULTS', 2):
            with cache.review_session(self.state, lambda: None, self.logs.append) as store:
                store.clock = lambda: self.now
                for i in range(3):
                    cache.content_result('image_held', {'image': 'SECRET-BASE64-' + str(i)}, {'reason': 'held'})
                    self.now += 1
                self.assertEqual(len(store.data['content_results_v1']), 2)
                self.assertNotIn('SECRET-BASE64', json.dumps(self.state))
                self.now += cache.CONTENT_TTL + 1
                self.assertIsNone(cache.content_result('image_held', {'image': 'SECRET-BASE64-2'}))


if __name__ == '__main__':
    unittest.main()
