"""Deterministic guards for verified publisher artwork, independent of AI votes."""
import hashlib
import io
import re
from urllib.parse import unquote, urlsplit

from PIL import Image

# TokenPost's reporter avatar, verified on article 438017 (2026-11-14).
# The opaque filename contains no "logo" keyword. Keep a byte and visual guard
# as CDN hostnames, encodings and resized copies can change.
TP_SHA256 = '3ba682fd6dab680a8743ec6dea7ea08d3184ee13e526bec425588512e99fcbd8'
TP_DHASH = int('5f04b86261d9ce3c981ea0e68366076f237d933ab33291b6c9c46619b8e25f04', 16)
TP_AHASH = int('f81fe007c003806181f907e81fe81ef807f007e0076087018001c003e007f81f', 16)
TP_COLOR = (124, 181, 204)


def placeholder_url(url):
    parsed = urlsplit(str(url or ''))
    path = unquote(parsed.path).lower()
    if re.search(r'(?:^|/)5y1g67jnxg(?:[_.-]|$)', path):
        return True
    # Explicit fallback artwork; a real subject logo such as ripple-logo.png
    # is not a placeholder solely because the word "logo" appears in its URL.
    if re.search(r'(?:^|[/_.-])(?:no[_-]?image|placeholder|default[_-]?(?:og|image|thumb)|og[_-]?default)(?:[/_.-]|$)', path):
        return True
    host = (parsed.hostname or '').lower()
    return ((host == 'tokenpost.kr' or host.endswith('.tokenpost.kr'))
            and bool(re.search(r'(?:^|[/_.-])(?:logo|favicon)(?:[/_.-]|$)|/assets/icons/', path)))


def ancillary_image_context(attrs):
    value = ' '.join(str(attrs.get(k, '') or '') for k in ('class', 'id', 'role', 'itemprop', 'alt'))
    return bool(re.search(
        r'(?:^|[\s_-])(?:byline|author|avatar|profile|social|share|sharing|follow|subscribe|newsletter|'
        r'related|recommendations?|advert(?:isement)?|banner|masthead)(?:$|[\s_-])|'
        r'article[_-]coin|publisher[_-]logo|site[_-]logo|기자\s*프로필|매체\s*로고', value, re.I))


def placeholder_bytes(data):
    """Whole-image fingerprint only: a small watermark must not block a photo."""
    if hashlib.sha256(data).hexdigest() == TP_SHA256:
        return True
    try:
        with Image.open(io.BytesIO(data)) as picture:
            w, h = picture.size
            if w < 180 or h < 180 or w * h > 25_000_000 or not .95 <= w / h <= 1.05:
                return False
            rgba = picture.convert('RGBA')
            background = Image.new('RGBA', rgba.size, 'white')
            background.alpha_composite(rgba)
            rgb = background.convert('RGB')
            color = rgb.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
            if max(abs(a-b) for a, b in zip(color, TP_COLOR)) > 12:
                return False
            gray = rgb.convert('L').resize((17, 16), Image.Resampling.LANCZOS)
            values = [gray.getpixel((x, y)) for y in range(16) for x in range(17)]
            dhash = 0
            for y in range(16):
                for x in range(16):
                    dhash = (dhash << 1) | (values[y*17+x] > values[y*17+x+1])
            if (dhash ^ TP_DHASH).bit_count() > 8:
                return False
            gray = rgb.convert('L').resize((16, 16), Image.Resampling.LANCZOS)
            values = [gray.getpixel((x, y)) for y in range(16) for x in range(16)]
            mean = sum(values) / len(values)
            ahash = 0
            for value in values:
                ahash = (ahash << 1) | (value >= mean)
            return (ahash ^ TP_AHASH).bit_count() <= 8
    except (OSError, ValueError, Image.DecompressionBombError):
        return False  # Ordinary image validation still rejects invalid data.
