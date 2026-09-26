"""New publisher feeds: first successful fetch is a silent baseline."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import xml.etree.ElementTree as ET

NEW_FEEDS = (
    ('블루밍비트', 'https://bloomingbit.io/rss.xml'),
    ('타임스테이블로이드', 'https://timestabloid.com/feed/'),
    ('비트코인닷컴', 'https://news.bitcoin.com/feed/'),
    ('블록체인리포터', 'https://blockchainreporter.net/feed/'),
    ('이투데이', 'https://rss.etoday.co.kr/eto/etoday_news_all.xml'),
)


def timestamp(value):
    try:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def url_key(value):
    parts = urlsplit(value.strip())
    if parts.scheme not in ('https', 'http') or not parts.netloc:
        return ''
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith('utm_')]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/'), urlencode(query), ''))


def parse_feed(text):
    root = ET.fromstring(text)
    if root.tag != 'rss':
        raise ValueError('RSS 형식 아님')
    stories = []
    # Read the whole feed, not only the six newest items. Otherwise older
    # entries could rotate into the next response and look like new stories.
    for item in root.findall('./channel/item'):
        title = unescape((item.findtext('title') or '').strip())
        link = (item.findtext('link') or '').strip()
        if not title or not url_key(link):
            continue
        desc = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', unescape(item.findtext('description') or ''))).strip()
        image = ''
        for child in item:
            if child.tag.endswith(('}content', '}thumbnail')) or (child.tag == 'enclosure' and child.attrib.get('type', '').startswith('image/')):
                candidate = child.attrib.get('url', '')
                if candidate.startswith(('https://', 'http://')):
                    image = candidate
                    break
        stories.append({'title': title, 'url': link, 'desc': desc,
                        'pub': (item.findtext('pubDate') or '').strip(), 'image_url': image})
    return stories


def after_baseline(state, feed_url, stories, now=None):
    """Return only dated stories published after this source was activated.

    Empty/error responses never initialize a source. Baseline URLs persist
    separately from the rolling posted history, so edited dates cannot revive
    old baseline articles. This state is not a record of Telegram sends.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('timezone required')
    sources = state.setdefault('source_baselines', {})
    if not isinstance(sources, dict):
        raise ValueError('출처 기준 이력 손상')
    record = sources.get(feed_url)
    if record is None:
        if stories:
            sources[feed_url] = {'activated_at': now.isoformat(),
                                 'baseline_urls': sorted({url_key(s['url']) for s in stories})}
        return []
    if not isinstance(record, dict) or not isinstance(record.get('baseline_urls'), list):
        raise ValueError('출처 기준 이력 손상')
    cutoff = timestamp(record.get('activated_at'))
    if cutoff is None:
        raise ValueError('출처 시작 시각 손상')
    baseline = set(record['baseline_urls'])
    eligible = []
    seen = set()
    for story in stories:
        key = url_key(story['url'])
        published = timestamp(story.get('pub'))
        if key in baseline or key in seen or not published or not cutoff < published <= now:
            continue
        seen.add(key)
        eligible.append(story)
    return eligible


def collect_new_sources(state, fetch, save, log=print, now=None):
    collected = []
    for name, feed_url in NEW_FEEDS:
        try:
            stories = parse_feed(fetch(feed_url))
        except Exception as exc:
            log(f'{name}: 수집 실패, 발송 없음 ({type(exc).__name__})')
            continue
        initialized = feed_url in state.get('source_baselines', {})
        candidates = after_baseline(state, feed_url, stories, now)
        # Persist the cutoff before a candidate can enter the sending pipeline.
        # Storage/validation errors propagate and stop the run.
        save(state)
        log(f'{name}: {len(stories)}개 확인 / ' +
            (f'새 기사 {len(candidates)}개 심사' if initialized else '최초 기준 저장, 발송 없음'))
        collected.extend(candidates)
    return collected
