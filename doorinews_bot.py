
# 뉴스봇 태그 로직 보강 패치
# 목적:
# 1) 본문 태그는 4~5개 제한 없이 핵심 태그를 최대한 많이 유지
# 2) footer는 영어 태그가 붙되, 본문에 영어 태그가 이미 있으면 중복 금지
#    예: 본문 #코인베이스 -> footer #Coinbase 추가
#        본문 #Coinbase -> footer #Coinbase 추가 금지
# 3) footer는 본문에 실제로 들어간 태그 기준으로만 생성
# 4) 조사 띄어쓰기와 붙은 해시태그 보정

# -----------------------------
# 1. ENTITY_RULES 구조 예시
# -----------------------------
# 기존 ENTITY_RULES가 있다면 아래 필드만 맞춰서 보강해.
# - aliases: 기사 본문/제목에서 잡을 문자열들
# - ko: 한국어 표기
# - inline_tag: 본문에 넣을 해시태그
# - footer_tag: footer에 넣을 영어 해시태그
#
# 예시:
ENTITY_RULES = [
    {
        "aliases": ["Coinbase", "코인베이스"],
        "ko": "코인베이스",
        "inline_tag": "#코인베이스",
        "footer_tag": "#Coinbase",
    },
    {
        "aliases": ["Polymarket", "폴리마켓"],
        "ko": "폴리마켓",
        "inline_tag": "#폴리마켓",
        "footer_tag": "#Polymarket",
    },
    {
        "aliases": ["Bitget Wallet", "Bitget", "비트겟월렛", "비트겟 월렛"],
        "ko": "비트겟월렛",
        "inline_tag": "#비트겟월렛",
        "footer_tag": "#BitgetWallet",
    },
    {
        "aliases": ["Mastercard", "마스터카드"],
        "ko": "마스터카드",
        "inline_tag": "#마스터카드",
        "footer_tag": "#Mastercard",
    },
    {
        "aliases": ["RLUSD"],
        "ko": "RLUSD",
        "inline_tag": "#RLUSD",
        "footer_tag": "#RLUSD",
    },
    {
        "aliases": ["XRP Ledger", "XRPL", "XRPLedger", "XRP 레저", "XRP레저"],
        "ko": "XRPL",
        "inline_tag": "#XRPL",
        "footer_tag": "#XRPL",
    },
    {
        "aliases": ["Wormhole"],
        "ko": "웜홀",
        "inline_tag": "#웜홀",
        "footer_tag": "#Wormhole",
    },
    {
        "aliases": ["Standard Chartered", "스탠다드차타드"],
        "ko": "스탠다드차타드",
        "inline_tag": "#스탠다드차타드",
        "footer_tag": "#StandardChartered",
    },
    {
        "aliases": ["Zodia Custody", "조디아 커스터디", "조디아쿠스투디", "조디아커스터디"],
        "ko": "조디아커스터디",
        "inline_tag": "#조디아커스터디",
        "footer_tag": "#ZodiaCustody",
    },
    {
        "aliases": ["CLARITY Act", "Clarity Act", "클래리티법안", "클래리티법"],
        "ko": "클래리티법안",
        "inline_tag": "#클래리티법안",
        "footer_tag": "#CLARITYAct",
    },
    {
        "aliases": ["Patrick Witt", "패트릭위트"],
        "ko": "패트릭위트",
        "inline_tag": "#패트릭위트",
        "footer_tag": "#PatrickWitt",
    },
    {
        "aliases": ["Anthropic", "앤트로픽"],
        "ko": "앤트로픽",
        "inline_tag": "#앤트로픽",
        "footer_tag": "#Anthropic",
    },
    {
        "aliases": ["AI", "인공지능"],
        "ko": "인공지능",
        "inline_tag": "#인공지능",
        "footer_tag": "#AI",
    },
    {
        "aliases": ["Cardano", "카르다노", "ADA"],
        "ko": "카르다노",
        "inline_tag": "#카르다노",
        "footer_tag": "#Cardano",
    },
    {
        "aliases": ["Charles Hoskinson", "찰스호스킨슨"],
        "ko": "찰스호스킨슨",
        "inline_tag": "#찰스호스킨슨",
        "footer_tag": "#CharlesHoskinson",
    },
    {
        "aliases": ["Raoul Pal", "라울팔"],
        "ko": "라울팔",
        "inline_tag": "#라울팔",
        "footer_tag": "#RaoulPal",
    },
]

