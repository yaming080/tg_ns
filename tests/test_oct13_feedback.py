"""Offline regressions for the reported intake, numeric crash and source gaps."""
import ast
import json
import random
import re
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import doorinews_editor as e
import news_coverage as c
import news_oct13_scope as scope
import news_manual_oct13 as manual
import news_event_review as events
import news_quality as quality
from news_source_cleanup import extract_article_text

TITLES = (
 '바이낸스, 한국 주식 투자상품 출시 검토…시총 상위 10개 종목 수요',
 'Sanctioned Russian payment network A7 unveils new USDT service',
 'Sberbank wins Russia’s approval for crypto exchange services',
 '美 가상자산 업계, 중간선거 앞두고 친가상자산 후보 지원에 270만달러 투입',
 'Singapore Gulf Bank expands 24/7 USD payments through BNY',
 '前 CFTC 위원장 대행 가상자산 규제, 기존 법률로 충분',
 'XRP treasury Evernorth’s shares rise 5% at Nasdaq opening print',
 'Morgan Stanley expects to support tokenized equities in Q1 2027, digital asset strategy head says',
)
def story(title, **values):
    return dict(title=title, pub=max(datetime.now(timezone.utc),scope.ENABLED_AT+timedelta(seconds=1)).isoformat(),url='https://example.com/new',**values)


