"""Remove explicit page furniture, preserving article facts and paragraph order."""
from html.parser import HTMLParser
import json
import re


def page_publication_date(source):
    """Only explicit publisher metadata, never dates in tweets/body text."""
    class Metadata(HTMLParser):
        def __init__(self):
            super().__init__()
            self.value = ''
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'meta' and (attrs.get('property') or attrs.get('name')) in (
                    'article:published_time', 'datePublished'):
                self.value = attrs.get('content', '')
    parser = Metadata()
    parser.feed(source)
    if parser.value:
        return parser.value
    def find(node):
        if isinstance(node, list):
            return next((date for item in node if (date := find(item))), '')
        if isinstance(node, dict):
            kind = node.get('@type', '')
            if any(t in (kind if isinstance(kind, list) else [kind]) for t in ('Article', 'NewsArticle', 'BlogPosting')):
                return str(node.get('datePublished', ''))
            return find(node.get('@graph', []))
        return ''
    for block in re.findall(r'<script\b[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>', source, re.I | re.S):
        try:
            date = find(json.loads(block))
            if date:
                return date
        except (ValueError, TypeError):
            continue
    return ''


class _PageText(HTMLParser):
    DROP = {'nav', 'footer', 'form', 'script', 'style', 'noscript'}
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.blocked = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if self.blocked or tag in self.DROP:
            if tag not in self.VOID:
                self.blocked.append(tag)
        else:
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.blocked:
            if tag in self.blocked:
                index = len(self.blocked)-1-self.blocked[::-1].index(tag)
                del self.blocked[index:]
        elif tag not in self.DROP:
            self.parts.append('</'+tag+'>')

    def handle_startendtag(self, tag, attrs):
        if not self.blocked and tag not in self.DROP:
            self.parts.append(self.get_starttag_text())

    def handle_data(self, data):
        if not self.blocked:
            self.parts.append(data)

    def handle_entityref(self, name):
        self.handle_data('&'+name+';')

    def handle_charref(self, name):
        self.handle_data('&#'+name+';')


def strip_page_furniture(source):
    # Remove only publisher follow-us embeds. Actual quoted reporting is evidence.
    source = re.sub(r'<blockquote\b[^>]*>.*?</blockquote>',
                    lambda m: '' if re.search(r'we are on X,?\s*follow us|follow us to connect', m[0], re.I)
                    else m[0], source, flags=re.I | re.S)
    parser = _PageText()
    try:
        parser.feed(source)
        parser.close()
        # Malformed navigation must not silently swallow the entire story.
        return source if parser.blocked else ''.join(parser.parts)
    except Exception:
        return source


def extract_article_text(source, url='', title=''):
    """Prefer this article's structured body; don't select a related-news card.

    Reads only content already delivered by the publisher. No paywall bypass,
    external fetch, or inferred facts. Empty/short results remain reviewable.
    """
    from html import unescape
    from urllib.parse import urlsplit
    def key(value):
        if isinstance(value, dict):
            value = value.get('@id', '') or value.get('url', '')
        p = urlsplit(str(value or ''))
        return p.netloc.lower().removeprefix('www.') + p.path.rstrip('/')
    def plain(value):
        value = re.sub(r'<[^>]+>', ' ', str(value or ''))
        return re.sub(r'\s+', ' ', unescape(value)).strip()
    candidates = []
    def visit(node):
        if isinstance(node, list):
            for child in node: visit(child)
        elif isinstance(node, dict):
            kind = node.get('@type', [])
            kind = [kind] if isinstance(kind, str) else kind
            if any(t in kind for t in ('Article', 'NewsArticle', 'BlogPosting')):
                identity = node.get('url') or node.get('mainEntityOfPage')
                body = node.get('articleBody')
                headline = plain(node.get('headline'))
                same_article = key(identity) == key(url) if identity else (not title or headline == plain(title))
                if isinstance(body, str) and same_article:
                    candidates.append((plain(node.get('headline')), plain(body)))
            visit(node.get('@graph', []))
    for block in re.findall(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', source, re.I | re.S):
        try: visit(json.loads(block))
        except (ValueError, TypeError): continue
    matching = [body for heading, body in candidates if title and plain(title) == heading]
    bodies = matching or ([candidates[0][1]] if len(candidates) == 1 else [])
    if bodies and len(max(bodies, key=len)) >= 180:
        return max(bodies, key=len)[:12000]

    class Paragraphs(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack = []; self.groups = []; self.paragraph = None; self.heading = None
            self.all_paragraphs = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'article':
                group = {'paragraphs': [], 'headings': []}
                self.groups.append(group); self.stack.append(group)
            if tag == 'p': self.paragraph = []
            if tag == 'h1': self.heading = []
        def handle_data(self, data):
            if self.paragraph is not None: self.paragraph.append(data)
            if self.heading is not None: self.heading.append(data)
        def handle_endtag(self, tag):
            if tag == 'p' and self.paragraph is not None:
                text = plain(' '.join(self.paragraph)); self.paragraph = None
                if len(text) >= 20:
                    self.all_paragraphs.append(text)
                    for group in self.stack: group['paragraphs'].append(text)
            if tag == 'h1' and self.heading is not None:
                text = plain(' '.join(self.heading)); self.heading = None
                for group in self.stack: group['headings'].append(text)
            if tag == 'article' and self.stack: self.stack.pop()
    parser = Paragraphs()
    parser.feed(strip_page_furniture(source)); parser.close()
    exact = [g for g in parser.groups if title and plain(title) in g['headings']]
    groups = exact or ([g for g in parser.groups if g['headings']] if not title else [])
    if not groups and len(parser.groups) == 1 and not parser.groups[0]['headings']:
        groups = parser.groups
    if groups:
        paragraphs = max(groups, key=lambda g: sum(map(len, g['paragraphs'])))['paragraphs']
    elif parser.groups:
        return ''  # Multiple unrelated cards are not evidence for this story.
    else:
        paragraphs = parser.all_paragraphs
    return '\n'.join(dict.fromkeys(paragraphs))[:12000]
