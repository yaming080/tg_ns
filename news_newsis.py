"""Read Newsis's public article HTML without surrounding recommendations."""
from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit


def article_body(source, url, title):
    def key(value):
        p=urlsplit(value)
        return p.hostname, p.path.rstrip('/')
    if urlsplit(url).hostname not in ('www.newsis.com', 'newsis.com') or not title:
        return ''
    def plain(value):
        return re.sub(r'\s+', ' ', unescape(value)).strip()
    class Body(HTMLParser):
        VOID={'br','img','input','meta','link','hr','source','wbr','area','embed','param','col'}
        def __init__(self):
            super().__init__()
            self.canonical='';self.headline='';self.viewer=0;self.stack=[]
            self.parts=[];self.bodies=[];self.article=False
        def handle_starttag(self,tag,attrs):
            a=dict(attrs); classes=a.get('class','').split()
            if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href','')
            if tag=='meta' and a.get('property')=='og:title':self.headline=a.get('content','')
            parent_blocked=any(blocked for _,blocked in self.stack)
            blocked=parent_blocked or tag in {'script','style','iframe','nav','footer','aside','form','noscript'} or bool(
                re.search(r'article_photo|photojournal|(?:^|[ _-])(?:ad|advert|related|social|share)(?:$|[ _-])',
                          a.get('id','')+' '+a.get('class',''),re.I))
            if tag=='article' and self.viewer and not self.article:
                self.article=True;self.parts=[]
            if self.article and not blocked and tag in {'br','p','h2'}:self.parts.append('\n')
            if tag not in self.VOID:
                self.stack.append((tag,blocked))
                if tag=='div' and 'viewer' in classes:self.viewer=len(self.stack)
        def handle_endtag(self,tag):
            if tag=='article' and self.article:
                self.bodies.append(''.join(self.parts));self.parts=[];self.article=False
            for i in range(len(self.stack)-1,-1,-1):
                if self.stack[i][0]==tag:
                    del self.stack[i:]
                    if self.viewer>len(self.stack):self.viewer=0
                    break
        def handle_data(self,data):
            if self.article and not any(b for _,b in self.stack):self.parts.append(data)
    parser=Body();parser.feed(source);parser.close()
    if key(parser.canonical)!=key(url) or plain(parser.headline)!=plain(title) or len(parser.bodies)!=1 or parser.article:
        return ''
    # Everything after the publisher signature is contact/social furniture.
    value=parser.bodies[0].split('◎공감언론',1)[0]
    text='\n'.join(plain(line) for line in value.splitlines() if plain(line))
    return text[:12000] if len(text)>=180 else ''
