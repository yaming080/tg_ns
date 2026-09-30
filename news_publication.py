"""One preparation path for both live sending and previews; never sends itself."""
from news_quality import valid_caption
from news_images import select_image


def prepare_publication(story,build_message,client,model,selector=select_image,event_review=None):
    caption=build_message(story)
    if not caption:
        return {'status':'held','reason':'본문 편집·금지기사·원문검사 통과 실패','caption':'','image':None,'attempts':[]}
    if not valid_caption(caption):
        return {'status':'held','reason':'캡션 길이/링크 검증 실패','caption':caption,'image':None,'attempts':[]}
    if event_review is not None:
        decision = event_review(caption)
        if decision.get('status') not in ('new', 'update'):
            return {'status':'held','reason':'사건 비교 '+decision.get('status','hold')+': '+decision.get('reason','판정 없음'),
                    'caption':caption,'image':None,'attempts':[]}
    picture,attempts=selector(story,caption,client,model)
    if picture is None:
        return {'status':'held','reason':'사용 가능한 검토 통과 이미지 없음','caption':caption,'image':None,'attempts':attempts}
    return {'status':'ready','reason':'본문 및 이미지 검사 통과','caption':caption,'image':picture,'attempts':attempts}
