import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, Mock

import doorinews_editor as editor
import news_nov27_scope as policy
import news_manual_nov27 as manual
import news_review_cache as cache
import news_event_review as events
from news_coverage import coverage_intake_reason
from news_quality import manual_post_reason
from news_source_cleanup import extract_article_text


def story(title, url='https://example.com/new'):
    return dict(title=title, url=url, pub=max(datetime.now(timezone.utc),
                policy.ENABLED_AT + timedelta(seconds=1)).isoformat())


class Nov27Feedback(unittest.TestCase):
    def test_feedback_candidates_pass_intake_without_coin_name_requirement(self):
        for i in (5, 6, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23):
            candidate = story(manual.EVENTS[i][1])
            with self.subTest(title=candidate['title']):
                self.assertTrue(policy.scope(candidate))
                self.assertFalse(editor._is_hard_blocked(candidate)[0])
                self.assertTrue(editor.matches_keywords(candidate, [], [], []))

    def test_source_background_price_does_not_discard_new_institutional_filing(self):
        candidate = story('Arkadios discloses XRP ETF stake in Q3 filing')
        candidate['article_text'] = 'Arkadios reported its quarter-end position. Background: shares rose 5% as stock prices gained.'
        with patch.object(editor, '_call_openai', return_value='SKIP') as api:
            self.assertEqual(editor._rewrite_summary(candidate), '')
            self.assertTrue(api.called)
        self.assertFalse(policy.scope(story('XRP ETF daily inflows rise as stock prices gain')))

    def test_old_and_undated_new_candidates_stay_out(self):
        for title in ('Switzerland approves 57 jurisdictions for crypto tax data sharing',
                      '한국은행 기준금리 0.25%p 인상',
                      '백악관 쿠팡 과징금에 약속 위반 비판'):
            for date in ('', 'bad', policy.ENABLED_AT.isoformat(), '2026-11-26T15:53:00'):
                candidate = dict(story(title), pub=date)
                self.assertTrue(coverage_intake_reason(candidate), (title, date))

    def test_known_channel_posts_never_pay_or_send_again(self):
        self.assertEqual(len(manual.EVENTS), 26)
        with patch.object(editor, '_call_openai') as api:
            for url, title, _ in manual.EVENTS:
                candidate = story(title, url)
                self.assertTrue(manual_post_reason(candidate))
                self.assertEqual(editor.build_message(candidate), '')
        api.assert_not_called()
        keys = {events.url_key(row['url']) for row in events.history_records({})}
        self.assertTrue(all(events.url_key(url) in keys for url in manual.URLS))

    def test_bank_plan_and_actual_opening_get_full_event_review(self):
        candidate = story('Discount Bank opens Bitcoin trading inside its own app today')
        old = 'action_integrate | asset_btc | entity_israeldiscountbank'
        self.assertEqual(editor.build_story_signature(candidate), '')
        self.assertFalse(editor.is_canonical_duplicate(editor.build_canonical_topic_key(candidate), {old}))
        self.assertFalse(editor.is_semantically_duplicate(candidate, [old],
                         ['Discount Bank opens Bitcoin trading inside its own app on November 26']))
        # No model verdict/evidence means no publication, despite intake deferral.
        self.assertEqual(events.review_event(candidate, '은행 앱 실제 거래 개시 보도', {}, lambda _: '')['status'], 'hold')
        duplicate = dict(candidate, url=manual.URLS[22])
        model = Mock()
        self.assertEqual(events.review_event(duplicate, '동일 서비스 개시', {}, model)['status'], 'duplicate')
        model.assert_not_called()

    def test_filing_context_requires_source_review_not_quantity_signature(self):
        candidate = story('Morgan Stanley lifts Bitcoin ETF holdings in Q3 filing')
        self.assertEqual(editor.build_story_signature(candidate), '')
        prompt = editor._summary_prompt(candidate['title'], 'source')
        for term in ('보고 기간', '신규 매수액', '고유자금', '같은 분기', '원문'):
            self.assertIn(term, prompt)

    def test_names_and_inline_tags_are_canonical(self):
        body = editor._clean_summary('리플이 Yapı Kredi와 터키에서 수탁 제휴를 발표함')
        self.assertIn('야피크레디', body)
        self.assertNotIn('Yapı', body)
        for original in ('야프ı 크레디', '야피 크레디', 'Yapi Kredi'):
            self.assertIn('야피크레디', editor._clean_summary(original+'가 수탁을 지원함'))
        tagged, selected = editor._inject_inline_tags(body, story('Ripple and Yapi Kredi custody partnership'))
        for tag in ('#리플', '#야피크레디', '#수탁'):
            self.assertIn(tag, tagged)
        self.assertIn('#YapiKredi', editor._build_footer_tags({}, selected))

    def test_essential_conditions_survive_short_team_style(self):
        body = '디스카운트은행이 앱에서 비트코인 거래를 개시함\n\n18세 이상 증권 계좌 고객 대상이며 외부 지갑 입출금은 불가능함'
        result = editor._clean_summary(body)
        for term in ('18세', '증권 계좌', '외부 지갑', '불가능'):
            self.assertIn(term, result)
        for index, terms in ((18, ('활성화된 트럼프 계좌', '지급 완료')),
                             (23, ('5영업일', '10영업일', '의회 승인')),
                             (11, ('테스트넷', '메인넷'))):
            prompt = editor._summary_prompt(manual.EVENTS[index][1], 'source')
            for term in terms:self.assertIn(term, prompt)

    def test_exclusions_and_empty_breaking_body_remain(self):
        for title in ('Sui launches new payment service', 'XRP Ledger critical vulnerability revealed',
                      'Rumor: Nvidia buys XRP', 'Morgan Stanley Bitcoin ETF price target $200000'):
            self.assertTrue(editor._is_hard_blocked(story(title))[0], title)
        for title in ('Anonymous whale increases Bitcoin ETF holdings',
                      'Coinbase share price rises 5%', 'Russia military conflict continues'):
            self.assertFalse(policy.scope(story(title)), title)
        html = '<script type="application/ld+json">'+json.dumps({
            '@type':'NewsArticle', 'url':'https://bloomingbit.io/feed/news/test',
            'headline':'한국은행 기준금리 인상', 'articleBody':''})+'</script>'
        self.assertEqual(extract_article_text(html, 'https://bloomingbit.io/feed/news/test', '한국은행 기준금리 인상'), '')
        with patch.object(editor, '_call_openai') as api:
            self.assertEqual(editor._rewrite_summary(story('한국은행 기준금리 인상')), '')
        api.assert_not_called()

    def test_previous_cache_reused_except_affected_semantic_results(self):
        manifest = json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text('utf8'))
        old = manifest['nov27_only_previous_identities'][0]
        with cache.review_session({}, lambda: None, logger=lambda _: None) as store:
            expiry = store.clock()+1000
            for kind, title, changed in (
                ('source_summary', 'Morgan Stanley lifts Bitcoin ETF holdings', True),
                ('event_rejected', 'Discount Bank opens Bitcoin trading in app', True),
                ('source_summary', 'Unchanged rejected article', False),
                ('source_summary', 'Nubank Secures Brazil Banking License', False),
                ('image_held', 'Morgan Stanley lifts Bitcoin ETF holdings', False)):
                scope = dict(title=title, source='same')
                key = cache.fingerprint([cache.VERSION, old, kind, scope])
                store.data.setdefault('content_results_v1', {})[key] = {'result': {'reason':'excluded'}, 'expires':expiry}
                result = cache.content_result(kind, scope)
                if changed:self.assertIsNone(result)
                else:self.assertEqual(result['reason'], 'excluded')
            self.assertTrue(all(r['expires'] == expiry for r in store.data['content_results_v1'].values()))


if __name__ == '__main__':
    unittest.main()
