# 구글 / 스페이스X / 엔비디아 / AI 태그 보강 패치
# 적용 대상: doorinews_bot.py
# 목적:
# 1) 본문 태그에 #구글 #스페이스X #엔비디아 #AI 안정적으로 붙이기
# 2) footer 영어 태그에 #Google #SpaceX #NVIDIA #AI 자동 대응
# 3) 본문에 한글 태그가 있거나 원문/요약에 엔티티가 감지되면 footer 영어 태그도 함께 붙이기

# --------------------------------------------------
# 1. INLINE_KO_ENTITY_TAGS에 아래 항목이 없으면 추가
# --------------------------------------------------
INLINE_KO_ENTITY_TAGS = [
    ('구글', [r'\bgoogle\b', r'구글']),
    ('스페이스X', [r'\bspacex\b', r'스페이스x', r'스페이스X']),
    ('엔비디아', [r'\bnvidia\b', r'엔비디아']),
    ('AI', [r'\bai\b', r'인공지능', r'AI']),
    # ... 기존 항목들 유지
]

# --------------------------------------------------
# 2. FOOTER_EN_TAGS_MAP에 아래 항목이 없으면 추가
# --------------------------------------------------
FOOTER_EN_TAGS_MAP = {
    '구글': '#Google',
    '스페이스X': '#SpaceX',
    '엔비디아': '#NVIDIA',
    'AI': '#AI',
    # ... 기존 항목들 유지
}

# --------------------------------------------------
# 3. _normalize_footer_tags() 매핑 보강
# 없으면 아래 매핑만 추가
# --------------------------------------------------
def _normalize_footer_tags(tags):
    if not tags:
        return []

    mapping = {
        '#USA': '#US',
        '#UnitedStates': '#US',
        '#America': '#US',
        '#Michael Saylor': '#MichaelSaylor',
        '#Wall Street': '#WallStreet',
        '#Black Rock': '#BlackRock',
        '#Google AI': '#Google',
        '#GoogleCloud': '#Google',
        '#Nvidia': '#NVIDIA',
        '#Space X': '#SpaceX',
    }

    out = []
    seen = set()

    for tag in tags:
        tag = (tag or '').strip()
        if not tag:
            continue
        if not tag.startswith('#'):
            tag = '#' + tag

        tag = mapping.get(tag, tag)
        tag = re.sub(r'\s+', '', tag)

        if tag not in seen:
            out.append(tag)
            seen.add(tag)

    return out

# --------------------------------------------------
# 4. 본문 태그를 footer 영어 태그로 넘기는 함수 확인/보강
# collect_footer_entity_tags(summary, raw_text) 안에 아래 로직이 살아 있어야 함
# --------------------------------------------------
def collect_footer_entity_tags(summary: str, raw_text: str) -> list[str]:
    base = (str(summary or "") + "\\n" + str(raw_text or "")).lower()
    tags = []

    for ko, en in FOOTER_EN_TAGS_MAP.items():
        # 본문에 #구글 같은 한글 태그가 이미 있으면 footer 영어 태그 추가
        if re.search(rf'#{re.escape(ko)}\\b', summary):
            tags.append(en)
            continue

        # 본문 태그가 없더라도 원문/요약에서 엔티티가 감지되면 footer 추가
        for label, patterns in INLINE_KO_ENTITY_TAGS:
            if label != ko:
                continue
            for pat in patterns:
                if re.search(pat, base, re.I):
                    tags.append(en)
                    break

    seen = set()
    out = []
    for t in tags:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out

# --------------------------------------------------
# 5. build_message() 안에서 아래 순서가 살아 있어야 함
# --------------------------------------------------
# raw_text = f"{title}\\n{desc}"
# summary = ensure_inline_entity_tags(summary, raw_text)
# summary = fix_split_person_tags(summary)
# summary = fix_korean_hashtag_particles(summary)
# summary = cleanup_summary_before_send(summary)
#
# footer_tags = build_footer_tags(...)  # 기존 footer 생성
# extra_footer_tags = collect_footer_entity_tags(summary, raw_text)
# for tag in extra_footer_tags:
#     if tag not in footer_tags:
#         footer_tags.append(tag)
# footer_tags = _normalize_footer_tags(footer_tags)

# --------------------------------------------------
# 6. 이 기사에서 기대되는 결과 예시
# --------------------------------------------------
# 본문:
# #구글 #스페이스X, 300억달러 규모 #AI 인프라 계약 체결함
# 구글은 2029년 6월까지 매월 9억2000만달러를 지급하고 #엔비디아 GPU 11만개 등 연산 자원 확보함
#
# footer:
# #Google #SpaceX #NVIDIA #AI #BTC #비트코인 #dooridoori #도리도리 #doorinati #도리나티

# --------------------------------------------------
# 7. 핵심 체크포인트
# --------------------------------------------------
# - 본문에 #구글 있으면 footer에 #Google 붙어야 함
# - 본문에 #엔비디아 있으면 footer에 #NVIDIA 붙어야 함
# - 본문/원문에 spacex가 감지되면 footer에 #SpaceX 붙어야 함
# - AI가 감지되면 footer에 #AI 붙어야 함
