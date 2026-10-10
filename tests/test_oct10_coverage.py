import ast
import json
from pathlib import Path
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock
import doorinews_editor as e
import news_quality as q
import news_coverage as c
import news_sources as sources
from news_source_cleanup import strip_page_furniture, page_publication_date


TITLES = (
    '그리스, 디지털자산 10% 과세 추진…연 500유로까지 면제',
    '프랑스, 스테이블코인 과세 추진…투자 손실은 10년 공제',
    '미국 재무부, 국채 바이백 60억달러 매입 제안 수락',
    '9월 연준 FOMC 의사록, 연내 추가 인상 시사',
    '칼시 "연준 10월 금리 동결 확률 84%"',
    'Moscow Exchange Plans To Open Crypto Trading On December 1',
    'DOJ scrutinizes Binance compliance with its 2023 settlement',
    "'4억7300만XRP' 보유 에버노스, 스팩 합병 완료…12일 나스닥 거래 예정",
    'Evernoth’s Corporate Strategy for XRP You Need to See',
    'IMF Highlights XRP and XLM In Recent Report. Here’s why',
    'JP모건 "올해 가상자산 시장에 500억달러 유입…4분기 모멘텀 개선"',
    '아서 헤이즈 "강세장은 불안 속 시작…돈 풀리면 가격 오른다"',
    'Base creator Jesse Pollak predicts a tokenization supercycle led by tokenized equities',
    '쿠오모 전 뉴욕주지사 "토큰화 주식, 시장에 급진적 변화 가져올 것"',
    '저스틴 선 "2012년 전재산 암호화폐로 전환…시스템 업그레이드"',
    'MARA Holdings Dumps 996 BTC During $1 Billion Liquidations',
    'Ledger Probes $86M in Wallet Drains Linked to CryptoBilis',
    '레저, 동남아 자산 탈취 대응…크립토빌리스 판매 중단 요청',
    'Robinhood Crypto Explores New Product With T Rowe Price',
    'Blockchain.com Seeks CFTC Approval for Prediction Markets, Crypto Derivatives',
    'Chris Larsen Donated $22.5M to US Federal Candidates',
    'Bessent puts a one-week clock on a $1 billion Iran crypto seizure',
    '리플, 칸톤 네트워크 통합 완료…DTCC 출시 앞둬',
    'Ripple Emerges as Major Wall Street Threat',
    'President Trump Unveils $215M Quantum Computing Plan',
    'IMF restricts El Salvador Bitcoin accumulation',
)


def story(title=TITLES[0], **kw):
    return dict(title=title, desc='A newly reported event with source evidence.',
                url='https://example.com/new', pub=datetime.now(timezone.utc).isoformat(), **kw)


