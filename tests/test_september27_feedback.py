"""Regression cases from user-reviewed posts; no API calls or Telegram sends."""
import unittest
from unittest.mock import patch
import doorinews_editor as e
from news_quality import manual_post_reason


class September27Feedback(unittest.TestCase):
    def test_stablecoin_and_regulator_news_enters_review(self):
        for title in (
            'South Korea weighs liquidity rules for won stablecoins',
            '한국, 원화 스테이블코인 유동성 규제 검토 중',
            'Circle gains Binance backing in USDC-Tether race',
            '서클, USDC 확대 위한 바이낸스와 제휴 계약 체결',
            'SEC Issues Fresh Crypto Guidance on Staking Tokens, Buybacks, and the Howey Test',
            'SEC Updates Crypto Asset FAQs on Staking Receipts',
            'SEC, 암호화폐 FAQ 공개…일부 스테이킹 토큰 분류 명확화',
        ):
            with self.subTest(title=title):
                self.assertTrue(e.matches_keywords({'title': title}, [], [], []))

    def test_unrelated_articles_stay_excluded(self):
        for title in (
            '서울 통신비 주요 6개 도시 중 최고 수준…4G 20GB 도쿄의 2.3배',
            'Airline issues new passenger rules',
            'RIN/USDT trading launches on XT',
            'RIN-USDC partnership announced for new trading market',
            'RIN 상장, USDT 마켓 거래 지원',
            'Circle signs office lease agreement',
            'Sponsored content: Circle announces USDC partnership',
            'Circle USDC price prediction: will it rise?',
        ):
            with self.subTest(title=title):
                self.assertFalse(e.matches_keywords({'title': title}, [], [], []))
        self.assertFalse(e.matches_keywords({
            'title': '서울 통신비 비교',
            'desc': '다른 소식으로 한국 원화 스테이블코인 규제를 검토 중이다',
        }, [], [], []))

    def test_background_clarity_support_does_not_block_new_policy(self):
        story = {
            'title': 'Federal Reserve Proposes Stablecoin Rules Under the GENIUS Act',
            'article_text': 'The Federal Reserve proposed stablecoin issuer rules. '
                            'Separately, the industry urges support for the CLARITY Act.',
        }
        self.assertFalse(e._is_hard_blocked(story)[0])
        self.assertTrue(e._is_hard_blocked({
            'title': 'Crypto industry urges support for CLARITY Act',
        })[0])

    def test_topic_particles_and_meaningful_name_boundaries(self):
        self.assertEqual(e.fix_hashtag_particles('#증권에 #토큰은 #스테이킹의'),
                         '#증권 에 #토큰 은 #스테이킹 의')
        self.assertEqual(e.fix_hashtag_particles('#인도 #국가 #미래에셋'),
                         '#인도 #국가 #미래에셋')
        text, _ = e._inject_inline_tags(
            'SEC가 일부 스테이킹 토큰은 증권에 해당하지 않는다고 지침을 제시함',
            {'title': 'SEC issues crypto staking token classification guidance'},
        )
        for wanted in ('#SEC 가', '#스테이킹', '#토큰 은', '#증권 에'):
            self.assertIn(wanted, text)

    def test_new_entity_name_has_boundary_at_insertion(self):
        for name, particle in (('새기관', '에서'), ('새서비스', '는'), ('NewProtocol', '을')):
            spec = e.EntitySpec('org', name, (name,), '')
            result, replaced = e._replace_surface_with_tag(name + particle + ' 발표함', spec)
            self.assertTrue(replaced)
            self.assertEqual(result, '#' + name + ' ' + particle + ' 발표함')

    def test_final_caption_keeps_particle_space_and_fixed_tags(self):
        story = {'title': 'SEC issues crypto staking token guidance', 'url': 'https://example.com/new-faq'}
        with patch.object(e, '_rewrite_summary', return_value='SEC가 일부 스테이킹 토큰은 증권에 해당하지 않는다고 지침을 제시함'):
            caption = e.build_message(story)
        self.assertIn('#증권 에', caption)
        self.assertNotIn('#증권에', caption)
        self.assertTrue(caption.endswith(' '.join(e.FIXED_FOOTER_TAGS)))

    def test_known_manual_articles_never_requeued(self):
        urls = (
            'https://crypto.news/circle-gains-binance-backing-in-usdc-tether-race/?utm_source=rss',
            'https://www.etoday.co.kr/news/view/2629507?trc=main_list_pick',
            'https://bloomingbit.io/feed/news/121107',
            'https://timestabloid.com/the-genius-act-will-amplify-xrps-use-case-expert-presents-proof/#news',
        )
        for url in urls:
            story = {'url': url, 'title': 'Circle gains Binance backing in USDC-Tether race'}
            with self.subTest(url=url), patch.object(e, '_call_openai') as ai:
                self.assertTrue(manual_post_reason(story))
                self.assertEqual(e.build_message(story), '')
                ai.assert_not_called()
        self.assertFalse(manual_post_reason({'url': 'https://crypto.news/a-new-circle-agreement/'}))
        self.assertFalse(manual_post_reason({'url': 'https://other.example/feed/news/121107'}))


if __name__ == '__main__':
    unittest.main()
