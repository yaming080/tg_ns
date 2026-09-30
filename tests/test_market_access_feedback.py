"""Future coverage from Sep 30 examples; no live model or Telegram calls."""
from datetime import datetime, timezone, timedelta
import json
import unittest
from unittest.mock import patch
import doorinews_editor as e
from news_quality import MARKET_ACCESS_ENABLED_AT, manual_post_reason
from news_event_review import history_records

TITLES = (
    '트럼프, 북한의 핵 능력 다시 인정…김정은에 유화 메시지',
    '관리규모 4조달러 브라질 인프라 기업, XRP레저에 펀드 기록 생성',
    "HSBC, 홍콩달러 스테이블코인 명칭 '레드코인'으로 확정",
    'Robinhood plans 10x crypto perps for U.S. traders',
    '집 사면 대출 이자 내립니다…다급해진 중국 초강수',
)
URLS = (
    'https://www.etoday.co.kr/news/view/2630619?trc=main_list_pick',
    'https://bloomingbit.io/feed/news/121308',
    'https://bloomingbit.io/feed/news/121305',
    'https://crypto.news/robinhood-plans-10x-crypto-perps-for-u-s-traders/',
    'https://bloomingbit.io/feed/news/121311',
)


def story(title, **kw):
    return dict(title=title, pub=datetime.now(timezone.utc).isoformat(), **kw)


class MarketAccessFeedback(unittest.TestCase):
    def test_future_equivalent_news_enters_source_review(self):
        titles=TITLES+(
            'President acknowledges nuclear capability in new diplomatic statement',
            'CSD BR registers fund records on XRP Ledger',
            'Central securities depository records bonds on Ethereum',
            'Bank names new dollar stablecoin',
            'Kraken plans crypto perpetual futures for new market',
            'China announces housing mortgage interest subsidies',
            '정부, 주택 대출 이자 지원책 발표',
        )
        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(e.matches_keywords(story(title), [], [], []))

    def test_already_manual_posted_urls_stay_blocked_with_tracking(self):
        for title,url in zip(TITLES,URLS):
            for address in (url,url.replace('https://','')):
                candidate=story(title,url=address)
                self.assertTrue(manual_post_reason(candidate))
                with patch.object(e,'_call_openai') as model:
                    self.assertEqual(e.build_message(candidate),'')
                    model.assert_not_called()
        evidence=' '.join(r['title'] for r in history_records({}))
        for term in ('CSD BR','HSBC','Robinhood','China housing','Trump acknowledges'):
            self.assertIn(term,evidence)

    def test_old_or_unknown_queue_does_not_reappear_after_expansion(self):
        for title in TITLES:
            for pub in ('', 'bad', MARKET_ACCESS_ENABLED_AT.isoformat(),
                        (MARKET_ACCESS_ENABLED_AT-timedelta(days=1)).isoformat()):
                self.assertFalse(e.matches_keywords(dict(title=title,pub=pub),[],[],[]))

    def test_ads_price_predictions_lifestyle_and_opinion_remain_excluded(self):
        for title in (
            '서울 통신비 세계 최고',
            'HSBC stock price target raised',
            'Robinhood crypto perps referral sign-up bonus',
            '중국 부동산 부양책 전망: 집값 상승 예측',
            '은행 주택 대출 이자 비교 추천',
            'Arthur Hayes praises Robinhood Ethereum security',
            'CSD BR XRP price prediction after fund tokenization',
        ):
            self.assertFalse(e.matches_keywords(story(title),[],[],[]),title)

    def test_new_scopes_still_require_source_and_two_editorial_reviews(self):
        source='Robinhood plans crypto perpetual futures with up to 10x leverage for eligible US traders. Approval and timing have not been finalized.'
        summary='로빈후드가 미국의 적격 이용자를 대상으로 최대 10배 레버리지의 암호화폐 무기한 선물 제공을 계획하며 승인과 출시 일정은 미정이라고 밝힘'
        checks=dict.fromkeys(('faithful','conditions_preserved','allowed_category','new_substantive_fact','source_sufficient','understandable'),True)
        candidate=story(TITLES[3],article_text=source)
        with patch.object(e,'_RUNTIME',{}),patch.object(e,'_call_openai',side_effect=[summary,json.dumps(dict(publish=True,reason='원문 대조',checks=checks))]) as model:
            caption=e.build_message(candidate)
            self.assertIn('10배',caption)
            self.assertNotIn('수수료',caption)
            self.assertEqual(model.call_count,2)
            for call in model.call_args_list:
                self.assertIn(e.MARKET_ACCESS_GUIDANCE,call.args[0])
        checks['faithful']=False
        with patch.object(e,'_RUNTIME',{}),patch.object(e,'_call_openai',side_effect=['수수료를 10배 지급한다고 밝힘',json.dumps(dict(publish=False,reason='배수 의미 오류',checks=checks))]):
            self.assertEqual(e.build_message(candidate),'')
        with patch.object(e,'_RUNTIME',{}),patch.object(e,'_call_openai') as model:
            self.assertEqual(e.build_message(story(TITLES[3])),'')
            model.assert_not_called()


if __name__=='__main__':
    unittest.main()
