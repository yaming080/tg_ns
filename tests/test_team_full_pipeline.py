"""Team regressions across intake, full-source, editorial, dedup and image gates.

Model verdicts are controlled: these tests prove gate wiring, not historical
article truth or real-model acceptance. No network or Telegram calls are made.
"""
import ast
import contextlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import doorinews_editor as e
import news_review_cache as cache
from news_event_review import MANUAL_EVENTS
from news_publication import prepare_publication


def candidate(title, **kw):
    return dict(title=title, url='https://example.com/new-event',
                pub=datetime.now(timezone.utc).isoformat(), **kw)


def verdict(**changes):
    checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                           'new_substantive_fact', 'source_sufficient', 'understandable'), True)
    checks.update(changes)
    return json.dumps(dict(publish=all(checks.values()), reason='원문과 핵심 조건 대조', checks=checks))


class AllTeamCases(unittest.TestCase):
    def setUp(self):
        runtime = patch.object(e, '_RUNTIME', {})
        runtime.start(); self.addCleanup(runtime.stop)

    def test_all_previous_team_examples_at_intake_and_enriched_source(self):
        count = 0
        with patch.object(e, 'manual_post_reason', return_value=''):
            for url, title, note in MANUAL_EVENTS:
                if any(host in url for host in ('x.com/', 'coingape.com/')):
                    continue
                count += 1
                s = candidate(title)
                with self.subTest(title=title), contextlib.redirect_stdout(io.StringIO()):
                    blocked, reason = e._is_hard_blocked(s)
                    if 'Simpsons' in title or title.startswith('Rumor: Nvidia'):
                        self.assertTrue(blocked); continue
                    self.assertFalse(blocked, reason)
                    self.assertTrue(e.matches_keywords(s, [], [], []))
                    self.assertFalse(e._is_hard_blocked(dict(s, article_text=note))[0])
                    self.assertIn('이번 기사에 적용하는 편집 허용 유형:', e._summary_prompt(title, note))
                    with patch.object(e, '_call_openai', return_value=verdict()) as api:
                        e._validate_summary_against_source(title, note, '발표 내용')
                    self.assertIn('이번 기사에 적용하는 편집 허용 유형:', api.call_args.args[0])
        self.assertGreaterEqual(count, 179)

    def test_statements_reach_publication_gates_with_body_tags(self):
        cases = (
            ('Bitcoin As Important as Ever if Inflation Rises, Coinbase CEO Says',
             'Coinbase CEO Brian Armstrong said Bitcoin remains important if inflation rises.',
             '코인베이스 CEO 브라이언암스트롱이 인플레이션이 높아지면 비트코인의 중요성이 유지된다고 밝힘', '#브라이언암스트롱'),
            ('Bitcoin Sentiment Can Turn Quickly, British Strategy CEO Says',
             'Smarter Web CEO Andrew Webley said Bitcoin sentiment can turn quickly.',
             '스마터웹 CEO가 비트코인의 투자 심리가 빠르게 바뀔 수 있다고 밝힘', '#스마터웹'),
            ('Galaxy walks back Bitcoin bottom call',
             'Galaxy Digital withdrew its previous Bitcoin bottom call. It is a conditional view, not a fact about future prices.',
             '갤럭시디지털이 비트코인 약세장 종료라는 기존 분석을 철회함', '#갤럭시디지털'),
        )
        for title, source, summary, tag in cases:
            s = candidate(title, article_text=source)
            selector = Mock(return_value=({'url':'https://example.com/relevant.jpg'}, []))
            event = Mock(return_value={'status':'new'})
            with self.subTest(title=title), patch.object(e, '_call_openai', side_effect=[summary, verdict()]):
                result = prepare_publication(s, e.build_message, None, 'mock', selector=selector, event_review=event)
            self.assertEqual(result['status'], 'ready', result)
            self.assertIn(tag, result['caption'])
            selector.assert_called_once(); event.assert_called_once()

    def test_allowance_never_bypasses_fact_event_or_image_verdict(self):
        title = 'Bitcoin Sentiment Can Turn Quickly, British Strategy CEO Says'
        for failed_gate in ('facts', 'event', 'image'):
            s = candidate(title, article_text='Smarter Web CEO expressed a conditional view. An earlier purchase is historical background.')
            selector = Mock(return_value=(None, []) if failed_gate == 'image' else ({'url':'relevant'}, []))
            event = Mock(return_value={'status':'duplicate' if failed_gate == 'event' else 'new', 'reason':'same announcement'})
            answer = verdict(faithful=False) if failed_gate == 'facts' else verdict()
            with patch.object(e, '_call_openai', side_effect=['스마터웹 CEO가 비트코인 심리 전환 가능성을 언급함', answer, 'SKIP']):
                result = prepare_publication(s, e.build_message, None, 'mock', selector=selector, event_review=event)
            self.assertEqual(result['status'], 'held')
            if failed_gate == 'facts': event.assert_not_called(); selector.assert_not_called()
            if failed_gate == 'event': selector.assert_not_called()

    def test_already_manual_posted_links_are_not_replayed(self):
        from news_manual_nov27 import EVENTS
        for url, title, _ in EVENTS[-3:]:
            s = candidate(title); s['url'] = url
            with patch.object(e, '_call_openai') as api:
                self.assertEqual(e.build_message(s), '')
                api.assert_not_called()

    def test_skip_reason_is_recorded_and_never_rendered_as_caption(self):
        s = candidate('Bitcoin Sentiment Can Turn Quickly, British Strategy CEO Says',
                      article_text='Smarter Web quote with insufficient date evidence.')
        with patch.object(e, '_call_openai', return_value='SKIP: 발언 날짜와 주체를 원문에서 확인할 수 없음') as api:
            self.assertEqual(e.build_message(s), '')
        self.assertIn('발언 날짜와 주체', s['_preparation_reason'])
        api.assert_called_once()

    def test_named_statement_updates_require_context_but_same_url_stays_duplicate(self):
        from news_event_review import review_event
        s = candidate('Galaxy walks back Bitcoin bottom call')
        self.assertEqual(e.build_story_signature(s), '')
        self.assertFalse(e.is_semantically_duplicate(s, ['asset_btc | entity_galaxy'], ['Galaxy Bitcoin bottom call']))
        history = {'old':dict(title=s['title'],url=s['url'],summary='같은 철회 발표')}
        model = Mock()
        self.assertEqual(review_event(s,'갤럭시디지털이 기존 분석을 철회함',history,model)['status'],'duplicate')
        model.assert_not_called()

    def test_cache_preserves_unchanged_fact_and_image_rejections(self):
        manifest = json.loads(Path(cache.__file__).with_name('news_cache_compatibility.json').read_text('utf8'))
        old = manifest['team_review_only_previous_identities'][0]
        with cache.review_session({}, lambda:None, logger=lambda _:None) as store:
            expiry = store.clock()+1000
            for kind, title, reason, redo in (
                ('source_summary', 'Bitcoin Sentiment Can Turn Quickly, British Strategy CEO Says', '구체사건 없음', True),
                ('source_summary', 'TRON Network Integrates with Backpack Wallet', '원문의 수치와 불일치', False),
                ('source_summary', 'TRON Network Integrates with Backpack Wallet', '요약 편집 단계의 명시적 제외 판정', True),
                ('source_summary', 'Unrelated Bitcoin report', '요약 편집 단계의 명시적 제외 판정', False),
                ('image_held', 'Bitcoin Sentiment Can Turn Quickly, British Strategy CEO Says', '이미지 없음', False)):
                scope = {'title':title,'reason_key':reason}
                key = cache.fingerprint([cache.VERSION,old,kind,scope])
                store.data.setdefault('content_results_v1',{})[key] = {'result':{'summary':'','reason':reason},'expires':expiry}
                result = cache.content_result(kind,scope)
                self.assertEqual(result is None, redo, (kind,title,reason))
            self.assertTrue(all(x['expires']==expiry for x in store.data['content_results_v1'].values()))


