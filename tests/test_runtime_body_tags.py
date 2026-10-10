"""Exercise tags with the bot's real legacy dictionary, without starting the bot."""
import ast
from pathlib import Path
import unittest
from unittest.mock import patch

import doorinews_editor as e


def runtime_translations():
    tree = ast.parse(Path(e.__file__).with_name('doorinews_bot.py').read_text(encoding='utf-8'))
    dictionaries = {}

    def read(statements):
        for node in statements:
            if isinstance(node, ast.Try):
                read(node.body)
            elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        try:
                            dictionaries[target.id] = ast.literal_eval(node.value)
                        except (ValueError, TypeError):
                            pass
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if (isinstance(call.func, ast.Attribute) and call.func.attr == 'update'
                        and isinstance(call.func.value, ast.Name)
                        and call.func.value.id == 'MANUAL_TRANSLATIONS' and len(call.args) == 1):
                    value = call.args[0]
                    if isinstance(value, ast.Dict):
                        dictionaries['MANUAL_TRANSLATIONS'].update(ast.literal_eval(value))
                    elif isinstance(value, ast.Name):
                        dictionaries['MANUAL_TRANSLATIONS'].update(dictionaries[value.id])
    read(tree.body)
    return dictionaries['MANUAL_TRANSLATIONS']


class RuntimeBodyTagsTests(unittest.TestCase):
    def setUp(self):
        mapping = runtime_translations()
        self.assertEqual(mapping['BTC'], 'BTC')
        runtime = patch.object(e, '_RUNTIME', {'MANUAL_TRANSLATIONS': mapping})
        runtime.start()
        self.addCleanup(runtime.stop)

    def test_legacy_btc_alias_cannot_reintroduce_body_tag(self):
        story = {'title': 'Anchorage Digital launches Bitcoin custody', 'desc': 'BTC custody service'}
        body = '앵커리지 디지털이 BTC와 비트코인 수탁 서비스를 출시했다고 밝힘'
        tagged, selected = e._inject_inline_tags(body, story)
        self.assertIn('#앵커리지디지털 이', tagged)
        self.assertIn('BTC와 비트코인', tagged)
        self.assertNotRegex(tagged, r'#(?:BTC|Bitcoin|비트코인)(?:\W|[은는이가와과]|$)')
        footer = e._build_footer_tags(story, selected)
        self.assertIn('#AnchorageDigital', footer)
        self.assertEqual(footer[-6:], list(e.FIXED_FOOTER_TAGS))
        self.assertEqual(footer.count('#BTC'), 1)

    def test_full_subject_aliases_and_repetition(self):
        for alias in ('Anchorage Digital', '앵커리지 디지털', '앵커리지디지털'):
            with self.subTest(alias=alias):
                tagged, _ = e._inject_inline_tags(alias + '이 BTC 수탁을 지원하며 앵커리지디지털은 기관 고객을 대상으로 한다',
                                                {'title': 'Anchorage Digital expands BTC custody'})
                self.assertEqual(tagged.count('#앵커리지디지털'), 1)
                self.assertNotIn('#BTC', tagged)
                self.assertNotIn('#디지털', tagged)

    def test_rendered_caption_has_footer_btc_only(self):
        story = {'title': 'Anchorage Digital launches Bitcoin custody', 'desc': 'BTC custody',
                 'url': 'https://example.com/custody'}
        with patch.object(e, '_rewrite_summary', return_value='앵커리지디지털이 #BTC 수탁 서비스를 출시했다고 밝힘'):
            caption = e.build_message(story)
        self.assertTrue(caption)
        body = caption.split('🌐')[0]
        self.assertIn('#앵커리지디지털 이', body)
        self.assertNotIn('#BTC', body)
        self.assertEqual(caption.count('#BTC'), 1)
        self.assertTrue(caption.endswith(' '.join(e.FIXED_FOOTER_TAGS)))

    def test_bitcoin_named_organization_is_not_suppressed(self):
        text = '비트코인정책연구소가 BTC 규제 자료를 발표했다고 밝힘'
        tagged, _ = e._inject_inline_tags(text, {'title': 'Bitcoin Policy Institute releases BTC policy report'})
        self.assertIn('#비트코인정책연구소', tagged)
        self.assertNotIn('#BTC', tagged)

    def test_body_tags_do_not_change_editorial_scope(self):
        story = {'title': "Bitcoin treasury companies get two Anchorage routes into Sui's Hashi"}
        with patch.object(e, '_call_openai') as api:
            self.assertEqual(e.build_message(story), '')
            api.assert_not_called()

    def test_known_actor_spacing_does_not_drop_tags(self):
        cases = (
            ('Standard Chartered announces custody service', '스탠다드 차타드가 수탁 서비스를 발표함', '#스탠다드차타드 가'),
            ('Mastercard announces payments service', '마스터 카드가 결제 서비스를 발표함', '#마스터카드 가'),
            ('Ironlight announces custody service', '아이언 라이트가 수탁 서비스를 발표함', '#아이언라이트 가'),
            ('기관 수탁 서비스 발표', '스탠다드 차타드가 수탁 서비스를 발표함', '#스탠다드차타드 가'),
        )
        for title, body, tag in cases:
            with self.subTest(title=title):
                tagged, _ = e._inject_inline_tags(body, {'title': title})
                self.assertIn(tag, tagged)

    def test_spacing_support_preserves_word_boundaries(self):
        body = '마스터 카드사의 자료와 스탠다드 차타드형 모델을 설명함'
        tagged, _ = e._inject_inline_tags(body, {'title': 'Mastercard and Standard Chartered'})
        self.assertNotIn('#마스터카드', tagged)
        self.assertNotIn('#스탠다드차타드', tagged)


if __name__ == '__main__':
    unittest.main()
