"""One preparation path for both live sending and previews; never sends itself."""
from news_quality import valid_caption
from news_images import select_image
from news_review_cache import content_result, fingerprint, request_options, record_content_reuse


def prepare_publication(story,build_message,client,model,selector=select_image,event_review=None):
    caption=build_message(story)
    if not caption:
        return {'status':'held','reason':story.get('_preparation_reason') or '본문 편집·금지기사·원문검사 통과 실패','caption':'','image':None,'attempts':[]}
    if not valid_caption(caption):
        return {'status':'held','reason':'캡션 길이/링크 검증 실패','caption':caption,'image':None,'attempts':[]}
    scope = {'url': story.get('url', ''), 'title': story.get('title', ''),
             'source': story.get('_review_source_sha256', ''), 'published': str(story.get('pub', '')),
             'caption': fingerprint(caption), 'model': model, 'options': request_options(model)}
    # Only a previously image-held candidate takes this path. Fetch candidates
    # and bytes again: a replacement image may make the article publishable.
    retry_image_first = content_result('image_held', scope) is not None
    picture, attempts = None, []
    if retry_image_first:
        picture, attempts = selector(story, caption, client, model)
        if picture is None:
            record_content_reuse('image_held', model, '이미지 미통과 지속: 사건 유료 재검색 생략')
            return {'status':'held','reason':'사용 가능한 검토 통과 이미지 없음 (사건 재검색 생략)',
                    'caption':caption,'image':None,'attempts':attempts}
    if event_review is not None:
        decision = event_review(caption)
        if decision.get('status') not in ('new', 'update'):
            return {'status':'held','reason':'사건 비교 '+decision.get('status','hold')+': '+decision.get('reason','판정 없음'),
                    'caption':caption,'image':None,'attempts':[]}
    if not retry_image_first:
        picture,attempts=selector(story,caption,client,model)
    if picture is None:
        content_result('image_held', scope, {'reason':'사용 가능한 검토 통과 이미지 없음'})
        return {'status':'held','reason':'사용 가능한 검토 통과 이미지 없음','caption':caption,'image':None,'attempts':attempts}
    return {'status':'ready','reason':'본문 및 이미지 검사 통과','caption':caption,'image':picture,'attempts':attempts}
