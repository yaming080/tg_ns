"""Incident backlog suppression; no paid API or Telegram calls."""
import ast
import copy
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from news_resume import resume_exclusion_reason, select_resume_candidates


class ResumeTests(TestCase):
    def test_fixed_boundary_and_timezone(self):
        for value in ('2026-10-05T05:38:42Z', 'Mon, 05 Oct 2026 14:38:42 +0900'):
            self.assertTrue(resume_exclusion_reason({'pub': value}))
        for value in ('2026-10-05T05:38:43Z', 'Mon, 05 Oct 2026 14:38:43 +0900',
                      '2026-10-06T05:00:00Z'):
            self.assertFalse(resume_exclusion_reason({'pub': value}))

    def test_unknown_date_never_releases_backlog(self):
        for value in ('', None, 123, 'invalid', '2026-10-05T14:00:00'):
            self.assertTrue(resume_exclusion_reason({'pub': value}))

    def test_latest_first_without_mutating_input(self):
        stories = [{'title': title, 'pub': pub} for title, pub in (
            ('old', '2026-10-04T06:00:00Z'), ('new', '2026-10-05T06:00:00Z'),
            ('latest', '2026-10-05T06:30:00Z'))]
        original = copy.deepcopy(stories)
        result = select_resume_candidates(stories, Mock())
        self.assertEqual([s['title'] for s in result], ['latest', 'new'])
        self.assertEqual(stories, original)

    def run_main(self, mutate=False):
        # Execute the actual final main() with I/O replaced; no module startup.
        source = Path(__file__).resolve().parents[1] / 'doorinews_bot.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        main = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main'][-1]
        old = {'title': 'old', 'url': 'old-url', 'pub': '2026-10-04T06:00:00Z'}
        fresh = {'title': 'fresh', 'url': 'fresh-url', 'pub': '2026-10-05T06:00:00Z'}
        state = {'posted': {'existing': {'title': 'existing', 'url': 'existing-url'}}}
        original_posted = copy.deepcopy(state['posted'])
        def prepare(story, *args, **kwargs):
            if mutate:
                story['pub'] = old['pub']
            return {'status': 'ready', 'image': b'photo', 'caption': 'caption'}
        ns = {name: Mock() for name in (
            'log', 'save_state', 'http_get', 'build_message', 'review_article_event',
            'update_posted', 'remember_context')}
        ns.update(STATE_FILE='unused', FEEDS=[], PORTFOLIO_COINS=[], ECON_KEYWORDS=[],
                  KOREAN_KEYWORDS=[], INITIAL_RUN=False, POST_ENABLED=True,
                  TELEGRAM_BOT_TOKEN='unused', TELEGRAM_CHANNEL_ID='unused',
                  OPENAI_MODEL='unused', openai_client=None, time=Mock(),
                  load_state=Mock(return_value=state), prune_posted_older_than=lambda p, **kw: p,
                  collect_new_sources=Mock(return_value=[old, fresh]),
                  matches_keywords=Mock(return_value=True), normalize_for_duplicate=lambda s: s,
                  build_story_signature=Mock(return_value=''), build_canonical_topic_key=Mock(return_value=''),
                  is_canonical_duplicate=Mock(return_value=False), is_duplicate=Mock(return_value=False),
                  is_semantically_duplicate=Mock(return_value=False),
                  prepare_publication=Mock(side_effect=prepare), send_reviewed_photo=Mock(return_value=True))
        exec(compile(ast.Module(body=[main], type_ignores=[]), str(source), 'exec'), ns)
        with patch('news_review_cache.record_publication'):
            ns['main']()
        self.assertEqual(ns['prepare_publication'].call_count, 1)
        self.assertEqual(ns['prepare_publication'].call_args.args[0]['title'], 'fresh')
        self.assertEqual(ns['matches_keywords'].call_count, 1)
        self.assertEqual(state['posted'], original_posted)
        return ns

    def test_old_stories_never_reach_paid_review_and_new_can_send(self):
        ns = self.run_main()
        ns['send_reviewed_photo'].assert_called_once()

    def test_send_guard_blocks_changed_publication_date(self):
        ns = self.run_main(mutate=True)
        ns['send_reviewed_photo'].assert_not_called()