# -----------------------------
# 2. 본문 태그 자동 수집 / 주입
# -----------------------------
def _collect_entity_tags(raw_text: str):
    low = (raw_text or "").lower()
    inline_tags = []
    footer_tags = []
    seen_inline = set()
    seen_footer = set()

    for rule in ENTITY_RULES:
        aliases = rule.get("aliases", [])
        if any(a.lower() in low for a in aliases):
            inline_tag = rule.get("inline_tag", "").strip()
            footer_tag = rule.get("footer_tag", "").strip()

            if inline_tag and inline_tag not in seen_inline:
                inline_tags.append(inline_tag)
                seen_inline.add(inline_tag)

            if footer_tag and footer_tag not in seen_footer:
                footer_tags.append(footer_tag)
                seen_footer.add(footer_tag)

    return inline_tags, footer_tags


def inject_entity_hashtags(summary: str, raw_text: str) -> str:
    summary = (summary or "").strip()
    raw_text = raw_text or ""

    inline_tags, _ = _collect_entity_tags(raw_text)

    existing = set(re.findall(r'#[A-Za-z0-9가-힣()]+', summary))
    tags_to_add = [t for t in inline_tags if t not in existing]

    if not tags_to_add:
        return summary

    # 맨 앞 문장에 몰아 붙이기
    prefix = " ".join(tags_to_add)
    if summary.startswith(prefix):
        return summary

    summary = f"{prefix} {summary}".strip()
    summary = _normalize_inline_hashtag_spacing(summary)
    summary = _normalize_korean_hashtag_particles(summary)
    return summary


