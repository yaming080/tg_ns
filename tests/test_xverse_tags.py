"""User-reported Xverse caption and aliases; no live API calls or publishing."""
import unittest
from unittest.mock import patch
import doorinews_editor as e


class XverseTags(unittest.TestCase):
    def test_reported_caption_has_subject_people_and_investor_tags(self):
        story={'title':'Xverse raises strategic investment from Tim Draper and Draper Associates'}
        summary=('Xverse가 팀 드레이퍼의 드레이퍼 어소시에이츠 등이 참여한 전략적 투자 유치를 바탕으로 '
                 '이용자가 개인키를 직접 관리하는 비수탁형 비트코인 네오뱅크 개발을 확대한다고 밝힘\n\n'
                 '조달 금액은 공개하지 않았으며 예치 수익·결제·비트코인 담보 대출 서비스 확장에 자금을 쓸 계획이라고 전함')
        tagged,selected=e._inject_inline_tags(summary,story)
        for term in ('#엑스버스 가','#팀드레이퍼 의','#드레이퍼어소시에이츠 등이',
                     '개인키를 직접 관리','조달 금액은 공개하지 않았으며','계획이라고'):
            self.assertIn(term,tagged)
        self.assertNotIn('#비트코인',tagged)
        self.assertNotIn('#BTC',tagged)
        footer=e._build_footer_tags(story,selected)
        for tag in ('#Xverse','#TimDraper','#DraperAssociates'):
            self.assertIn(tag,footer)
        self.assertEqual(footer[-6:],list(e.FIXED_FOOTER_TAGS))

    def test_aliases_particles_and_repeats(self):
        for name in ('Xverse','xverse','엑스버스'):
            text,selected=e._inject_inline_tags(f'{name}가 서비스를 출시했다고 밝힘. {name}는 개인키를 보관하지 않음',{})
            self.assertEqual(text.count('#엑스버스'),1)
            self.assertIn('#엑스버스 가',text)
        for name in ('Tim Draper','팀 드레이퍼','팀드레이퍼'):
            text,_=e._inject_inline_tags(f'{name}의 투자라고 밝힘',{})
            self.assertIn('#팀드레이퍼 의',text)
        for name in ('Draper Associates','드레이퍼 어소시에이츠','드레이퍼어소시에이츠'):
            text,_=e._inject_inline_tags(f'{name}가 투자에 참여했다고 밝힘',{})
            self.assertIn('#드레이퍼어소시에이츠 가',text)

    def test_background_mentions_do_not_create_unrelated_footer_tags(self):
        story={'title':'은행이 새 결제 서비스를 출시', 'article_text':'Background: Xverse Tim Draper Draper Associates'}
        text,selected=e._inject_inline_tags('은행이 새 결제 서비스를 출시했다고 밝힘',story)
        footer=e._build_footer_tags(story,selected)
        self.assertNotIn('#Xverse',footer)
        self.assertNotIn('#TimDraper',footer)
        self.assertNotIn('#DraperAssociates',footer)

    def test_partial_names_do_not_match(self):
        text,selected=e._inject_inline_tags('XverseLabs와 Tim Draperson, Draper Fisher가 발표했다고 밝힘',{})
        self.assertFalse(selected)
        self.assertNotIn('#',text)

    def test_full_caption_keeps_fixed_footer(self):
        story={'title':'Xverse raises investment from Tim Draper', 'url':'https://example.com/article'}
        with patch.object(e,'_is_hard_blocked',return_value=(False,'')),patch.object(e,'_rewrite_summary',return_value='Xverse가 팀 드레이퍼의 투자를 받아 비트코인 결제 서비스를 확대할 계획이라고 밝힘'):
            caption=e.build_message(story)
        self.assertIn('#엑스버스 가',caption)
        self.assertIn('#팀드레이퍼 의',caption)
        self.assertIn('#Xverse',caption)
        self.assertTrue(caption.endswith(' '.join(e.FIXED_FOOTER_TAGS)))
