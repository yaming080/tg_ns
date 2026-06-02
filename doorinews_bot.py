
# PATCH NOTE — footer 태그를 "본문에 걸린 것만 영어로", 붙은 해시태그 띄어쓰기 수정

# 1) 아래 함수 새로 추가
def _normalize_inline_hashtag_spacing(text: str) -> str:
    text = text or ""

    # 한글 해시태그가 바로 붙는 경우 띄어쓰기 추가
    # 예: #잉글랜드#은행 -> #잉글랜드 #은행
    text = re.sub(r'(#[가-힣A-Za-z0-9()]+)(?=#[가-힣A-Za-z0-9()]+)', r'\1 ', text)

    # 조사 앞은 유지하되, 해시태그 뒤에 조사 없이 바로 다른 해시태그가 오면 분리
    text = re.sub(r'(#[가-힣A-Za-z0-9()]+)\s*(#[가-힣A-Za-z0-9()]+)', r'\1 \2', text)

    # 중복 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# 2) footer 태그를 summary 본문 해시태그 기준으로만 만들 함수 추가
#    - 본문에 #코인베이스 가 있으면 footer에 #Coinbase
#    - 본문에 영어 해시태그가 직접 있으면 footer에는 다시 안 붙임
#    - House / Silver / Gold 같은 잡태그 제거
INLINE_TO_FOOTER_TAG_MAP = {
    '#비트코인': '#Bitcoin',
    '#이더리움': '#Ethereum',
    '#XRP': '#XRP',
    '#리플': '#Ripple',
    '#스테이블코인': '#Stablecoin',
    '#코인베이스': '#Coinbase',
    '#에테나': '#Ethena',
    '#ENA': '#ENA',
    '#영국': '#UK',
    '#잉글랜드은행': '#BankOfEngland',
    '#은행': '#Bank',
    '#하원': '#HouseOfLords',
    '#하원위원회': '#HouseOfLords',
    '#EU': '#EU',
    '#유럽': '#EU',
    '#DFS': '#DFS',
    '#EBA': '#EBA',
    '#금융': '#Finance',
}

BLOCKED_FOOTER_TAGS = {
    '#House', '#Silver', '#Gold'
}

def _extract_inline_tags_from_summary(summary: str) -> list[str]:
    return re.findall(r'#[A-Za-z0-9가-힣()]+', summary or '')

def _build_footer_tags_from_inline(summary: str, base_tags: list[str]) -> list[str]:
    inline_tags = _extract_inline_tags_from_summary(summary)
    out = []

    # 본문에 걸린 태그만 영어 footer로 변환
    for t in inline_tags:
        if re.search(r'#[A-Za-z0-9()]+', t):
            # 본문에 영어 해시태그가 직접 있으면 footer 재추가 금지
            continue

        mapped = INLINE_TO_FOOTER_TAG_MAP.get(t)
        if mapped and mapped not in BLOCKED_FOOTER_TAGS:
            out.append(mapped)

    # 기본 브랜드 태그는 항상 유지
    for t in base_tags:
        if t not in out:
            out.append(t)

    # 중복 제거
    dedup = []
    seen = set()
    for t in out:
        if t in BLOCKED_FOOTER_TAGS:
            continue
        if t not in seen:
            dedup.append(t)
            seen.add(t)

    return dedup


# 3) build_message() 안에서 아래 부분 교체
# 기존:
# summary_ko = fix_broken_inline_hashtags(summary_ko)
# summary_ko = remove_duplicate_inline_hashtags(summary_ko)
# summary_ko = finalize_summary_ending(summary_ko)
#
# 교체:
summary_ko = fix_broken_inline_hashtags(summary_ko)
summary_ko = _normalize_inline_hashtag_spacing(summary_ko)
summary_ko = remove_duplicate_inline_hashtags(summary_ko)
summary_ko = finalize_summary_ending(summary_ko)
summary_ko = _normalize_inline_hashtag_spacing(summary_ko)


# 4) build_message() 안 footer 생성 부분 교체
# 기존:
# dynamic_tags = filter_final_tags(dynamic_tags)
# footer_tags = dynamic_tags + [f'#{t}' for t in FINAL_HASHTAGS]
# footer_tags = _ensure_case_tags(summary, story, footer_tags)
# footer_tags = _normalize_footer_tags(footer_tags)
# inline_tags = set(re.findall(r'#[A-Za-z0-9가-힣]+', summary))
# footer_tags = [f for f in footer_tags if f not in inline_tags]

# 교체:
base_footer_tags = [f'#{t}' for t in FINAL_HASHTAGS]
footer_tags = _build_footer_tags_from_inline(summary, base_footer_tags)
footer_tags = _normalize_footer_tags(footer_tags)

# dedup 아래는 그대로 사용


# 5) 잉글랜드은행 / 영국 / 하원 / 스테이블코인 inline 태그가 잘 걸리게 ENTITY_RULES 또는 통합 규칙에 아래 항목 포함
ENTITY_RULES_EXTRA = {
    "UK": {
        "aliases": ["UK", "United Kingdom", "Britain", "영국"],
        "ko": "영국",
        "inline_tag": "#영국",
        "footer_tag": "#UK",
    },
    "Bank of England": {
        "aliases": ["Bank of England", "잉글랜드은행"],
        "ko": "잉글랜드은행",
        "inline_tag": "#잉글랜드은행",
        "footer_tag": "#BankOfEngland",
    },
    "House of Lords": {
        "aliases": ["House of Lords", "하원 위원회", "하원위원회"],
        "ko": "하원",
        "inline_tag": "#하원",
        "footer_tag": "#HouseOfLords",
    },
    "Stablecoin": {
        "aliases": ["stablecoin", "stablecoins", "스테이블코인"],
        "ko": "스테이블코인",
        "inline_tag": "#스테이블코인",
        "footer_tag": "#Stablecoin",
    },
}
