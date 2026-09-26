import ast
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import news_images as images
from news_publication import prepare_publication
from preview_news import save_preview


def png(width=640,height=360):
    output=io.BytesIO()
    Image.new('RGB',(width,height),(40,90,130)).save(output,format='PNG')
    return output.getvalue()


def accepted_response():
    return json.dumps({'approved':True,'reason':'관련 삽화','checks':dict.fromkeys(images.IMAGE_CHECKS,True)})


class ImagePublicationTests(unittest.TestCase):
    def test_live_main_cannot_send_held_article_or_record_it_as_posted(self):
        source=(Path(__file__).resolve().parents[1]/'doorinews_bot.py').read_text(encoding='utf-8')
        main=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='main'][-1]
        story={'title':'기사','url':'https://example.com/article'}
        for status in ('held','ready'):
            with self.subTest(status=status):
                sender=Mock(return_value=True);register=Mock()
                prepared={'status':status,'reason':'검사 결과','attempts':[],'caption':'본문','image':object()}
                ns={'log':Mock(),'load_state':lambda p:{'posted':{}},'STATE_FILE':'unused',
                    'prune_posted_older_than':lambda p,days:p,'save_state':Mock(),
                    'FEEDS':[('feed','url',False)],'_feed_unpack_final':lambda f:f,
                    'fetch_rss':lambda *a,**k:[dict(story)],'MAX_ITEMS_PER_FEED':1,
                    'matches_keywords':lambda *a:True,'PORTFOLIO_COINS':[],'ECON_KEYWORDS':[],'KOREAN_KEYWORDS':[],
                    'build_story_signature':lambda s:'','build_canonical_topic_key':lambda s:'',
                    'normalize_for_duplicate':lambda t:t,'is_canonical_duplicate':lambda *a:False,
                    'is_duplicate':lambda *a:False,'is_semantically_duplicate':lambda *a:False,
                    'INITIAL_RUN':False,'POST_ENABLED':True,'DRY_RUN_RECORD':False,
                    'prepare_publication':Mock(return_value=prepared),'build_message':Mock(),
                    'openai_client':None,'OPENAI_MODEL':'m','send_reviewed_photo':sender,
                    'TELEGRAM_BOT_TOKEN':'t','TELEGRAM_CHANNEL_ID':'c','update_posted':register,
                    'time':SimpleNamespace(sleep=lambda *a:None)}
                exec(compile(ast.Module(body=[main],type_ignores=[]),'<live main>','exec'),ns)
                ns['main']()
                self.assertEqual(sender.call_count,1 if status=='ready' else 0)
                self.assertEqual(register.call_count,1 if status=='ready' else 0)

    def test_real_image_header_and_dimensions(self):
        self.assertEqual(images.inspect_image(png()),('image/png',640,360))

    def test_tiny_banner_html_and_truncated_images_are_rejected(self):
        for data in (png(40,40),png(1800,200),b'<html>Not an image</html>',png()[:100]):
            with self.subTest(size=len(data)),self.assertRaises(Exception):images.inspect_image(data)

    def test_oversized_image_is_rejected(self):
        with self.assertRaises(ValueError):images.inspect_image(b'x'*(images.MAX_IMAGE_BYTES+1))

    def test_private_urls_and_credentials_are_rejected(self):
        for url in ('file:///tmp/a','http://user:pass@example.com/a','https://example.com:1234/a'):
            with self.assertRaises(ValueError):images.public_url(url)
        with patch.object(socket,'getaddrinfo',return_value=[(None,None,None,None,('127.0.0.1',80))]):
            with self.assertRaises(ValueError):images.public_url('http://localhost/a')

    def test_image_review_receives_bytes_not_refetchable_url(self):
        client=Mock();client.responses.create.return_value=SimpleNamespace(output_text=accepted_response())
        accepted,reason=images.review_image(client,'existing-model',{'title':'story'},'summary',png(),'image/png')
        self.assertTrue(accepted)
        content=client.responses.create.call_args.kwargs['input'][0]['content']
        self.assertTrue(content[1]['image_url'].startswith('data:image/png;base64,'))

    def test_uncertain_missing_or_failed_checks_are_rejected(self):
        responses=['not json','[]','{"approved":true}',accepted_response().replace('"clear": true','"clear": "true"')]
        for response in responses:
            client=Mock();client.responses.create.return_value=SimpleNamespace(output_text=response)
            self.assertFalse(images.review_image(client,'m',{},'caption',png(),'image/png')[0])
        self.assertFalse(images.review_image(None,'m',{},'caption',png(),'image/png')[0])

    def test_api_failure_is_rejected(self):
        client=Mock();client.responses.create.side_effect=RuntimeError('unavailable')
        self.assertFalse(images.review_image(client,'m',{},'caption',png(),'image/png')[0])

    def test_source_candidates_exclude_unrelated_page_images(self):
        page=b'<img src="/ad.png"><meta property="og:image" content="/cover.png"><article><img src="/second.png"></article>'
        story={'url':'https://example.com/news','image_url':'https://example.com/rss.png'}
        self.assertEqual(images.image_candidates(story,lambda *args:page),['https://example.com/rss.png','https://example.com/cover.png','https://example.com/second.png'])

    def test_rejected_cover_falls_back_to_another_source_image(self):
        data=png(); page=b'<meta property="og:image" content="/second.png">'
        fetch=lambda url,*args:page if url.endswith('/news') else data
        review=Mock(side_effect=[(False,'광고 배너'),(True,'관련 사진')])
        picture,attempts=images.select_image({'url':'https://example.com/news','image_url':'https://example.com/first.png'},'summary',None,'m',fetch,review)
        self.assertEqual(picture.source_url,'https://example.com/second.png')
        self.assertEqual(picture.data,data)
        self.assertEqual(len(attempts),2)

    def test_no_accepted_image_means_no_ready_post(self):
        selector=Mock(return_value=(None,[{'accepted':False,'reason':'관련 없음'}]))
        result=prepare_publication({},lambda story:'본문',None,'m',selector)
        self.assertEqual(result['status'],'held')

    def test_disallowed_article_never_fetches_an_image(self):
        selector=Mock()
        result=prepare_publication({},lambda story:'',None,'m',selector)
        self.assertEqual(result['status'],'held');selector.assert_not_called()

    def test_invalid_caption_never_fetches_an_image(self):
        selector=Mock()
        result=prepare_publication({},lambda story:'가'*1025,None,'m',selector)
        self.assertEqual(result['status'],'held');selector.assert_not_called()

    def test_delivery_uploads_exact_reviewed_bytes(self):
        data=png();picture=images.ReviewedImage('https://example.com/image',data,'image/png',640,360,'통과')
        response=Mock();response.read.return_value=b'{"ok":true}'
        manager=Mock();manager.__enter__=Mock(return_value=response);manager.__exit__=Mock(return_value=False)
        with patch.object(images.urllib.request,'urlopen',return_value=manager) as request:
            self.assertTrue(images.send_reviewed_photo('test-token','test-channel',picture,'정상 본문'))
            payload=request.call_args.args[0].data
            self.assertIn(data,payload)
            self.assertNotIn(b'https://example.com/image',payload)

    def test_delivery_rejects_unreviewed_image_and_bad_caption(self):
        with patch.object(images.urllib.request,'urlopen') as request:
            self.assertFalse(images.send_reviewed_photo('t','c','https://example.com/image','caption'))
            request.assert_not_called()

    def test_preview_is_escaped_and_preserves_reviewed_image(self):
        data=png();picture=images.ReviewedImage('https://example.com/img',data,'image/png',640,360,'관련')
        result={'status':'ready','reason':'통과','caption':'본문\n<a href="https://example.com">출처</a>', 'image':picture,'attempts':[]}
        with tempfile.TemporaryDirectory() as directory:
            save_preview([({'title':'<script>alert(1)</script>'},result)],directory)
            text=(Path(directory)/'index.html').read_text(encoding='utf-8')
            self.assertNotIn('<script>',text)
            self.assertIn('검사 통과 · 미발송',text)
            self.assertEqual((Path(directory)/'image-1.png').read_bytes(),data)

    def test_full_editor_to_image_path_uses_three_reviews_and_never_sends(self):
        import doorinews_editor as editor
        story={'title':'Ripple receives final approval for XRP payments license in Singapore',
               'desc':'Ripple received final approval for an XRP payments license in Singapore.',
               'url':'https://example.com/news','image_url':'https://example.com/image.png'}
        verdict=json.dumps({'publish':True,'reason':'원문 일치','checks':dict.fromkeys(('faithful','conditions_preserved','allowed_category','new_substantive_fact','source_sufficient'),True)})
        client=Mock();client.responses.create.return_value=SimpleNamespace(output_text=accepted_response())
        selector=lambda s,c,cl,m:images.select_image(s,c,cl,m,fetch=lambda *args:png())
        with patch.object(editor,'_RUNTIME',{}),patch.object(editor,'_call_openai',side_effect=['리플이 XRP 결제 서비스 정식 라이선스를 취득했다고 밝힘',verdict]) as text_model,patch.object(images.urllib.request,'urlopen') as sender:
            result=prepare_publication(story,editor.build_message,client,'existing-model',selector)
            self.assertEqual(result['status'],'ready')
            self.assertEqual(text_model.call_count,2)
            self.assertEqual(client.responses.create.call_count,1)
            sender.assert_not_called()


if __name__=='__main__':unittest.main()
