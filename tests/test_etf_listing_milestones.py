import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import doorinews_editor as editor
import news_review_cache as cache
from news_coverage import coverage_intake_reason
from news_institutional_actions import etf_listing_scope, ETF_LISTING_ENABLED_AT
from news_manual_nov28 import EVENTS
from news_publication import prepare_publication
from tests.test_team_full_pipeline import verdict


TEAM_URL, TEAM_TITLE, _ = EVENTS[-1]


def candidate(title, **fields):
    published = max(datetime.now(timezone.utc), ETF_LISTING_ENABLED_AT + timedelta(seconds=1))
    return dict({'title': title, 'url': 'https://example.com/etf-event', 'pub': published.isoformat()}, **fields)


class ETFListingMilestones(unittest.TestCase):
    def test_bilingual_schedules_and_actual_trading_reach_the_normal_intake(self):
        titles = (
            TEAM_TITLE,
            'Malaysia’s First Shariah Bitcoin ETF Lists Dec. 2 at a 0.84% All-In Cost',
            '말레이시아 첫 비트코인 현물 ETF, 12월 2일 부르사 증권거래소 상장',
            'Spot Ether ETF starts trading on Example Exchange',
        )
        for title in titles:
            with self.subTest(title=title):
                story = candidate(title)
                self.assertTrue(etf_listing_scope(story))
                self.assertTrue(editor.matches_keywords(story, [], [], []))
                self.assertEqual(editor.build_story_signature(story), '')
        for title in ('Bitcoin ETF inflows hit new record', 'Bitcoin futures ETF to list next week',
                      'Unconfirmed rumor: XRP ETF to list next month', 'Leveraged Ether ETF set for listing'):
            with self.subTest(title=title):
                self.assertFalse(etf_listing_scope(candidate(title)))

    def test_listing_caption_retains_date_stage_and_tags_and_checks_duplicates(self):
        source = ('Halogen Capital says Malaysia’s first spot Bitcoin ETF is scheduled to list on Bursa '
                  'Malaysia on December 2. Listing approval and prospectus registration are separate steps.')
        caption = ('할로겐캐피털의 말레이시아 첫 현물 비트코인 ETF가 12월 2일 '
                   '부르사 말레이시아 증권거래소에 상장될 예정임')
        for decision in ('update', 'duplicate'):
            selector = Mock(return_value=({'url': 'https://example.com/photo.jpg'}, []))
            review = Mock(return_value={'status': decision})
            with patch.object(editor, '_RUNTIME', {}), patch.object(editor, '_call_openai', side_effect=[caption, verdict()]) as model:
                result = prepare_publication(candidate(TEAM_TITLE, article_text=source), editor.build_message,
                                             None, 'mock', selector=selector, event_review=review)
            for call in model.call_args_list:
                self.assertIn('상장 소식의 핵심이 아닌 수수료 수치·비교는 생략', call.args[0])
            if decision == 'duplicate':
                self.assertEqual(result['status'], 'held')
                selector.assert_not_called()
            else:
                self.assertEqual(result['status'], 'ready', result)
                for text in ('#할로겐캐피털', '#비트코인', '#ETF', '#부르사말레이시아', '12월 2일', '상장될 예정'):
                    self.assertIn(text, result['caption'])
                selector.assert_called_once()

    def test_team_link_and_old_queue_are_blocked_before_paid_review(self):
        with patch.object(editor, '_call_openai') as model:
            self.assertEqual(editor.build_message(candidate(TEAM_TITLE, url=TEAM_URL)), '')
        model.assert_not_called()
        self.assertIn('과거 대기열', coverage_intake_reason(candidate(
            TEAM_TITLE, pub=(ETF_LISTING_ENABLED_AT - timedelta(minutes=1)).isoformat())))

    def test_listing_fee_refusal_can_be_reviewed_once_without_flushing_other_results(self):
        manifest = json.loads(Path(cache.__file__).with_name('news_cache_compatibility.json').read_text('utf8'))
        old = manifest['etf_listing_only_previous_identities'][0]
        with cache.review_session({}, lambda: None, logger=lambda _: None) as store:
            cases = (
                ('source_summary', TEAM_TITLE, {'summary': '', 'reason': '수수료 총보수 설명이 부정확함'}, True),
                ('source_summary', TEAM_TITLE, {'summary': '', 'reason': '원문 본문이 불충분함'}, False),
                ('source_summary', TEAM_TITLE, {'summary': '검증된 일정', 'reason': '수수료 생략'}, False),
                ('source_summary', 'Another unrelated article', {'summary': '', 'reason': '수수료 오역'}, False),
                ('event_rejected', TEAM_TITLE, {'reason': '같은 상장 일정이 이미 게시됨'}, False),
            )
            for index, (kind, title, result, retry) in enumerate(cases):
                with self.subTest(kind=kind, result=result):
                    scope = {'title': title, 'test_case': index}
                    key = cache.fingerprint([cache.VERSION, old, kind, scope])
                    store.data.setdefault('content_results_v1', {})[key] = {
                        'result': result, 'expires': store.clock() + 1000}
                    self.assertEqual(cache.content_result(kind, scope), None if retry else result)
