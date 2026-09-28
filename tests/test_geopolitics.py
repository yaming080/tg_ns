"""User-approved international news scope; no network or Telegram calls."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import unittest
from unittest.mock import patch

import doorinews_editor as e
from news_quality import (GEOPOLITICS_ENABLED_AT, GEOPOLITICS_SCOPE,
                          channel_scope_reason, geopolitics_intake_reason)


def story(title, **extra):
    return {'title': title, 'pub': datetime.now(timezone.utc).isoformat(), **extra}


class GeopoliticsTests(unittest.TestCase):
    def test_confirmed_diplomacy_enters_review(self):
        for title in (
            '이란, 호르무즈 재개방 기존 조건 유지…美 공식 답변 대기',
            '미국·중국, 관세 인하 합의 발표',
            '유럽연합, 러시아 경제 제재 강화 발표',
            '이스라엘, 휴전 합의 서명',
            '미국·중국 정상회담 개최',
            'Iran maintains conditions for reopening Strait of Hormuz',
            'US and China sign trade deal reducing tariffs',
            'EU announces new sanctions against Russia',
            'Israel accepts ceasefire proposal',
            'US and Iran resume nuclear talks',
        ):
            with self.subTest(title=title):
                item = story(title)
                self.assertEqual(channel_scope_reason(item), GEOPOLITICS_SCOPE)
                self.assertTrue(e.matches_keywords(item, [], [], []))

    def test_lifestyle_metrics_rumors_and_commentary_stay_out(self):
        for title in (
            '서울 통신비 주요 6개 도시 중 최고 수준…4G 20GB 도쿄의 2.3배',
            '중동 원유 수출 1280만배럴 회복…호르무즈 통항은 저조',
            '원·달러 NDF 2.1원 하락, 호르무즈 재개방 낙관론',
            '트럼프, 호르무즈를 트럼프 해협으로 바꾼 지도 게시',
            '미국 관세 협상 합의 가능성…전문가 전망',
            'US could announce new Iran sanctions, analysts predict',
            '아서 헤이즈 "로빈후드, 이더리움 보안성 인정…목표가 5000弗"',
            'Ethereum price could rally to $5,000: Arthur Hayes',
            'RIN/USDT trading launches on XT',
        ):
            with self.subTest(title=title):
                self.assertFalse(e.matches_keywords(story(title), [], [], []))

    def test_background_diplomacy_does_not_change_subject(self):
        item = story('서울 통신비 비교 발표', desc='미국과 중국은 관세 인하 합의를 발표했다.')
        self.assertFalse(e.matches_keywords(item, [], [], []))

    def test_sponsored_geopolitics_stays_blocked(self):
        item = story('US and China sign trade deal', article_text='Sponsored content: Register with referral code ABC')
        self.assertTrue(e._is_hard_blocked(item)[0])

    def test_pre_activation_backlog_and_exact_boundary_are_blocked(self):
        for delta in (-60, 0):
            item = story('미국·중국, 관세 인하 합의 발표',
                         pub=(GEOPOLITICS_ENABLED_AT + timedelta(seconds=delta)).isoformat())
            self.assertIn('과거 대기열', geopolitics_intake_reason(item))
            self.assertFalse(e.matches_keywords(item, [], [], []))

    def test_new_dates_accept_iso_and_rss_timezones(self):
        date = GEOPOLITICS_ENABLED_AT + timedelta(seconds=1)
        for value in (date.isoformat(), format_datetime(date),
                      date.astimezone(timezone(timedelta(hours=9))).isoformat()):
            self.assertEqual(geopolitics_intake_reason(story('US and China sign trade deal', pub=value)), '')

    def test_missing_bad_naive_and_future_dates_do_not_publish(self):
        for value in ('', 'not-a-date', '2026-09-28T17:30:00', '2099-01-01T00:00:00Z'):
            with self.subTest(value=value):
                self.assertFalse(e.matches_keywords(story('US and China sign trade deal', pub=value), [], [], []))

    def test_cutover_does_not_change_existing_crypto_policy(self):
        item = {'title': '한국 원화 스테이블코인 유동성 규제 검토 중'}
        self.assertEqual(geopolitics_intake_reason(item), '')
        self.assertTrue(e.matches_keywords(item, [], [], []))

    def test_confirmed_manual_and_rejected_articles_never_requeue(self):
        for number in (121114, 121125):
            item = story('미국·중국, 관세 인하 합의 발표',
                         url=f'https://www.bloomingbit.io/feed/news/{number}/?utm_source=rss')
            with patch.object(e, '_call_openai') as ai:
                self.assertEqual(e.build_message(item), '')
                ai.assert_not_called()

    def test_allowed_category_still_requires_source_verification(self):
        item = story('이란, 호르무즈 재개방 조건 유지 발표',
                     desc='이란은 조건 유지와 미국의 답변을 기다린다는 새 공식 입장을 발표했다.')
        with patch.object(e, '_RUNTIME', {}), patch.object(e, '_call_openai',
                side_effect=['이란이 호르무즈 재개방에 합의했다고 밝힘',
                             '{"publish": false, "reason": "대기를 합의로 왜곡"}']):
            self.assertEqual(e.build_message(item), '')

    def test_international_entity_tag_particle_boundaries(self):
        item = story('Iran announces conditions for reopening Strait of Hormuz')
        tagged, _ = e._inject_inline_tags('이란이 호르무즈 재개방 조건을 발표함', item)
        self.assertIn('#이란 이', tagged)
        self.assertIn('#호르무즈 ', tagged)


if __name__ == '__main__':
    unittest.main()