class PublicationLatency(unittest.TestCase):
    def test_ready_story_is_sent_before_later_paid_comparisons(self):
        path = Path(e.__file__).with_name('doorinews_bot.py')
        main = [n for n in ast.parse(path.read_text('utf8')).body if isinstance(n,ast.FunctionDef) and n.name=='main'][-1]
        events=[]; state={'posted':{}}
        stories=[dict(title=t,url='https://example.com/'+t,pub=datetime.now(timezone.utc).isoformat()) for t in ('first','second')]
        def compare(s,*_): events.append('compare '+s['title']);return False
        def prepare(s,*_,**kw): events.append('prepare '+s['title']);return dict(status='ready',caption=s['title'],image='image',attempts=[])
        def send(*args): events.append('send '+args[3]);return True
        ns=dict(log=lambda _:None,STATE_FILE='',load_state=lambda _:state,save_state=lambda *_:None,
                prune_posted_older_than=lambda p,days:p,FEEDS=[],collect_new_sources=lambda *_:stories,http_get=None,
                PORTFOLIO_COINS=[],ECON_KEYWORDS=[],KOREAN_KEYWORDS=[],matches_keywords=lambda *_:True,
                normalize_for_duplicate=lambda t:t,build_story_signature=lambda _: '',build_canonical_topic_key=lambda _: '',
                is_canonical_duplicate=lambda *_:False,is_duplicate=lambda *_:False,is_semantically_duplicate=compare,
                INITIAL_RUN=False,POST_ENABLED=True,prepare_publication=prepare,build_message=None,openai_client=None,
                OPENAI_MODEL='mock',TELEGRAM_BOT_TOKEN='mock',TELEGRAM_CHANNEL_ID='mock',send_reviewed_photo=send,
                update_posted=lambda *_:None,remember_context=lambda *_:None,time=SimpleNamespace(sleep=lambda _:None))
        exec(compile(ast.Module(body=[main],type_ignores=[]),str(path),'exec'),ns)
        with patch('news_resume.select_resume_candidates',return_value=stories): ns['main']()
        self.assertEqual(events,['compare first','prepare first','send first','compare second','prepare second','send second'])


if __name__ == '__main__': unittest.main()
