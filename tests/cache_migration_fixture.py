"""Test migration mechanics independently of a production policy release."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import news_review_cache as cache


def install(test):
    temp = tempfile.TemporaryDirectory()
    test.addCleanup(temp.cleanup)
    manifest = {'current_identity': 'test-current', 'previous_identity': 'test-old',
                'previous_identities': ['test-old', 'test-older']}
    (Path(temp.name)/'news_cache_compatibility.json').write_text(json.dumps(manifest), encoding='utf8')
    for target, value in [('__file__', str(Path(temp.name)/'news_review_cache.py')),
                          ('editorial_identity', None)]:
        p = patch.object(cache, target, return_value='test-current') if value is None else patch.object(cache, target, value)
        p.start(); test.addCleanup(p.stop)
    cache.compatible_identity.cache_clear()
    test.addCleanup(cache.compatible_identity.cache_clear)