class CoverageTests(unittest.TestCase):
    def test_candidates_reach_source_review(self):
        for title in TITLES:
            with self.subTest(title=title):
                self.assertTrue(c.coverage_scope(story(title)))
                self.assertTrue(e.matches_keywords(story(title), [], [], []))

    def test_no_legacy_queue_release_or_undated_article(self):
        for title in TITLES:
            for pub in ('', (c.ENABLED_AT-timedelta(seconds=1)).isoformat()):
                s=story(title); s['pub']=pub
                with self.subTest(title=title, pub=pub):
                    self.assertTrue(e._is_hard_blocked(s)[0])

    def test_all_38_user_urls_block_before_model_even_with_future_dates(self):
        rows=json.loads((Path(__file__).parent/'oct10_user_articles.json').read_text(encoding='utf-8'))
        self.assertEqual(len(rows),38)
        with patch.object(e,'_call_openai') as model:
            for row in rows:
                s=story(); s['url']=row['url']+'?utm_source=rss'
                with self.subTest(name=row['name']):
                    self.assertEqual(e.build_message(s),'')
            model.assert_not_called()

    def test_promotions_charts_and_unrelated_mentions_stay_excluded(self):
        for title in ('Analyst XRP price prediction: 100x presale',
                      'Arthur Hayes Bitcoin price target $500000',
                      'Ledger sponsored wallet giveaway',
                      'RSI oversold: Evernorth XRP merger price prediction',
                      'New cooking recipes', 'Anonymous whale moves 900 BTC'):
            with self.subTest(title=title):
                self.assertFalse(c.coverage_scope(story(title)))
                self.assertFalse(e.matches_keywords(story(title),[],[],[]))
        s=story(TITLES[0],article_text='Sponsored content. Register using referral code xyz.')
        self.assertTrue(e._is_hard_blocked(s)[0])

    def test_conditional_summary_survives_only_after_source_approval(self):
        s=story('Blockchain.com Seeks CFTC Approval for Crypto Derivatives')
        good='블록체인닷컴이 CFTC 등록을 신청했으며 승인 시 파생상품 서비스를 제공할 수 있다고 밝힘'
        with patch.object(e,'_rewrite_summary',return_value=good):
            self.assertIn('승인 시', e.build_message(s))
        with patch.object(e,'_rewrite_summary',return_value=''):
            self.assertEqual(e.build_message(s),'')

    def test_new_source_failure_never_falls_back_to_unverified_publication(self):
        url='https://coingape.com/feed/'
        with patch.object(sources,'NEW_FEEDS',[('코인게이프',url)]):
            fetch=Mock(side_effect=OSError('unavailable'))
            state={}
            self.assertEqual(sources.collect_new_sources(state,fetch,lambda _:None,lambda _:None),[])
            self.assertEqual(fetch.call_count,2)
            self.assertNotIn(url,state.get('source_baselines',{}))

    def test_fallback_keeps_same_source_baseline(self):
        url='https://coingape.com/feed/'
        xml='<rss><channel><item><title>new</title><link>https://coingape.com/new</link><pubDate>Sat, 10 Oct 2026 11:00:00 +0000</pubDate></item></channel></rss>'
        with patch.object(sources,'NEW_FEEDS',[('코인게이프',url)]):
            state={}; log=[]
            self.assertEqual(sources.collect_new_sources(state,Mock(side_effect=[OSError(),xml]),lambda _:None,log.append),[])
            self.assertEqual(list(state['source_baselines']),[url])

    def test_publisher_date_not_embedded_tweet_date(self):
        raw='''<meta property="article:published_time" content="2026-10-09T12:00:00Z">
        <article><p>Ripple Custody integrated with Canton.</p>
        <blockquote><p>We are on X, follow us to connect</p><a>June 15, 2025</a></blockquote>
        <blockquote><p>Real source: the integration completed October 8, 2026.</p></blockquote></article>'''
        clean=strip_page_furniture(raw)
        self.assertNotIn('June 15, 2025',clean)
        self.assertIn('Real source:',clean)
        self.assertEqual(page_publication_date(raw),'2026-10-09T12:00:00Z')
        self.assertEqual(page_publication_date('<p>June 15, 2025</p>'),'')
        schema='<script type="application/ld+json">{"@graph":[{"@type":"NewsArticle","datePublished":"2026-10-09"}]}</script>'
        self.assertEqual(page_publication_date(schema),'2026-10-09')

    def test_longer_summary_keeps_conditions_and_subject_tags(self):
        raw='삼성전자가 삼성월렛의 USDC 송금을 지원한다고 밝힘\n\n출시는 규제 승인 여부에 따라 달라질 가능성이 있다고 설명함'
        clean=e._clean_summary(raw)
        self.assertIn('가능성',clean)
        tagged,_=e._inject_inline_tags(clean,story(raw))
        self.assertIn('#삼성전자',tagged)
        for raw,label in [('Travala가 예약 기능을 출시함','트라발라'),('아크가 문페이 연동을 발표함','아크'),('MoneyGram이 USDC 송금을 지원함','머니그램')]:
            tagged,_=e._inject_inline_tags(e._clean_summary(raw),story(raw))
            self.assertIn('#'+label,tagged)
        self.assertTrue(q.valid_caption('가'*320))

    def test_required_conditions_and_attribution_are_in_both_model_prompts(self):
        packet=c.source_packet(dict(story(),page_published_at='2026-10-10T11:00:00Z'),
                               'Actual article, quoting an event in 2025.')
        self.assertIn('page_published_at',packet)
        captured=[]
        verdict=json.dumps(dict(publish=False, reason='missing conditions', checks={
            key:False for key in ('faithful','conditions_preserved','allowed_category',
                                 'new_substantive_fact','source_sufficient','understandable')}))
        with patch.object(e,'_call_openai',side_effect=lambda prompt: captured.append(prompt) or verdict):
            self.assertFalse(e._validate_summary_against_source('test',packet,'미확정임'))
        self.assertIn('삽입 X 게시물 날짜',captured[0])
        self.assertIn('거래소로 이체',captured[0])
        self.assertIn('최대 320자',captured[0])

    def test_merger_completed_is_not_same_stage_as_approval(self):
        before=q.approval_stage_tokens('Evernorth merger approved, closing planned')
        after=q.approval_stage_tokens('Evernorth merger completed')
        self.assertTrue(q.event_conflicts(before,after))

    def test_legacy_collector_reads_beyond_six_but_not_old_backlog(self):
        tree=ast.parse((Path(__file__).parents[1]/'doorinews_bot.py').read_text(encoding='utf-8'))
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fetch_rss')
        import re, xml.etree.ElementTree as ET
        from html import unescape
        def xml(old=False):
            rows=[]
            for i in range(20):
                date='Fri, 09 Oct 2026 11:00:00 +0000' if old else 'Sat, 10 Oct 2026 11:00:00 +0000'
                rows.append(f'<item><title>News {i}</title><link>https://example.com/{i}</link><pubDate>{date}</pubDate></item>')
            return '<rss><channel>'+''.join(rows)+'</channel></rss>'
        ns=dict(MAX_ITEMS_PER_FEED=50,http_get=lambda *a,**k:xml(),ET=ET,re=re,unescape=unescape,
                fetch_article_meta=lambda *_:('',''),is_weak_text=lambda *_:False,log=lambda *_:None)
        exec(compile(ast.Module(body=[func],type_ignores=[]),'collector','exec'),ns)
        self.assertEqual(len(ns['fetch_rss']('test')),20)
        ns['http_get']=lambda *a,**k:xml(True)
        self.assertEqual(len(ns['fetch_rss']('test')),6)


if __name__=='__main__':
    unittest.main()
