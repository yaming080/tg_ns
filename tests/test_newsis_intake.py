import json
from pathlib import Path
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import doorinews_editor as editor
import news_sources as sources
import news_review_cache as cache
from news_source_cleanup import extract_article_text
from news_nov26_scope import scope, ENABLED_AT

URL='https://www.newsis.com/view/NISX20261126_0003884450'
TITLE="[단독]금융위, '한국디지털자산업협회' 설립 추진…닥사 역할 변화 예고"


def story(title=TITLE):
    return dict(title=title,url=URL,pub=max(datetime.now(timezone.utc),ENABLED_AT+timedelta(minutes=1)).isoformat())


class NewsisIntake(unittest.TestCase):
    def test_official_feeds_and_silent_first_fetch(self):
        feeds=[pair for pair in sources.NEW_FEEDS if 'newsis.com' in pair[1]]
        self.assertEqual([u for _,u in feeds],['https://www.newsis.com/RSS/bank.xml','https://www.newsis.com/RSS/economy.xml'])
        now=ENABLED_AT+timedelta(hours=1)
        old=story();old['pub']=ENABLED_AT.isoformat()
        new=story();new.update(url=URL+'1',pub=(now+timedelta(minutes=1)).isoformat())
        state={}
        for _,feed in feeds:
            self.assertEqual(sources.after_baseline(state,feed,[old],now),[])
            self.assertEqual(sources.after_baseline(state,feed,[old,new],now+timedelta(minutes=2)),[new])
            old['pub']=(now+timedelta(minutes=1)).isoformat()
            self.assertEqual(sources.after_baseline(state,feed,[old],now+timedelta(minutes=2)),[])
            old['pub']=ENABLED_AT.isoformat()

    def test_new_rulemaking_reaches_fact_review_without_coin_name(self):
        for title in (TITLE,'정부, 디지털자산기본법 초안에 보호재단 신설 추진',
                      '금융위, 가상자산 거래지원·이상거래 업무규정 개정 추진',
                      '12월 3일부터 개정 외국환거래법 시행'):
            s=story(title)
            self.assertTrue(scope(s))
            self.assertFalse(editor._is_hard_blocked(s)[0],(title,editor._is_hard_blocked(s)))
            self.assertTrue(editor.matches_keywords(s,[],[],[]))

    def test_no_old_queue_or_invalid_date(self):
        for date in ('','bad',ENABLED_AT.isoformat(),'2026-11-26T10:00:00'):
            s=story();s['pub']=date
            self.assertTrue(editor._is_hard_blocked(s)[0])

    def test_unrelated_news_and_existing_exclusions_remain(self):
        for title in ('금융투자협회장상 수상','민간 디지털자산협회 회원 모집 행사',
                      '외국환거래법 개정 해설 광고','정부 동물보호협회 설립 추진'):
            self.assertFalse(scope(story(title)))
        for title in ('Sui launches USDC payment service','XRP Ledger critical vulnerability revealed'):
            self.assertTrue(editor._is_hard_blocked(story(title))[0])
        self.assertEqual(scope('cached request hash'),'')

    def test_draft_and_undecided_conditions_are_in_review_prompt(self):
        prompt=editor._summary_prompt(TITLE,'source')
        for text in ('초안 단계','전환 여부는 미정','실제 위원회 구성 완료','시행일을 합쳐 쓰지'):
            self.assertIn(text,prompt)
        tagged,_=editor._inject_inline_tags('금융위가 한국디지털자산업협회 설립을 추진하며 닥사 전환 여부는 미정임',story())
        self.assertIn('#한국디지털자산업협회',tagged)
        self.assertIn('#닥사',tagged)
        self.assertIn('미정',tagged)

    def test_preserve_unrelated_cache_and_original_expiry(self):
        manifest=json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text('utf8'))
        old=manifest['nov26_only_previous_identities'][0]
        with cache.review_session({},lambda:None,logger=lambda _:None) as store:
            expiry=store.clock()+1000
            for title,changed in ((TITLE,True),('Unchanged rejected article',False),('메타 스레드 암호화폐 시세 기능 도입',False)):
                record={'title':title,'source':'unchanged'}
                key=cache.fingerprint([cache.VERSION,old,'source_summary',record])
                store.data.setdefault('content_results_v1',{})[key]={'result':{'summary':'','reason':'excluded'},'expires':expiry}
                result=cache.content_result('source_summary',record)
                if changed:self.assertIsNone(result)
                else:self.assertEqual(result['reason'],'excluded')
            self.assertTrue(all(row['expires']==expiry for row in store.data['content_results_v1'].values()))


class NewsisBody(unittest.TestCase):
    body=('정부가 법정협회 설립을 추진한다. 제정안 초안 단계이며 협회 전환은 미정이다. '
          '기관별 역할과 승인 절차 및 이용자 보호 조건은 법안 심의 과정에서 논의된다. ')*4
    def html(self,title=TITLE,canonical=URL,body=None):
        return (f'<link rel="canonical" href="{canonical}"><meta property="og:title" content="{title}">'
                '<nav>메뉴</nav><div class="viewer"><article><div id="textBody"><div class="article_photo"><p>사진 설명과 메일</div></div>'
                +(body or self.body)+'<br>확정 아님<script>script noise</script><div id="view_ad">광고</div>'
                '<br>◎공감언론 뉴시스 연락처</article></div><article>무관한 추천 기사</article>')
    def test_br_text_outside_photo_div_is_extracted(self):
        body=extract_article_text(self.html(),URL,TITLE)
        self.assertIn('제정안 초안',body);self.assertIn('확정 아님',body)
        for noise in ('사진 설명','메일','script noise','광고','추천 기사','연락처'):
            self.assertNotIn(noise,body)
    def test_wrong_article_identity_and_incomplete_body_fail_closed(self):
        for page in (self.html(title='다른 기사'),self.html(canonical=URL+'9'),
                     self.html().replace('</article>',''),self.html(body='짧음')):
            self.assertEqual(extract_article_text(page,URL,TITLE),'')
    def test_fake_host_cannot_activate_publisher_parser(self):
        from news_newsis import article_body
        self.assertEqual(article_body(self.html(),'https://example.com/view/NISX20261126_0003884450',TITLE),'')


if __name__=='__main__':unittest.main()
