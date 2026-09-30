"""Deleted cross-source reports and empty legacy signatures must stay deduped."""
from datetime import datetime, timezone
import unittest
from unittest.mock import patch
import doorinews_editor as e
from news_quality import manual_post_reason

EN = 'Morgan Stanley Launches Digital Asset Lab to Explore Stablecoins and Tokenization'
KO = '모건스탠리, 디지털자산 연구소 신설…스테이블코인·토큰화·디파이 실험'
ES = 'Spain’s Tax Agency Clarifies Form 721 Rules for Crypto Wallets'
ES_OLD = 'Spain says self-custody crypto does not need Form 721 reporting'


def story(title, **kw):
    return dict(title=title, pub='2026-09-30T00:00:00Z', **kw)


class CrossSourceConfirmedEvents(unittest.TestCase):
    def test_exact_deleted_urls_stay_blocked_even_without_scheme(self):
        urls = ('bloomingbit.io/feed/news/121234',
                'coinedition.com/spains-tax-agency-clarifies-form-721-rules-for-crypto-wallets',
                'u.today/morgan-stanley-launches-digital-asset-lab-to-explore-stablecoins-and-tokenization')
        for url in urls:
            for variant in (url, 'https://'+url+'/?utm_source=rss'):
                self.assertIn('중복 삭제', manual_post_reason(story('다른 제목', url=variant)))

    def test_bilingual_lab_signatures_are_nonempty_and_same_event(self):
        a, b = [e.build_story_signature(story(t)) for t in (EN, KO)]
        self.assertTrue(a); self.assertTrue(b)
        self.assertTrue(e._same_event(a, b))
        self.assertTrue(e._same_event(b, a))

    def test_empty_legacy_state_rebuilds_from_titles(self):
        for title, old in ((KO, EN), (EN, KO), (ES, ES_OLD), (ES_OLD, ES)):
            self.assertTrue(e.is_semantically_duplicate(story(title), [''], [old]))

    def test_old_partial_signature_does_not_require_state_reset(self):
        legacy = 'action_launch | entity_assetlab | entity_모건스탠리 | entity_토큰화'
        self.assertTrue(e.is_semantically_duplicate(story(KO), [legacy], [EN]))

    def test_same_batch_cross_language_duplicate(self):
        keys = {e.build_canonical_topic_key(story(EN))}
        self.assertTrue(e.is_canonical_duplicate(e.build_canonical_topic_key(story(KO)), keys))

    def test_other_bank_and_different_project_not_duplicates(self):
        base = e.build_story_signature(story(EN))
        for title in ('BlackRock launches digital asset lab to explore tokenization',
                      'Morgan Stanley launches tokenized money market fund',
                      'Morgan Stanley opens digital asset lab partnership with Citi'):
            self.assertFalse(e._same_event(base, e.build_story_signature(story(title))), title)
        citi_a = 'Citigroup and Coinbase partner on institutional stablecoin payments'
        citi_b = 'Citi launches tokenized deposit service in Japan and UAE'
        self.assertFalse(e.is_semantically_duplicate(story(citi_b), [], [citi_a]))

    def test_material_followups_and_different_regions_remain_separate(self):
        for title in ('Morgan Stanley expands digital asset lab',
                      'Morgan Stanley closes digital asset lab',
                      'Morgan Stanley publishes digital asset lab results',
                      'Spain changes Form 721 reporting rules',
                      'Spain extends Form 721 reporting deadline',
                      '스페인, 양식 721 신고 규정 개정'):
            prior = EN if 'Morgan' in title else ES
            self.assertFalse(e.is_semantically_duplicate(story(title), [], [prior]), title)
        a = e.build_story_signature(story('Morgan Stanley opens digital asset lab in Japan'))
        b = e.build_story_signature(story('Morgan Stanley opens digital asset lab in Korea'))
        self.assertFalse(e._same_event(a, b))



if __name__ == '__main__':
    unittest.main()