# -----------------------------
# 3. 본문 붙은 해시태그 띄어쓰기 보정
# -----------------------------
def _normalize_inline_hashtag_spacing(text: str) -> str:
    text = text or ""

    # #잉글랜드#은행 -> #잉글랜드 #은행
    text = re.sub(r'(#[가-힣A-Za-z0-9()]+)(?=#[가-힣A-Za-z0-9()]+)', r'\1 ', text)

    # 해시태그와 일반 텍스트 사이 최소 공백 확보
    text = re.sub(r'(?<!\s)(#[가-힣A-Za-z0-9()]+)', r' \1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _normalize_korean_hashtag_particles(text: str) -> str:
    text = text or ""

    particles = ["은", "는", "이", "가", "을", "를", "에", "의", "과", "와", "로", "도", "만", "인"]
    for p in particles:
        text = re.sub(rf'(#[가-힣A-Za-z0-9()]+)\s+{p}(\b)', rf'\1 {p}\2', text)
    return text


# -----------------------------
# 4. footer 생성 로직
# -----------------------------
# 중요:
# - 본문에 한국어 태그가 있으면 footer에 영어 태그를 붙임
# - 본문에 영어 태그가 이미 있으면 footer에 같은 영어 태그는 다시 안 붙임
# - footer는 본문에 실제 들어간 태그 기준으로만 생성
INLINE_TO_FOOTER_TAG_MAP = {
    "#비트코인": "#Bitcoin",
    "#이더리움": "#Ethereum",
    "#리플": "#Ripple",
    "#XRP": "#XRP",
    "#XRPL": "#XRPL",
    "#스테이블코인": "#Stablecoin",
    "#코인베이스": "#Coinbase",
    "#비트겟월렛": "#BitgetWallet",
    "#폴리마켓": "#Polymarket",
    "#마스터카드": "#Mastercard",
    "#웜홀": "#Wormhole",
    "#스탠다드차타드": "#StandardChartered",
    "#조디아커스터디": "#ZodiaCustody",
    "#클래리티법안": "#CLARITYAct",
    "#패트릭위트": "#PatrickWitt",
    "#앤트로픽": "#Anthropic",
    "#인공지능": "#AI",
    "#카르다노": "#Cardano",
    "#ADA": "#ADA",
    "#찰스호스킨슨": "#CharlesHoskinson",
    "#라울팔": "#RaoulPal",
    "#미국": "#US",
    "#영국": "#UK",
    "#한국": "#Korea",
    "#일본": "#Japan",
    "#은행": "#Bank",
    "#모기지": "#Mortgage",
    "#담보": "#Collateral",
    "#고용": "#Jobs",
}

FIXED_FOOTER_TAGS = ["#BTC", "#비트코인", "#dooridoori", "#도리도리", "#doorinati", "#도리나티"]


def _extract_inline_tags_from_summary(summary: str):
    return re.findall(r'#[A-Za-z0-9가-힣()]+', summary or '')


def _build_footer_tags_from_inline(summary: str, base_tags=None):
    if base_tags is None:
        base_tags = FIXED_FOOTER_TAGS[:]

    inline_tags = _extract_inline_tags_from_summary(summary)
    inline_set = set(inline_tags)

    english_inline = {t for t in inline_tags if re.fullmatch(r'#[A-Za-z0-9()]+', t or '')}
    out = []

    # 본문에 걸린 한국어 태그 -> 영어 footer 변환
    for t in inline_tags:
        mapped = INLINE_TO_FOOTER_TAG_MAP.get(t)
        if mapped and mapped not in english_inline and mapped not in out:
            out.append(mapped)

    # base tags 유지
    for t in base_tags:
        if t not in out:
            out.append(t)

    return out


def _normalize_footer_tags(tags):
    seen = set()
    out = []

    for tag in tags:
        tag = (tag or "").strip().replace(".", "")
        if not tag.startswith("#"):
            continue
        if tag in seen:
            continue
        seen.add(tag)
        out.append(tag)

    return out


# -----------------------------
# 5. build_message / format_message 쪽 교체
# -----------------------------
# 네 코드에 아래 흐름이 있으면:
#
# summary = rewrite_summary_with_openai(...)
# summary = inject_entity_hashtags(summary, raw_text)
# summary = _normalize_inline_hashtag_spacing(summary)
# summary = _normalize_korean_hashtag_particles(summary)
# footer_tags = _build_footer_tags_from_inline(summary, FIXED_FOOTER_TAGS)
# footer_tags = _normalize_footer_tags(footer_tags)
#
# parts = [
#     html.escape(summary),
#     '🌐 <a href="http://t.me/Doorinews">공식 글로벌 실시간 도리뉴스</a>',
#     f'<a href="{html.escape(story.get("url", ""))}">출처</a>',
#     ' '.join(html.escape(t) for t in footer_tags)
# ]
#
# return '\n\n'.join(parts)

# -----------------------------
# 6. 문장 끝 강제 축약
# -----------------------------
def normalize_sentence_endings(summary: str) -> str:
    summary = summary or ""

    replacements = [
        ("했다", "함"),
        ("하였다", "함"),
        ("됐다", "됨"),
        ("되었다", "됨"),
        ("밝혔다", "밝힘"),
        ("전했다", "전함"),
        ("설명했다", "설명함"),
        ("알려졌다", "알려짐"),
        ("나타났다", "나타남"),
        ("보였다", "보임"),
        ("거론됐다", "거론됨"),
        ("예정이다", "예정"),
        ("예정임.", "예정"),
        ("추진하고 있다", "추진 중"),
        ("검토하고 있다", "검토 중"),
        ("준비하고 있다", "준비 중"),
        ("확대하고 있다", "확대 중"),
    ]

    for a, b in replacements:
        summary = summary.replace(a, b)

    summary = summary.replace(".", "")
    summary = re.sub(r'\s+', ' ', summary).strip()
    return summary


# -----------------------------
# 7. 추천 적용 순서
# -----------------------------
# summary = rewrite_summary_with_openai(title, article_text, desc)
# summary = normalize_sentence_endings(summary)
# summary = inject_entity_hashtags(summary, raw_text)
# summary = _normalize_inline_hashtag_spacing(summary)
# summary = _normalize_korean_hashtag_particles(summary)
# footer_tags = _build_footer_tags_from_inline(summary, FIXED_FOOTER_TAGS)
# footer_tags = _normalize_footer_tags(footer_tags)

# -----------------------------
# 8. 핵심 포인트
# -----------------------------
# - "본문 태그는 최대 4~5개" 같은 제한을 두지 말고, ENTITY_RULES에 잡힌 핵심 태그는 다 넣어도 됨
# - 대신 footer는 "본문에 실제로 걸린 태그"를 기준으로 영어 변환
# - 본문에 영어 태그가 이미 있으면 footer 중복 금지
# - 본문에 #코인베이스 가 있으면 footer에 #Coinbase 추가
# - 본문에 #Coinbase 가 직접 있으면 footer에 #Coinbase 재추가 금지
