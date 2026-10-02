"""Team edits: subject tags and primary-subject image review; no external calls."""
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from PIL import Image
import doorinews_editor as editor
import news_images as images
from news_publication import prepare_publication


def photo(color):
    output = io.BytesIO()
    Image.new('RGB', (640, 360), color).save(output, format='PNG')
    return output.getvalue()


def decision(**checks):
    result = dict.fromkeys(images.IMAGE_CHECKS, True)
    result.update(checks)
    return SimpleNamespace(output_text=json.dumps(dict(approved=True, reason='주체 대조 결과', checks=result)))


class SubjectTagsAndImages(unittest.TestCase):
    def test_missing_subject_names_get_inline_and_footer_tags(self):
        cases = (
            ('Uphold Vault adds inheritance for XRP and Bitcoin',
             '업홀드가 자가 보관 서비스 볼트에 XRP·비트코인 상속 기능을 출시했다고 밝힘',
             '#업홀드', '#Uphold'),
            ('Silicon Valley Acquisition filing mentions Ripple in director biography',
             '실리콘밸리어퀴지션이 SEC 제출 서류의 이사 경력 소개에서 리플을 언급했으며 합병을 뜻하지 않는다고 밝힘',
             '#실리콘밸리어퀴지션', '#SiliconValleyAcquisition'),
            ('Phantom wallet adds BNB Chain support',
             '팬텀 월렛이 BNB Chain 지원을 추가했다고 밝힘', '#팬텀', '#Phantom'),
            ('MetaMask exits Ethereum validators after infrastructure incident',
             '메타마스크가 이더리움 검증자 종료 절차를 진행 중이며 조사 시점까지 고객 자금 피해 징후는 없다고 밝힘',
             '#메타마스크', '#MetaMask'),
            ('Flare launches confidential compute on Songbird',
             '플레어가 송버드에서 비공개 데이터를 검증하는 서비스를 출시했다고 밝힘',
             '#송버드', '#Songbird'),
        )
        for title, body, tag, footer_tag in cases:
            with self.subTest(title=title), patch.object(editor, '_RUNTIME', {}):
                candidate = {'title': title}
                tagged, selected = editor._inject_inline_tags(body, candidate)
                self.assertIn(tag, tagged)
                footer = editor._build_footer_tags(candidate, selected)
                self.assertIn(footer_tag, footer)
                self.assertEqual(footer[-6:], list(editor.FIXED_FOOTER_TAGS))
                if 'Phantom' in title:
                    self.assertIn('#월렛', tagged)
                if 'Silicon' in title:
                    self.assertIn('합병을 뜻하지 않는다고', tagged)
                if 'MetaMask' in title:
                    self.assertIn('조사 시점까지 고객 자금 피해 징후는 없다고', tagged)

    def test_ousd_tag_keeps_secondary_networks_as_plain_facts(self):
        body = '코인베이스가 OUSD 입출금을 Base·이더리움·솔라나·템포 4개 네트워크에서 지원하며 지원 지역에서 제공된다고 밝힘'
        for title in ('Coinbase adds OUSD deposits and withdrawals',
                      'Coinbase supports OUSD on Ethereum, Solana, Base and Tempo'):
            candidate = {'title': title}
            tagged, selected = editor._inject_inline_tags(body, candidate)
            self.assertIn('#OUSD', tagged)
            self.assertIn('솔라나', tagged)
            self.assertNotIn('#솔라나', tagged)
            self.assertNotIn('#SOL', editor._build_footer_tags(candidate, selected))
            self.assertIn('4개 네트워크', tagged)
            self.assertIn('지원 지역', tagged)

    def test_no_new_tags_from_unmentioned_entities_or_ticker_guessing(self):
        for text in ('OUSD deposits are supported', 'Fantom launches a service'):
            tagged, selected = editor._inject_inline_tags(text, {'title': text})
            footer = editor._build_footer_tags({'title': text}, selected)
            self.assertNotIn('#OpenUSD', footer)
            self.assertNotIn('#메타마스크', tagged)
            if 'Fantom' in text:
                self.assertNotIn('#팬텀', tagged)
        tagged, _ = editor._inject_inline_tags('솔라나가 새 결제 서비스를 출시했다고 밝힘', {'title': 'Solana launches payments service'})
        self.assertIn('#솔라나', tagged)

    def test_secondary_coin_and_generic_art_are_rejected_even_if_relevant(self):
        data = photo('blue')
        for field in ('primary_subject', 'not_incidental_asset_only', 'identifiable_subject'):
            client = Mock()
            client.responses.create.return_value = decision(**{field: False})
            approved, _ = images.review_image(client, 'existing-model', {'title': 'Coinbase supports OUSD'}, 'OUSD 입출금 지원', data, 'image/png')
            self.assertFalse(approved)
        # A pre-v27 response omitting the new fields must not silently pass.
        client.responses.create.return_value = SimpleNamespace(output_text=json.dumps(dict(
            approved=True, reason='related', checks=dict.fromkeys(images.IMAGE_CHECKS[:5], True))))
        self.assertFalse(images.review_image(client, 'existing-model', {}, 'caption', data, 'image/png')[0])

    def test_image_prompt_uses_article_body_without_fixed_btc_footer(self):
        client = Mock()
        client.responses.create.return_value = decision()
        caption = '코인베이스가 OUSD를 지원한다고 밝힘\n\n🌐 공식 도리뉴스\n\n출처\n\n#BTC #비트코인 #dooridoori'
        self.assertTrue(images.review_image(client, 'existing-model', {'title': 'Coinbase supports OUSD'}, caption, photo('blue'), 'image/png')[0])
        content = client.responses.create.call_args.kwargs['input'][0]['content']
        evidence = json.loads(content[0]['text'].split('자료: ', 1)[1])
        self.assertEqual(evidence['caption_body'], '코인베이스가 OUSD를 지원한다고 밝힘')
        self.assertNotIn('#BTC', evidence['caption_body'])
        self.assertIn('지원 네트워크', content[0]['text'])
        self.assertTrue(content[1]['image_url'].startswith('data:image/png;base64,'))

    def test_rejected_solana_cover_uses_reviewed_product_image(self):
        page = b'<meta property="og:image" content="/ousd.png">'
        solana, ousd = photo('purple'), photo('blue')
        def fetch(url, *args):
            return page if url.endswith('/news') else solana if url.endswith('/solana.png') else ousd
        client = Mock()
        client.responses.create.side_effect = [decision(primary_subject=False, not_incidental_asset_only=False), decision()]
        candidate = {'title': 'Coinbase supports OUSD', 'url': 'https://example.com/news', 'image_url': 'https://example.com/solana.png'}
        selector = lambda s, c, cl, m: images.select_image(s, c, cl, m, fetch=fetch)
        with patch.object(images.urllib.request, 'urlopen') as sender:
            prepared = prepare_publication(candidate, lambda _: '코인베이스가 OUSD 입출금을 지원한다고 밝힘', client, 'existing-model', selector)
            self.assertEqual(prepared['status'], 'ready')
            self.assertEqual(prepared['image'].source_url, 'https://example.com/ousd.png')
            self.assertEqual(prepared['image'].data, ousd)
            self.assertFalse(prepared['attempts'][0]['accepted'])
            sender.assert_not_called()

    def test_all_images_without_primary_subject_hold_the_post(self):
        client = Mock()
        client.responses.create.return_value = decision(primary_subject=False)
        candidate = {'title': 'Flare launches confidential compute on Songbird', 'url': 'https://example.com/news', 'image_url': 'https://example.com/art.png'}
        fetch = lambda url, *args: b'<article></article>' if url.endswith('/news') else photo('pink')
        selector = lambda s, c, cl, m: images.select_image(s, c, cl, m, fetch=fetch)
        result = prepare_publication(candidate, lambda _: '플레어가 서비스를 출시함', client, 'existing-model', selector)
        self.assertEqual(result['status'], 'held')
        self.assertIsNone(result['image'])

    def test_additional_source_images_are_bounded_and_can_be_tried(self):
        page = ('<article>' + ''.join(f'<img src="/{i}.png">' for i in range(10)) + '</article>').encode()
        candidate = {'url': 'https://example.com/news'}
        urls = images.image_candidates(candidate, lambda *args: page)
        self.assertEqual(len(urls), 6)
        review = Mock(side_effect=[(False, 'secondary')] * 4 + [(True, 'product')])
        image, attempts = images.select_image(candidate, '본문', None, None,
            fetch=lambda url, *args: page if url.endswith('/news') else photo('blue'), review=review)
        self.assertEqual(image.source_url, 'https://example.com/4.png')
        self.assertEqual(len(attempts), 5)


if __name__ == '__main__':
    unittest.main()
