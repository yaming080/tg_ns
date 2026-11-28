"""Offline regressions: real-model/source acceptance is not simulated evidence."""
import contextlib
import io
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import doorinews_editor as e
import news_review_cache as cache
from news_financial_infrastructure import ENABLED_AT, scope, date_refusal, runtime_date_guidance
from news_coverage import coverage_intake_reason
from news_manual_nov28 import EVENTS as NOV28_EVENTS
from news_publication import prepare_publication
from tests.test_team_full_pipeline import verdict

EVENTS = NOV28_EVENTS[:7]  # Original overnight cases; later ETF feedback has its own tests.


def story(title, **kw):
    return dict(title=title, url='https://example.com/new-announcement',
                pub=max(datetime.now(timezone.utc), ENABLED_AT+timedelta(seconds=1)).isoformat(), **kw)


class OvernightCoverage(unittest.TestCase):
    def setUp(self):
        runtime = patch.object(e, '_RUNTIME', {})
        runtime.start(); self.addCleanup(runtime.stop)

    def test_new_types_generalize_and_reach_source_review(self):
        titles = [x[1] for x in EVENTS if 'Mastercard' not in x[1]] + [
            'Example Bank launches digital asset OTC trading for qualified investors',
            'Government announces blockchain digital identity rules effective next March',
            'Brazil’s stock exchange B3 partners with six firms to launch real-backed stablecoin',
        ]
        for title in titles:
            with self.subTest(title=title), contextlib.redirect_stdout(io.StringIO()):
                s = story(title)
                self.assertTrue(scope(s))
                self.assertFalse(e._is_hard_blocked(s)[0])
                self.assertTrue(e.matches_keywords(s, [], [], []))
                self.assertIn('11월 28일 추가 허용 유형:', e._summary_prompt(title, 'source'))
                with patch.object(e, '_call_openai', return_value=verdict()) as api:
                    e._validate_summary_against_source(title, 'source', '요약')
                self.assertIn('11월 28일 추가 허용 유형:', api.call_args.args[0])

    def test_already_posted_examples_never_call_model(self):
        for url, title, _ in EVENTS:
            with self.subTest(title=title), patch.object(e, '_call_openai') as api:
                s = story(title); s['url'] = url
                self.assertEqual(e.build_message(s), '')
                api.assert_not_called()

    def test_newly_admitted_old_articles_do_not_flood(self):
        for _, title, _ in EVENTS[:4]:
            s = story(title); s['pub'] = (ENABLED_AT-timedelta(minutes=1)).isoformat()
            self.assertIn('과거 대기열', coverage_intake_reason(s), title)

    def test_rendered_tags_attribution_and_all_publication_gates(self):
        cases = (
            (EVENTS[0][1], 'VTB Bank launched OTC digital asset trading for qualified investors.',
             '러시아 VTB은행이 적격투자자 대상 디지털자산 장외거래 서비스를 출시함', '#VTB은행'),
            (EVENTS[1][1], 'China announced blockchain digital identity rules taking effect next March.',
             '중국이 블록체인 기반 디지털신원인증 규정을 발표했으며 내년 3월 시행할 예정임', '#중국'),
            (EVENTS[2][1], 'Digital Asset Investor cites XRP accounts and forecasts a bull market.',
             '디지털에셋인베스터가 XRP 계정 증가와 AI 결제 활용을 근거로 상승장 가능성을 전망함', '#디지털에셋인베스터'),
            (EVENTS[3][1], 'In an old interview, Eric Trump praised Brad Garlinghouse. It was personal, not government policy.',
             '에릭트럼프가 과거 인터뷰에서 리플 CEO 브래드갈링하우스와 친분이 있으며 그의 사업 성과를 긍정적으로 평가한 내용이 재조명됨', '#에릭트럼프'),
        )
        for title, source, summary, tag in cases:
            image = Mock(return_value=({'url':'https://example.com/relevant.jpg'}, []))
            event = Mock(return_value={'status':'new'})
            with self.subTest(title=title), patch.object(e, '_call_openai', side_effect=[summary, verdict()]):
                result = prepare_publication(story(title, article_text=source), e.build_message,
                    None, 'mock', selector=image, event_review=event)
            self.assertEqual(result['status'], 'ready', result)
            self.assertIn(tag, result['caption'])
            event.assert_called_once(); image.assert_called_once()

    def test_factual_failure_duplicate_and_default_image_still_hold(self):
        for gate in ('facts', 'duplicate', 'image'):
            event = Mock(return_value={'status':'duplicate' if gate=='duplicate' else 'new'})
            image = Mock(return_value=(None, []) if gate=='image' else ({'url':'relevant'}, []))
            responses = ['미국 정부가 XRP 채택을 발표함', verdict(faithful=False), 'SKIP: 원문 근거 없음'] if gate=='facts' else ['에릭트럼프의 과거 리플 관련 인터뷰가 재조명됨', verdict()]
            with patch.object(e, '_call_openai', side_effect=responses):
                result = prepare_publication(story(EVENTS[3][1], article_text='An old personal interview, not a policy decision.'),
                    e.build_message, None, 'mock', selector=image, event_review=event)
            self.assertEqual(result['status'], 'held', (gate, result))
            if gate=='facts': event.assert_not_called(); image.assert_not_called()
            if gate=='duplicate': image.assert_not_called()

    def test_clock_and_historical_qualifiers(self):
        now=datetime(2026,11,28,20,0,tzinfo=timezone.utc)
        text=runtime_date_guidance(now)
        self.assertIn('UTC 2026-11-28',text); self.assertIn('한국 2026-11-29',text)
        with patch.object(e, 'runtime_date_guidance', return_value=text):
            p=e._summary_prompt(EVENTS[3][1], '2025 interview')
        self.assertIn(text,p); self.assertIn('과거 발언임을 명시',p)
        self.assertIn('미국 정부의 XRP 채택·보장·정책 결정이 아니다',p)
        p=e._summary_prompt(EVENTS[2][1], 'source')
        self.assertIn('계정 수는 고유 이용자 수가 아니다',p)
        self.assertEqual(e.build_story_signature(story(EVENTS[3][1])), '')
        self.assertEqual(e.build_story_signature(story(EVENTS[2][1])), '')

    def test_existing_nonportfolio_and_unverified_exclusions_remain(self):
        for title in ('Sui price jumps as whales buy', 'XRP Ledger vulnerability patched',
                      'Bitcoin price prediction: $200000 target'):
            self.assertTrue(e._is_hard_blocked(story(title))[0],title)
        for title in ('Rumor: Eric Trump buys XRP', 'XRP RSI signals buy', 'Bank launches credit card'):
            self.assertFalse(scope(story(title)))

    def test_only_stale_date_or_category_refusals_rechecked(self):
        manifest=json.loads(Path(cache.__file__).with_name('news_cache_compatibility.json').read_text('utf8'))
        old=manifest['overnight_only_previous_identities'][0]
        with cache.review_session({},lambda:None,logger=lambda _:None) as store:
            expiry=store.clock()+1000
            for kind,title,reason,redo in (
                ('source_summary','B3 Keeps the Ledger','기사 원문이 2026년 11월 27일 발표를 다루지만 현재 날짜보다 미래이며, 발표 사실을 확인할 수 없음',True),
                ('source_summary',EVENTS[0][1],'지정 코인 핵심맥락 없음',True),
                ('source_summary',EVENTS[0][1],'원문 수치와 불일치',False),
                ('event_rejected',EVENTS[3][1],'같은 인터뷰 재인용',False),
                ('image_held',EVENTS[0][1],'기본 로고 이미지',False),
                ('source_summary','Unrelated Bitcoin story','요약 편집 단계의 명시적 제외 판정',False)):
                key_scope={'title':title,'test_reason':reason}
                key=cache.fingerprint([cache.VERSION,old,kind,key_scope])
                store.data.setdefault('content_results_v1',{})[key]={'result':{'reason':reason},'expires':expiry}
                self.assertEqual(cache.content_result(kind,key_scope) is None,redo,reason)
                if redo:
                    cache.content_result(kind,key_scope,{'reason':'새 검토 결과'})
                    self.assertEqual(cache.content_result(kind,key_scope),{'reason':'새 검토 결과'})
                else:
                    current=cache.fingerprint([cache.VERSION,cache.editorial_identity(),kind,key_scope])
                    self.assertEqual(store.data['content_results_v1'][current]['expires'],expiry)
        self.assertFalse(date_refusal({'result':{'summary':'valid','reason':'현재 날짜보다 미래'}}))


if __name__=='__main__':
    unittest.main()
