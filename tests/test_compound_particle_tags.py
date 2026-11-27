import json
from pathlib import Path
import unittest

import doorinews_editor as editor
import news_review_cache as cache


class CompoundParticleTags(unittest.TestCase):
    def test_real_published_ripple_partnership_sentence(self):
        text = '마스터카드 부사장이 리플과의 협력을 AI 에이전트 금융으로 확대 중이라고 밝힘'
        tagged, _ = editor._inject_inline_tags(text, {'title':'Mastercard expands partnership with Ripple'})
        self.assertIn('#리플 과의 협력', tagged)
        self.assertNotIn('#리플과의', tagged)
        self.assertIn('#마스터카드', tagged)

    def test_bounded_compound_particles_and_only_first_mention(self):
        for suffix in ('과의', '와의', '과는', '와는', '과도', '와도', '으로의', '로의'):
            tagged, _ = editor._inject_inline_tags('리플'+suffix+' 협력 및 리플의 계획을 설명함', {})
            self.assertIn('#리플 '+suffix, tagged)
            self.assertEqual(tagged.count('#리플'), 1)
            self.assertEqual(editor.fix_hashtag_particles('#리플'+suffix+' 협력'), '#리플 '+suffix+' 협력')

    def test_unknown_longer_names_are_not_split(self):
        for text in ('리플렉스가 서비스를 시작함', '리플과의료라는 새 기업', '카드사가 결제를 처리함'):
            tagged, _ = editor._inject_inline_tags(text, {})
            self.assertNotIn('#리플', tagged)
            self.assertNotIn('#카드 ', tagged)

    def test_team_added_upgrade_and_agency_names_are_tagged(self):
        body = '이더리움 핵심 개발자들이 글램스터담 업그레이드의 후디 테스트넷 적용일을 정함'
        tagged, _ = editor._inject_inline_tags(body, {'title':'Ethereum Glamsterdam Hoodi date'})
        for name in ('#이더리움', '#글램스터담', '#후디'):
            self.assertIn(name, tagged)
        tagged, _ = editor._inject_inline_tags('국토안보부 관련 연구기관이 리플과 같은 결제 수단을 분석함', {})
        self.assertIn('#국토안보부', tagged)
        self.assertIn('#리플', tagged)

    def test_format_only_migration_preserves_completed_verdicts(self):
        manifest = json.loads(Path(cache.__file__).with_name('news_cache_compatibility.json').read_text('utf8'))
        old = manifest['format_only_previous_identities'][0]
        with cache.review_session({}, lambda:None, logger=lambda _:None) as store:
            expires = store.clock()+1000
            for kind in ('source_summary', 'event_rejected', 'image_held'):
                scope = {'title':'Japan crypto security group taps SEAL to speed up hack response'}
                key = cache.fingerprint([cache.VERSION,old,kind,scope])
                result = {'reason':'요약 편집 단계의 명시적 제외 판정', 'summary':''}
                store.data.setdefault('content_results_v1',{})[key] = {'result':result,'expires':expires}
                self.assertEqual(cache.content_result(kind,scope), result)
            self.assertTrue(all(x['expires']==expires for x in store.data['content_results_v1'].values()))