class Oct13Tests(unittest.TestCase):
    def test_all_eight_future_equivalents_reach_review(self):
        for title in TITLES:
            with self.subTest(title=title):
                self.assertFalse(e._is_hard_blocked(story(title))[0])
                self.assertTrue(e.matches_keywords(story(title),[],[],[]))

    def test_bilingual_headlines(self):
        for title in ('Binance considers Korean stock investment products',
                      '러시아 중앙은행, 스베르방크 가상자산 거래 허가 기관 등록',
                      '제재 대상 러시아 결제 네트워크 A7, 새 USDT 서비스 공개',
                      '싱가포르 걸프은행, BNY와 제휴해 24시간 달러 결제 확대',
                      'US crypto industry spends $2.7 million on election candidates'):
            self.assertTrue(scope.scope(story(title)),title)

    def test_new_scope_excludes_old_or_undated_backlog(self):
        for title in TITLES[:6]:
            for pub in ('', 'bad', scope.ENABLED_AT.isoformat()):
                s=story(title);s['pub']=pub
                self.assertTrue(e._is_hard_blocked(s)[0],(title,pub))

    def test_confirmed_posts_skip_before_model_calls(self):
        with patch.object(e,'_call_openai') as model:
            for url,title,_ in manual.EVENTS:
                for suffix in ('','?utm_source=rss','/'):
                    s=story(title);s['url']=url.rstrip('/')+suffix
                    self.assertIn('게시',e._is_hard_blocked(s)[1])
                    self.assertEqual(e.build_message(s),'')
        model.assert_not_called()
        records=events.history_records({})
        for url,_,_ in manual.EVENTS:
            self.assertTrue(any(r['url']==url for r in records))
        self.assertEqual(len(manual.EVENTS),8)
        self.assertFalse(any('2109579312999346639' in r['url'] for r in records))

    def test_existing_exclusions_remain(self):
        for title in ('Sui launches USDT payment network service',
                      'XRP Ledger critical vulnerability patched',
                      'Binance Korean stocks price prediction sponsored giveaway',
                      'Evernorth stock price target after Nasdaq debut',
                      'Bank announces mortgage rate discount',
                      'US election candidates offer general support for crypto'):
            self.assertTrue(e._is_hard_blocked(story(title))[0],title)

    def test_numeric_parser_ignores_commas_without_digits(self):
        for text in (', won', ', krw', 'Company, won approval', '$, million',
                     ', developers', '개발자 , 명', ', 개 팀'):
            with self.subTest(text=text):
                self.assertEqual(e._amount_tokens(text),set())
                e.build_story_signature(story(text))

    def test_numeric_parser_preserves_duplicate_anchors(self):
        tokens=e._amount_tokens('$2.7 million; 1,000 won; 6 developers; 473 XRP; 5%')
        self.assertTrue({'amount_usd_2700000','amount_krw_1000','count_developers_6','amount_xrp_473','amount_pct_5'}<=tokens)
        rng=random.Random(13)
        for _ in range(200):
            prefix=''.join(rng.choice(', .:;') for _ in range(12))
            e._amount_tokens(prefix+' won '+prefix+' developers '+prefix+' million dollars')

    def test_short_korean_names_tag_in_body(self):
        s=story('Caroline Pham CFTC statement')
        tagged,_=e._inject_inline_tags(e._clean_summary('캐롤라인 팸 전 CFTC 위원장 대행은 현행 규제로 감독할 수 있다고 주장했다'),s)
        self.assertIn('#캐롤라인팸',tagged)
        self.assertIn('#CFTC',tagged)
        s=story('Singapore Gulf Bank expands USD payments through BNY')
        tagged,_=e._inject_inline_tags(e._clean_summary('Singapore Gulf Bank가 BNY와 달러 결제 제휴를 발표했다'),s)
        self.assertIn('#싱가포르걸프은행',tagged)
        self.assertIn('#BNY',tagged)

    def test_source_review_remains_fail_closed_with_new_guidance(self):
        captured=[]
        checks=dict.fromkeys(('faithful','conditions_preserved','allowed_category','new_substantive_fact','source_sufficient','understandable'),True)
        checks['source_sufficient']=False
        reply=json.dumps(dict(publish=False,reason='RSS 설명만 확보',checks=checks))
        with patch.object(e,'_call_openai',side_effect=lambda p:captured.append(p) or reply):
            self.assertFalse(e._validate_summary_against_source(TITLES[-1],'Infrastructure only.','2027년 1분기 목표'))
        self.assertIn('실제 첫 거래 개시',captured[0])
        self.assertIn('전직 인사의 발언',captured[0])
        self.assertIn('제재 대상이라는 조건',captured[0])

    def test_listing_plan_and_first_trade_are_distinct_but_same_stage_is_not(self):
        planned=quality.approval_stage_tokens('Evernorth merger completed ahead of Nasdaq debut')
        actual=quality.approval_stage_tokens(TITLES[6])
        translated=quality.approval_stage_tokens('에버노스 나스닥 상장 첫날 5% 상승')
        self.assertTrue(quality.event_conflicts(planned,actual))
        self.assertFalse(quality.event_conflicts(actual,translated))

    def test_unrelated_structured_or_article_card_is_not_used(self):
        html='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','headline':'Different title','articleBody':'Other story '*60})+'</script>'
        html+='<article><h1>Different title</h1><p>Related news is not the requested article evidence.</p></article>'
        self.assertEqual(extract_article_text(html,'https://example.com/new','Primary headline'),'')

    def test_structured_body_keeps_later_timing_and_skips_other_url(self):
        body='Morgan Stanley is building infrastructure. '*8+'Amy Oldenburg targets Q1 2027.'
        nodes=[{'@type':'NewsArticle','url':'https://example.com/other','articleBody':'WRONG '*100},
               {'@type':'NewsArticle','url':'https://example.com/new','articleBody':body}]
        html='<script type="application/ld+json">'+json.dumps(nodes)+'</script>'
        self.assertEqual(extract_article_text(html,'https://example.com/new'),body.strip())

    def test_primary_article_beats_related_card_and_twenty_paragraph_limit(self):
        html='<article><p>Related story teaser that is not the main report.</p></article>'
        html+='<article><h1>Primary headline</h1><picture>Not a paragraph</picture>'
        html+=''.join('<p>Background paragraph number %s with context.</p>'%i for i in range(22))
        html+='<p>New launch is conditional on regulatory approval in Q1 2027.</p></article>'
        text=extract_article_text(html,title='Primary headline')
        self.assertIn('conditional on regulatory approval in Q1 2027',text)
        self.assertNotIn('Related story',text)
        self.assertNotIn('Not a paragraph',text)

    def test_source_failure_explained_without_fabricating_body(self):
        tree=ast.parse((Path(__file__).parents[1]/'doorinews_bot.py').read_text(encoding='utf-8'))
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('fetch_article_text','get_best_source_text')]
        logs=[]
        def failed(*a,**k):raise OSError('network unavailable')
        ns=dict(http_get=failed,log=logs.append,cleanup_text=lambda x:x)
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'source','exec'),ns)
        s=story(TITLES[-1],desc='Only a short RSS description about infrastructure. '*3)
        self.assertEqual(ns['get_best_source_text'](s),s['desc'].strip())
        self.assertEqual(s['_source_kind'],'rss_description')
        self.assertIn('OSError',logs[0])
        packet=json.loads(c.source_packet(s,s['desc']))
        self.assertEqual(packet['source_kind'],'rss_description')


if __name__=='__main__':unittest.main()
