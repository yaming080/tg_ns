"""Reviewable editorial safeguards; no network access or posting side effects."""
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import re


def freshness_reason(story, now=None, max_age_hours=72):
    """Check publication time, never mistake an old date in background for freshness."""
    value = story.get('pub', '')
    if not value:
        return ''  # Missing publication date is handled by the source-based review.
    try:
        try:
            published = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            published = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if published.tzinfo is None:
            return '발행 시각의 시간대 불명확: 검토 필요'
        now = now or datetime.now(timezone.utc)
        if published > now + timedelta(hours=6):
            return '미래 발행 시각: 검토 필요'
        if now - published > timedelta(hours=max_age_hours):
            return '오래된 발행 기사: 새 사실 확인 필요'
    except (ValueError, TypeError, OverflowError):
        return '발행 시각 해석 실패: 검토 필요'
    return ''


def source_promotion_reason(story):
    """Explicit disclosure and conversion copy, including full article evidence."""
    text = '\n'.join(str(story.get(k, '') or '') for k in ('title','desc','article_text'))
    disclosure = r'(?im)^\s*(?:sponsored(?:\s+(?:content|article|post))?|paid\s+(?:content|press release|advertisement)|advertorial|유료\s*광고|협찬\s*(?:기사|콘텐츠))\s*[.:：\-]?'
    conversion = r'(?i)(?:sign\s+up|register|가입|등록).{0,60}(?:referral\s+code|추천인\s*코드)|(?:use|enter|입력).{0,35}(?:referral\s+code|추천인\s*코드)'
    if re.search(disclosure, text):
        return '본문 광고·협찬 표시'
    if re.search(conversion, text):
        return '가입·추천인 유도'
    return ''


def approval_stage_tokens(text):
    if not re.search(r'(?i)licen[cs]e|regulator|approval|승인|인가|라이선스', text):
        return set()
    stages = set()
    if re.search(r'(?i)preliminary|in[- ]principle|provisional|예비\s*승인|원칙적\s*승인', text):
        stages.add('stage_approval_preliminary')
    if re.search(r'(?i)(?:final|full)\s+(?:regulatory\s+)?(?:approval|licen[cs]e)|정식\s*(?:승인|인가|라이선스)|최종\s*승인', text):
        stages.add('stage_approval_final')
    # Both can occur in an article describing progress: its latest explicit stage wins.
    return {'stage_approval_final'} if 'stage_approval_final' in stages else stages


def event_conflicts(cur, old):
    for prefix in ('stage_approval_', 'reference_version_', 'reference_eip_', 'reference_bip_'):
        a = {t for t in cur if t.startswith(prefix)}
        b = {t for t in old if t.startswith(prefix)}
        if a and b and a.isdisjoint(b):
            return True
    return False


def quantity_only_update(cur, old):
    """Quantity changes alone do not earn another post; retain stage/version anchors."""
    # Different loan contracts or vulnerabilities must not become the same
    # event solely because this representation happens to share entity tokens.
    if not {'object_corporate_crypto_purchase', 'object_etf_holdings'} & (cur & old):
        return False
    prefixes = ('amount_', 'count_')
    quantities_a = {t for t in cur if t.startswith(prefixes)}
    quantities_b = {t for t in old if t.startswith(prefixes)}
    core_a, core_b = cur - quantities_a, old - quantities_b
    return bool(
        quantities_a and quantities_b and quantities_a != quantities_b
        and core_a == core_b
        and any(t.startswith('entity_') for t in core_a)
        and any(t.startswith('action_') for t in core_a)
        and any(t.startswith('object_') for t in core_a)
    )


class CaptionParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]; self.stack=[]; self.valid=True
    def handle_starttag(self, tag, attrs):
        if tag != 'a' or self.stack or not dict(attrs).get('href', '').startswith(('http://','https://')):
            self.valid=False
        self.stack.append(tag)
    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop()!=tag:
            self.valid=False
    def handle_data(self, data):
        self.parts.append(data)


def valid_caption(caption):
    """Conservative UTF-16 bound on visible text; preserve complete HTML and tags."""
    parser=CaptionParser()
    try:
        parser.feed(caption); parser.close()
    except Exception:
        return False
    return parser.valid and not parser.stack and len(''.join(parser.parts).encode('utf-16-le'))//2 <= 1024
