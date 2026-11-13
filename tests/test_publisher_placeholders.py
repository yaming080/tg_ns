import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from PIL import Image
import news_images as images
import news_publisher_images as guard
import news_review_cache as cache
from news_publication import prepare_publication

LOGO = (Path(__file__).parent/'fixtures/tokenpost-reporter-logo.png').read_bytes()
LOGO_URL = 'https://f1.tokenpost.kr/2025/07/5y1g67jnxg.png'
STORY = {'title':'FutureBit Apollo III reaches Micro Center stores',
         'url':'https://www.tokenpost.kr/news/cryptocurrency/438017'}


def png(color='orange', size=(640,360)):
    out=io.BytesIO(); Image.new('RGB',size,color).save(out,format='PNG'); return out.getvalue()


class PublisherPlaceholderTests(unittest.TestCase):
    def test_real_reporter_avatar_and_ui_are_not_article_images(self):
        page = '''<article><header><span class="article_byline_writer">
        <img class="article_byline_image" src="/opaque-avatar.png"></span>
        <a class="article_coin_chip"><img src="/btc-icon.png"></a></header>
        <figure><img data-src="/real-product.jpg"></figure>
        <div class="related-news"><section><img src="/other-story.jpg"></section></div>
        <p><img src="/second-product.jpg"></p></article>'''.encode()
        candidates=images.image_candidates(STORY,lambda *args:page)
        self.assertEqual(candidates,['https://www.tokenpost.kr/real-product.jpg',
                                     'https://www.tokenpost.kr/second-product.jpg'])

    def test_opaque_default_url_and_generic_fallbacks_are_blocked(self):
        for url in (LOGO_URL, LOGO_URL+'?width=600',
                    'https://other-cdn.example/2025/07/5y1g67jnxg_th_500.jpg',
                    'https://news.example/images/default-og.png',
                    'https://news.example/no-image.jpg'):
            self.assertTrue(images.publisher_placeholder_url(url),url)
        for url in ('https://media.example/ripple-logo.jpg',
                    'https://f1.tokenpost.kr/2026/11/8umisq99nn_th_860x0.jpg'):
            self.assertFalse(images.publisher_placeholder_url(url),url)

    def test_known_logo_is_blocked_after_resize_or_reencoding(self):
        self.assertTrue(guard.placeholder_bytes(LOGO))
        rgba=Image.open(io.BytesIO(LOGO)).convert('RGBA')
        white=Image.new('RGBA',rgba.size,'white'); white.alpha_composite(rgba)
        for size,fmt in (((384,384),'PNG'),((600,600),'JPEG'),((512,512),'WEBP')):
            out=io.BytesIO();white.convert('RGB').resize(size).save(out,format=fmt)
            data,mime,_,_=images.prepare_image_bytes(out.getvalue())
            self.assertTrue(guard.placeholder_bytes(data),(size,fmt))

    def test_watermark_and_other_subject_images_are_not_blanket_blocked(self):
        picture=Image.new('RGB',(800,450),'orange')
        logo=Image.open(io.BytesIO(LOGO)).convert('RGBA').resize((50,50))
        picture.paste(logo,(740,390),logo)
        out=io.BytesIO();picture.save(out,format='PNG')
        self.assertFalse(guard.placeholder_bytes(out.getvalue()))
        self.assertFalse(guard.placeholder_bytes(png(size=(512,512))))

    def test_logo_cannot_be_overridden_by_ai_approval(self):
        review=Mock(return_value=(True,'incorrectly approved company logo'))
        story=dict(STORY,image_url='https://cdn.example/renamed.png')
        fetch=lambda url,*args:b'<article></article>' if url==story['url'] else LOGO
        picture,attempts=images.select_image(story,'summary',None,'m',fetch,review)
        self.assertIsNone(picture); review.assert_not_called()
        self.assertIn('매체 기본',attempts[0]['reason'])
        client=Mock()
        self.assertFalse(images.review_image(client,'m',story,'summary',LOGO,'image/png')[0])
        client.responses.create.assert_not_called()

    def test_send_boundary_rejects_stale_approved_logo(self):
        for url,data in ((LOGO_URL,png()),('https://cdn.example/renamed.png',LOGO)):
            picture=images.ReviewedImage(url,data,'image/png',512,512,'old wrong approval')
            with patch.object(images.urllib.request,'urlopen') as send:
                self.assertFalse(images.send_reviewed_photo('test','test',picture,'본문',lambda _:None))
                send.assert_not_called()

    def test_no_related_alternative_holds_article_and_replacement_can_pass(self):
        story=dict(STORY,image_url=LOGO_URL)
        page=[b'<article><div class="byline"><img src="/author.png"></div></article>']
        def fetch(url,*args):
            return page[0] if url==story['url'] else png()
        review=Mock(return_value=(True,'verified product'))
        selector=lambda s,c,cl,m:images.select_image(s,c,cl,m,fetch,review)
        result=prepare_publication(story,lambda _:'기사 본문',None,'m',selector)
        self.assertEqual(result['status'],'held'); review.assert_not_called()
        page[0]=b'<article><figure><img src="/new-product.png"></figure></article>'
        result=prepare_publication(story,lambda _:'기사 본문',None,'m',selector)
        self.assertEqual(result['status'],'ready');self.assertEqual(review.call_count,1)

    def test_image_only_release_preserves_semantic_cache_expiry(self):
        manifest=json.loads((Path(cache.__file__).parent/'news_cache_compatibility.json').read_text('utf8'))
        old=manifest['image_only_previous_identities'][0]
        with cache.review_session({},lambda:None,logger=lambda _:None) as store:
            expiry=store.clock()+1000
            for kind in ('source_summary','event_rejected','image_held'):
                scope={'title':'Nomura explores sale of crypto unit Laser Digital','source':'same'}
                key=cache.fingerprint([cache.VERSION,old,kind,scope])
                store.data.setdefault('content_results_v1',{})[key]={'result':{'reason':'unchanged'},'expires':expiry}
                self.assertEqual(cache.content_result(kind,scope)['reason'],'unchanged')
            self.assertTrue(all(v['expires']==expiry for v in store.data['content_results_v1'].values()))


if __name__=='__main__':unittest.main()
