"""No paid model calls: verify eligible types still traverse publication gates."""
import contextlib
import io
import json
from datetime import timedelta
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import doorinews_editor as e
import news_review_cache as cache
from news_coverage import coverage_intake_reason
from news_institutional_actions import ENABLED_AT, scope
from news_manual_nov27 import EVENTS as ALL_EVENTS
EVENTS = ALL_EVENTS[-5:]
from news_publication import prepare_publication
from tests.test_team_full_pipeline import verdict


def story(title, **kwargs):
    return dict(title=title, url='https://example.com/future-announcement',
                pub=(ENABLED_AT+timedelta(hours=1)).isoformat(), **kwargs)


class InstitutionalActions(unittest.TestCase):
    def setUp(self):
        runtime = patch.object(e, '_RUNTIME', {})
        runtime.start(); self.addCleanup(runtime.stop)

    def test_all_five_and_other_publishers_reach_review(self):
        titles = [row[1] for row in EVENTS[:5]] + [
            'JPCrypto-ISAC partners with SEAL to enhance cyberattack response',
            'Japan’s JPCrypto-ISAC partners with SEAL to strengthen crypto hack detection, incident response',
            'Government requires crypto test for retail investors to buy digital assets',
            'Crypto market maker Example Firm winds down operations',
            '암호화폐 보안 단체, 위협정보 공유·대응 협약 체결',
        ]
        for title in titles:
            with self.subTest(title=title), contextlib.redirect_stdout(io.StringIO()):
                s = story(title)
                self.assertTrue(scope(s))
                self.assertFalse(e._is_hard_blocked(s)[0])
                self.assertTrue(e.matches_keywords(s, [], [], []))
                self.assertIn('추가 허용 유형:', e._summary_prompt(title, 'source'))
                with patch.object(e, '_call_openai', return_value=verdict()) as api:
                    e._validate_summary_against_source(title, 'source', '요약')
                self.assertIn('추가 허용 유형:', api.call_args.args[0])

    def test_newly_allowed_backlog_and_manual_urls_never_replay(self):
        for url, title, _ in EVENTS[:5]:
            s = story(title); s['url'] = url
            with patch.object(e, '_call_openai') as api:
                self.assertEqual(e.build_message(s), '')
                api.assert_not_called()
        for _, title, _ in EVENTS[:4]:
            s = story(title); s['pub'] = (ENABLED_AT-timedelta(hours=1)).isoformat()
            self.assertIn('과거 대기열', coverage_intake_reason(s))

    def test_new_actions_are_rendered_with_entities_and_attribution(self):
        cases = (
            (EVENTS[2][1], 'Sources report Auros is winding down. Its closure date and reason are undisclosed.',
             '오로스가 사업 운영을 단계적으로 종료하고 있다는 소식통 보도가 나옴', '#오로스'),
            (EVENTS[3][1], 'JPCrypto-ISAC signed an MOU with SEAL for threat intelligence sharing and incident response.',
             '일본 JPCrypto-ISAC가 SEAL과 위협정보 공유 및 해킹 대응 협약을 체결함', '#SEAL'),
            (EVENTS[4][1], 'Malaysia approved the spot Bitcoin ETF managed by Halogen Capital under Shariah principles.',
             '말레이시아가 할로겐캐피털의 샤리아 원칙을 준수하는 현물 비트코인 ETF를 승인함', '#할로겐캐피털'),
            (EVENTS[0][1], 'An older study by the Homeland Security Studies and Analysis Institute assessed Ripple-style payment systems. It is not a current government adoption policy.',
             '미국 국토안보부 관련 연구기관이 과거 보고서에서 리플과 같은 결제 수단을 통한 달러 접근 가능성을 평가한 내용이 재조명됨', '#리플'),
        )
        for title, body, summary, tag in cases:
            with self.subTest(title=title), patch.object(e, '_call_openai', side_effect=[summary, verdict()]):
                event = Mock(return_value={'status':'new'})
                image = Mock(return_value=({'url':'https://example.com/relevant.jpg'}, []))
                result = prepare_publication(story(title, article_text=body), e.build_message,
                                             None, 'mock', selector=image, event_review=event)
            self.assertEqual(result['status'], 'ready', result)
            self.assertIn(tag, result['caption'])
            event.assert_called_once(); image.assert_called_once()

    def test_source_rejection_duplicate_or_missing_image_still_holds(self):
        for gate in ('source', 'duplicate', 'image'):
            title = EVENTS[0][1]
            event = Mock(return_value={'status':'duplicate' if gate == 'duplicate' else 'new'})
            image = Mock(return_value=(None, []) if gate == 'image' else ({'url':'relevant'}, []))
            responses = ['국토안보부가 XRP를 채택함', verdict(faithful=False), 'SKIP: 원문 근거 없음'] if gate == 'source' else ['과거 연구기관의 리플 결제 평가가 재조명됨', verdict()]
            with patch.object(e, '_call_openai', side_effect=responses):
                result = prepare_publication(story(title, article_text='Old research, not government adoption.'),
                    e.build_message, None, 'mock', selector=image, event_review=event)
            self.assertEqual(result['status'], 'held', (gate, result))
            if gate == 'source': event.assert_not_called(); image.assert_not_called()
            if gate == 'duplicate': image.assert_not_called()

    def test_adverse_coin_rumors_and_unrelated_articles_remain_excluded(self):
        for title in ('XRP Ledger vulnerability patched after unauthorized mint risk',
                      'Bitcoin price prediction: $200000 target',
                      'Sui price jumps as whales buy'):
            self.assertFalse(scope(story(title)))
            self.assertTrue(e._is_hard_blocked(story(title))[0], title)
        for title in ('Rumor: government will adopt XRP', 'School requires exam for students', 'Market maker updates trading volume',
                      'Japan crypto exchange hacked yesterday'):
            self.assertFalse(scope(story(title)))

    def test_historical_and_policy_guidance_keeps_qualifiers(self):
        p = e._summary_prompt(EVENTS[0][1], 'source')
        self.assertIn('작성 연도는 확인되는 경우만', p)
        self.assertIn('미국 정부의 XRP 채택·구매·정책 결정 또는 보장이 아니다', p)
        self.assertEqual(e.build_story_signature(story(EVENTS[0][1])), '')
        self.assertEqual(e.build_story_signature(story(EVENTS[1][1])), '')

    def test_cache_reconsiders_only_affected_category_refusals(self):
        manifest = json.loads(Path(cache.__file__).with_name('news_cache_compatibility.json').read_text('utf8'))
        old = manifest['institutional_actions_only_previous_identities'][0]
        with cache.review_session({}, lambda:None, logger=lambda _:None) as store:
            expiry = store.clock()+1000
            for kind, title, reason, redo in (
                ('source_summary', EVENTS[2][1], '지정 코인 핵심맥락 없음', True),
                ('source_summary', EVENTS[2][1], '원문 수치와 불일치', False),
                ('event_rejected', EVENTS[0][1], '동일 문서 재보도', False),
                ('image_held', EVENTS[3][1], '기본 로고 이미지', False),
                ('source_summary', 'Unrelated Bitcoin story', '요약 편집 단계의 명시적 제외 판정', False)):
                key_scope = {'title':title, 'test_reason':reason}
                key = cache.fingerprint([cache.VERSION, old, kind, key_scope])
                store.data.setdefault('content_results_v1', {})[key] = {'result':{'reason':reason}, 'expires':expiry}
                self.assertEqual(cache.content_result(kind, key_scope) is None, redo, reason)
            self.assertTrue(all(x['expires']==expiry for x in store.data['content_results_v1'].values()))
