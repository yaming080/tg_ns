"""Free candidate ordering only; visual/byte checks still decide acceptance."""
import re
from urllib.parse import unquote

BRANDS = (
    (r'UniCredit|유니크레디?트|유니크레딧', r'unicredit|유니크레딧|유니크레디트'),
    (r'Ethena|에테나', r'ethena|\bena\b|에테나'),
    (r'\bUBS\b|유비에스', r'\bubs\b|유비에스'),
    (r'\bH100\b', r'\bh100\b'),
    (r'Two\s*Prime|투프라임', r'two[\W_]*prime|twoprime|투프라임'),
    (r'Binance|바이낸스', r'binance|바이낸스'),
)


def prioritize(urls, title, descriptions):
    """Use the earliest named subject, not an incidental partner/underlying."""
    matches = [(m.start(), asset) for pattern, asset in BRANDS
               if (m := re.search(pattern, title, re.I))]
    if not matches:
        return urls
    subject = min(matches, key=lambda pair: pair[0])[1]
    def rank(url):
        evidence = unquote(url) + ' ' + descriptions.get(url, '')
        # Metadata is a ranking hint, never approval or a license to add images.
        return 0 if re.search(subject, evidence, re.I) else 1
    return sorted(urls, key=rank)
