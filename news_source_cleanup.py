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
