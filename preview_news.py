"""Generate the real preparation result without sending or changing news state."""
import argparse
import html
import json
import os
from pathlib import Path


def save_preview(results,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    cards=[]; records=[]
    for index,(story,result) in enumerate(results,1):
        picture=result['image']; picture_html=''; filename=''
        if picture:
            filename=f'image-{index}.'+('jpg' if picture.mime=='image/jpeg' else 'png')
            (output/filename).write_bytes(picture.data)
            picture_html=f'<img src="{filename}" alt="검토 통과한 기사 이미지">'
        # Escape all generated text. Telegram HTML is shown literally, not executed.
        caption=html.escape(result['caption'])
        from news_quality import CaptionParser
        if result['caption']:
            parser=CaptionParser();parser.feed(result['caption'])
            caption=html.escape(''.join(parser.parts))
        cards.append(f'''<article><div class="status {result['status']}">{'검사 통과 · 미발송' if result['status']=='ready' else '게시 보류'}</div>
<h2>{html.escape(str(story.get('title','')))}</h2>{picture_html}<p class="caption">{caption}</p>
<p class="reason">{html.escape(result['reason'])}</p></article>''')
        records.append({'title':story.get('title',''),'url':story.get('url',''),'status':result['status'],
                        'reason':result['reason'],'caption':result['caption'],'image_file':filename,
                        'image_source':picture.source_url if picture else '', 'image_attempts':result['attempts']})
    doc='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>도리뉴스 게시 전 미리보기</title><style>
body{font-family:system-ui,sans-serif;background:#edf2f6;color:#172b40;margin:0;padding:32px}main{max-width:1120px;margin:auto}
h1{font-size:26px}header p{color:#526477}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px}
article{background:white;border-radius:16px;padding:20px;box-shadow:0 3px 16px #14273b10;overflow:hidden}h2{font-size:15px;color:#596579}
img{width:100%;height:auto;border-radius:10px}.caption{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7;font-size:16px}
.status{font-weight:700;font-size:13px;color:#ac5600}.ready{color:#087b57}.reason{border-top:1px solid #eee;padding-top:12px;font-size:13px}
</style><main><header><h1>도리뉴스 게시 전 미리보기</h1><p>실제 전송 경로와 같은 본문·이미지 검사 결과입니다. Telegram 발송과 게시 이력 변경은 하지 않습니다.</p></header><div class="grid">'''+''.join(cards)+'</div></main></html>'
    (output/'index.html').write_text(doc,encoding='utf-8')
    (output/'results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,help='RSS story objects as a JSON array')
    parser.add_argument('--output',default='preview')
    parser.add_argument('--limit',type=int,default=5)
    args=parser.parse_args()
    stories=json.loads(Path(args.input).read_text(encoding='utf-8'))
    if not isinstance(stories,list) or not all(isinstance(s,dict) for s in stories):
        parser.error('입력은 기사 객체의 JSON 배열이어야 합니다')
    stories=stories[:max(0,min(args.limit,20))]
    results=[]
    if not os.environ.get('OPENAI_API_KEY'):
        for story in stories:
            results.append((story,{'status':'held','reason':'API 키 미설정: 실제 본문·이미지 생성 검증 미실시',
                                  'caption':'','image':None,'attempts':[]}))
    else:
        import doorinews_bot as bot
        from news_publication import prepare_publication
        # Do not call bot.main(), load/save state, or any send function.
        for story in stories:
            try:
                result=prepare_publication(story,bot.build_message,bot.openai_client,bot.OPENAI_MODEL)
            except Exception as exc:
                result={'status':'held','reason':f'준비 실패: {type(exc).__name__}','caption':'','image':None,'attempts':[]}
            results.append((story,result))
    save_preview(results,args.output)
    print(f'{len(results)}개 검사 결과 저장: {Path(args.output)/"index.html"} (미발송)')


if __name__=='__main__':main()
