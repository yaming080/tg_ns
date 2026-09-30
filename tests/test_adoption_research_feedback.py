"""Oct 1 feedback. All model and Telegram interactions are mocked."""
from datetime import datetime, timezone, timedelta
import json
import unittest
from unittest.mock import patch
import doorinews_editor as e
from news_quality import ADOPTION_RESEARCH_ENABLED_AT, MANUALLY_POSTED_ARTICLES
from news_event_review import history_records
import news_sources as sources


def story(title, **kw):
    return dict(title=title, pub=datetime.now(timezone.utc).isoformat(), **kw)


def verdict(**changes):
    checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                           'new_substantive_fact', 'source_sufficient', 'understandable'), True)
    checks.update(changes)
    return json.dumps(dict(publish=True, reason='source checked', checks=checks))


RESEARCH = 'Standard Chartered initiates Ethena coverage, sees ENA at $2 by 2028'
ADOPTION = 'Brazilian State Energy Giant Petrobras Taps Cardano for Tracing Fuel'
STABLE = 'Bank-backed AllUnity launches MiCA-compliant US dollar stablecoin USDAU'


class AdoptionResearchFeedback(unittest.TestCase):
    def test_added_publishers_baseline_then_only_future_articles(self):
        now = datetime.now(timezone.utc)
        for url in ('https://cryptobriefing.com/feed/', 'https://coingape.com/feed/'):
            self.assertIn(url, dict(sources.NEW_FEEDS).values())
            state = {}
            saves = []
            old = dict(title=STABLE, url=url+'old', pub=(now-timedelta(minutes=1)).isoformat())
            fresh = dict(title=STABLE+' in a new market', url=url+'fresh', pub=(now+timedelta(minutes=1)).isoformat())
            with patch.object(sources, 'NEW_FEEDS', [('publisher', url)]), patch.object(sources, 'parse_feed', return_value=[old]) as parse:
                self.assertEqual(sources.collect_new_sources(state, lambda _: 'rss', lambda s: saves.append(s.copy()), log=lambda _: None, now=now), [])
                parse.return_value = [old, fresh]
                rows = sources.collect_new_sources(state, lambda _: 'rss', lambda s: saves.append(s.copy()), log=lambda _: None, now=now+timedelta(minutes=2))
                self.assertEqual(rows, [fresh])
                self.assertEqual(len(saves), 2)
                self.assertIn(url, saves[0]['source_baselines'])

    def test_future_examples_and_different_institutions_qualify(self):
        for title in (RESEARCH, ADOPTION, STABLE,
                      'Standard Chartered Sets $2 Target for Ethena’s ENA After September Rally',
                      '"내년 말까지 8배 급등할 것"…SC, 에테나 커버리지 개시',
                      'UBS initiates Flare coverage with $1 price target by 2029',
                      'Example Bank publishes new Ethereum research report',
                      'Regulated issuer launches new dollar stablecoin',
                      'Energy company pilots Flare for carbon tracking',
                      '물류기업, 블록체인 공급망 추적 시범사업 착수',
                      'Flare launches new institutional custody integration',
                      'Ethena launches new institutional custody integration'):
            with self.subTest(title=title):
                self.assertTrue(e.matches_keywords(story(title), [], [], []))
        self.assertEqual(e.target_assets('에테나 ENA, 플레어 FLR'), {'ENA', 'FLR'})

    def test_anonymous_predictions_ads_and_chart_analysis_remain_blocked(self):
        for title in ('Analysts set ENA price target at $2',
                      'Ethena price prediction: best token to buy',
                      'Flare price analysis at resistance level',
                      RESEARCH + ' presale referral bonus',
                      'Standard Chartered: Ethena technical analysis price target',
                      'Bank-backed AllUnity stablecoin price prediction',
                      'Could Petrobras use Cardano for fuel tracking?'):
            self.assertFalse(e.matches_keywords(story(title), [], [], []), title)
        self.assertTrue(e._is_hard_blocked(story(RESEARCH, article_text='Sponsored content'))[0])

    def test_new_scope_does_not_replay_old_or_undated_queue(self):
        for title in (RESEARCH, ADOPTION):
            for pub in ('', 'invalid', ADOPTION_RESEARCH_ENABLED_AT.isoformat(),
                        (ADOPTION_RESEARCH_ENABLED_AT-timedelta(days=1)).isoformat()):
                self.assertFalse(e.matches_keywords(dict(title=title, pub=pub), [], [], []))

    def test_known_team_posts_are_duplicate_evidence_not_topic_bans(self):
        paths = [p for p in MANUALLY_POSTED_ARTICLES if any(s in p[1] for s in
                 ('bank-backed-allunity', 'brazils-petrobras', 'standard-chartered-initiates'))]
        self.assertEqual(len(paths), 3)
        for host, path in paths:
            with patch.object(e, '_call_openai') as model:
                self.assertEqual(e.build_message(story(RESEARCH, url=f'https://{host}{path}/?utm_source=rss')), '')
                model.assert_not_called()
        evidence = ' '.join(row['title'] for row in history_records({}))
        for name in ('AllUnity', 'Petrobras', 'Ethena'):
            self.assertIn(name, evidence)

    def test_full_message_retains_attributed_forecast_and_pilot_conditions(self):
        cases = (
            (RESEARCH, 'Standard Chartered initiated Ethena coverage in a new report. Based on USDe growth and ENA buybacks, the bank sets a $2 price target by 2028, a forecast rather than a guaranteed return.',
             '스탠다드차타드가 에테나 분석을 시작하며 USDe 성장과 ENA 바이백을 근거로 2028년 ENA 목표가 2달러를 제시했다고 밝힘', '#에테나', '2028년'),
            (ADOPTION, 'Petrobras is researching Cardano for tracing environmental benefits of low-carbon fuel. The project is at research stage and no commercial launch date is set.',
             '페트로브라스가 카르다노로 저탄소 연료의 환경적 혜택 이력을 기록하는 연구를 진행하며 상용 출시 일정은 미정이라고 밝힘', '#카르다노', '미정'),
            (STABLE, 'Bank-backed AllUnity launched MiCA-compliant US dollar stablecoin USDAU backed by 100% US dollar reserves.',
             '올유니티가 유럽 암호화폐 규정에 맞춘 달러 스테이블코인 USDAU를 출시했으며 달러 준비금으로 100% 뒷받침한다고 밝힘', '#올유니티', '100%'),
        )
        for title, source, summary, tag, condition in cases:
            candidate = story(title, article_text=source)
            with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[summary, verdict()]) as model:
                caption = e.build_message(candidate)
                self.assertIn(tag, caption)
                self.assertIn(condition, caption)
                self.assertTrue(caption.endswith(' '.join(e.FIXED_FOOTER_TAGS)))
                self.assertEqual(model.call_count, 2)
                self.assertTrue(all(e.ADOPTION_RESEARCH_GUIDANCE in c.args[0] for c in model.call_args_list))
            for check in ('conditions_preserved', 'faithful', 'allowed_category', 'new_substantive_fact'):
                with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[summary, verdict(**{check: False})]):
                    self.assertEqual(e.build_message(candidate), '')
        with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai') as model:
            self.assertEqual(e.build_message(story(RESEARCH)), '')
            model.assert_not_called()

    def test_drift_subject_tag_and_token_tags(self):
        title = '드리프트재단, 해킹 자금 920만 달러 동결…이더리움 잔액 미이동'
        candidate = story(title, article_text='Drift Foundation froze $9.2 million of stolen funds after the April hack.')
        summary = '드리프트 재단이 4월 해킹으로 탈취된 이용자 자산 중 920만달러를 동결했다고 밝힘'
        with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai', side_effect=[summary, verdict()]):
            caption = e.build_message(candidate)
            self.assertIn('#드리프트 재단', caption)
            self.assertIn('#Drift', caption)
        tagged, _ = e._inject_inline_tags('플레어가 FLR 기반 서비스를 출시하고 에테나가 ENA 관련 제휴를 발표함', story('Flare FLR and Ethena ENA'))
        for tag in ('#플레어', '#FLR', '#에테나', '#ENA'):
            self.assertIn(tag, tagged)
        specs = e._candidate_specs('Prices drift lower', story('Prices drift lower'))
        self.assertNotIn('드리프트', [s.label for s in specs])


if __name__ == '__main__':
    unittest.main()
