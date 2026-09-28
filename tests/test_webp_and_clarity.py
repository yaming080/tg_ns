import io
import json
from pathlib import Path
import sys
from unittest import TestCase
from unittest.mock import Mock, patch

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import news_images as images
import doorinews_editor as editor


def webp(mode='RGB', size=(640, 360), animated=False):
    output = io.BytesIO()
    color = (20, 80, 140, 0) if mode == 'RGBA' else (20, 80, 140)
    picture = Image.new(mode, size, color)
    if animated:
        picture.save(output, 'WEBP', save_all=True,
                     append_images=[Image.new(mode, size, (140, 80, 20))], duration=100, loop=0)
    else:
        picture.save(output, 'WEBP', lossless=True)
    return output.getvalue()


class WebpAndClarity(TestCase):
    def test_webp_converted_reviewed_and_uploaded_as_same_jpeg(self):
        original = webp()
        seen = []
        def review(client, model, story, caption, data, mime):
            seen.append(data)
            self.assertEqual(images.inspect_image(data), ('image/jpeg', 640, 360))
            self.assertEqual(mime, 'image/jpeg')
            return True, '관련 사진'
        story = {'url': 'https://example.com/news', 'image_url': 'https://example.com/photo.webp'}
        fetch = lambda url, *args: b'<article></article>' if url.endswith('/news') else original
        picture, _ = images.select_image(story, '본문', None, 'm', fetch, review)
        self.assertEqual(picture.data, seen[0])
        self.assertNotEqual(picture.data, original)
        response = Mock(); response.read.return_value = b'{"ok":true}'
        manager = Mock(); manager.__enter__ = Mock(return_value=response); manager.__exit__ = Mock(return_value=False)
        with patch.object(images.urllib.request, 'urlopen', return_value=manager) as send:
            self.assertTrue(images.send_reviewed_photo('test', 'test', picture, '본문'))
            payload = send.call_args.args[0].data
            self.assertIn(seen[0], payload)
            self.assertIn(b'filename="news.jpg"', payload)
            self.assertNotIn(original, payload)

    def test_transparent_webp_composited_before_review(self):
        data, mime, width, height = images.prepare_image_bytes(webp('RGBA'))
        self.assertEqual((mime, width, height), ('image/jpeg', 640, 360))
        with Image.open(io.BytesIO(data)) as picture:
            self.assertEqual(picture.getpixel((0, 0)), (255, 255, 255))

    def test_animated_tiny_banner_truncated_webp_stay_rejected(self):
        for data in (webp(animated=True), webp(size=(40, 40)),
                     webp(size=(1800, 200)), webp()[:30]):
            with self.subTest(length=len(data)), self.assertRaises(Exception):
                images.prepare_image_bytes(data)

    def test_converted_output_still_obeys_byte_limit(self):
        data = webp()
        with patch.object(images, 'MAX_IMAGE_BYTES', len(data) + 1), self.assertRaises(ValueError):
            images.prepare_image_bytes(data)

    def test_png_and_jpeg_bytes_are_preserved(self):
        for fmt in ('PNG', 'JPEG'):
            output = io.BytesIO(); Image.new('RGB', (640, 360)).save(output, fmt)
            data = output.getvalue()
            self.assertEqual(images.prepare_image_bytes(data)[0], data)

    def test_conversion_does_not_override_negative_visual_review(self):
        story = {'url': 'https://example.com/news', 'image_url': 'https://example.com/cover.webp'}
        fetch = lambda url, *args: b'<article></article>' if url.endswith('/news') else webp()
        reviewer = Mock(return_value=(False, '광고 이미지'))
        picture, attempts = images.select_image(story, '본문', None, 'm', fetch, reviewer)
        self.assertIsNone(picture)
        self.assertEqual(attempts[0]['reason'], '광고 이미지')
        reviewer.assert_called_once()

    def test_diagnostic_reason_identifies_validation_failure(self):
        story = {'url': 'https://example.com/news', 'image_url': 'https://example.com/cover.webp'}
        fetch = lambda url, *args: b'<article></article>' if url.endswith('/news') else webp(size=(40, 40))
        reviewer = Mock()
        picture, attempts = images.select_image(story, '본문', None, 'm', fetch, reviewer)
        self.assertIsNone(picture); reviewer.assert_not_called()
        self.assertIn('image_validation: 너무 작거나', attempts[0]['reason'])

    def test_user_deleted_bip_article_stays_blocked_without_posted_state(self):
        story = {'title': '비트코인 BIP138 초안 공개',
                 'url': 'https://www.tokenpost.kr/news/blockchain/414798?utm_source=rss'}
        with patch.object(editor, '_call_openai') as ai:
            self.assertEqual(editor.build_message(story), '')
            ai.assert_not_called()
        self.assertIn('사용자 삭제', editor._is_hard_blocked(story)[1])
        self.assertFalse(editor._is_hard_blocked({
            'title': 'Bitcoin developers publish new network upgrade proposal',
            'url': 'https://example.com/different-proposal'})[0])

    def test_understandability_requires_explicit_true(self):
        for value in (False, None, 'true', True):
            checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                                    'new_substantive_fact', 'source_sufficient'), True)
            if value is not None:
                checks['understandable'] = value
            verdict = json.dumps({'publish': True, 'reason': '검토', 'checks': checks})
            with self.subTest(value=value), patch.object(editor, '_call_openai', return_value=verdict):
                self.assertEqual(editor._validate_summary_against_source('제안', '원문', '요약'), value is True)

    def test_unclear_technical_summary_never_becomes_caption(self):
        story = {'title': 'Bitcoin developers publish a new wallet backup proposal',
                 'desc': 'Developers published a draft wallet backup proposal.'}
        checks = dict.fromkeys(('faithful', 'conditions_preserved', 'allowed_category',
                               'new_substantive_fact', 'source_sufficient'), True)
        checks['understandable'] = False
        verdict = json.dumps({'publish': False, 'reason': '용어만 나열', 'checks': checks})
        with patch.object(editor, '_RUNTIME', {}), patch.object(editor, '_call_openai',
                side_effect=['비트코인 xpub 백업 구조 초안을 공개함', verdict]):
            self.assertEqual(editor.build_message(story), '')
