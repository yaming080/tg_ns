"""Remove explicit page furniture, preserving article facts and paragraph order."""
from html.parser import HTMLParser


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
    parser = _PageText()
    try:
        parser.feed(source)
        parser.close()
        # Malformed navigation must not silently swallow the entire story.
        return source if parser.blocked else ''.join(parser.parts)
    except Exception:
        return source
