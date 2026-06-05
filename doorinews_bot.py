
# 0606 수정 패치
# 1) 제목만 번역되는 fallback 제거
# 2) footer에서 #US 유지
# 3) 줄띄어쓰기 보정
# 4) "원본 설명" 박스가 나오면 다른 버전이 돌고 있는지 확인

# -----------------------------
# A. build_message() 안 fallback 부분 교체
# 기존:
# if not summary_ko:
#     raw_source = f"{title}. {desc}"
#     raw_summary = summarize_text(raw_source, title=title, max_sentences=SUMMARY_SENTENCES)
#     summary_ko = translate_text_to_korean(raw_summary)
#     summary_ko = cleanup_text(summary_ko)
#     summary_ko = fix_translation_terms(summary_ko)
#     summary_ko = fix_truncated_phrases(summary_ko)
#     summary_ko = normalize_style(summary_ko)
#     summary_ko = cleanup_text(summary_ko)

# 교체:
if not summary_ko:
    log(f"[요약실패 스킵] {title}")
    return ""

# 그리고 main() 전송 루프 직전에 추가:
# msg = build_message(story)
# if not msg.strip():
#     log(f"[빈메시지 스킵] {story.get('title','')}")
#     continue


# -----------------------------
# B. footer #US 유지
# 현재 _normalize_footer_tags()에서 #US -> #미국 으로 바뀜
# 아래처럼 수정

def _normalize_footer_tags(tags: list[str]) -> list[str]:
    mapping = {
        '#Japan': '#일본',
        '#Bhutan': '#부탄',
        '#Germany': '#독일',
        '#USA': '#US',
        '#Ripple': '#XRP',
        '#RL#미국D': '#RLUSD',
        '#F O M C': '#FOMC',
        '#HesterPeirce': '#헤스터피어스',
        '#CME': '#시카고상품거래소(CME)',
        '#Qivalis': '#키발리스',
        '#RaoulPal': '#라울팔',
        '#Nuva': '#누바',
        '#Tempo': '#템포',
        '#MoneyGram': '#머니그램',
        '#Muro': '#무로',
        '#Santander': '#산탄데르'
    }
    out = []
    seen = set()
    for tag in tags:
        tag = mapping.get(tag, tag)
        if tag == '#리플':
            tag = '#XRP'
        if tag and tag not in seen:
            out.append(tag)
            seen.add(tag)
    return out


# -----------------------------
# C. 줄 띄어쓰기 보정
# _clean_summary_for_style_v3() 는 줄바꿈을 너무 평평하게 만들 수 있으니,
# 마지막에 문장 단위 줄바꿈 복구 함수 추가

def restore_telegram_linebreaks(text: str) -> str:
    text = (text or '').replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text).strip()

    # 이미 빈 줄이 있으면 유지
    if '\n\n' in text:
        return text

    # 마침표가 없는 스타일이라도 "임/함/됨/밝힘/전함/추진 중" 뒤는 줄바꿈
    text = re.sub(r'\s+(?=[^#\n]{0,80}(?:임|함|됨|밝힘|전함|설명함|추진 중|검토 중)\b)', '\n\n', text, count=1)

    # 너무 길면 앞문장/뒷문장 2줄로 쪼갬
    if len(text) > 70 and '\n\n' not in text:
        m = re.search(r'(임|함|됨|밝힘|전함|설명함)', text)
        if m:
            cut = m.end()
            text = text[:cut].strip() + '\n\n' + text[cut:].strip()

    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

# build_message() 안에서
# summary = format_summary_for_telegram(summary, max_sentences=3, max_chars=110)
# 바로 다음 줄에 추가:
summary = restore_telegram_linebreaks(summary)


# -----------------------------
# D. pink "원본 설명" 박스 확인
# 현재 네가 올린 코드의 build_message()는
# summary / 링크 / 출처 / footer 4블록만 만들고 "원본 설명" 블록은 없음
# 그래서 그 박스가 계속 보이면,
# 1) 다른 옛날 파일이 실행 중이거나
# 2) 텔레그램에서 수동 수정한 글일 가능성이 큼
#
# 아래 로그를 main() 시작부에 추가해서 실제 실행 파일 버전 확인:
log("RUNNING_BUILD=0606_fix_us_skip_linebreak")


# -----------------------------
# E. 3번째 기사(Morgan Stanley/SpaceX)용 태그 강제 추가
# _ensure_case_tags_v3() pairs에 이 2개 추가
# ('모건스탠리', [r'morgan stanley', r'모건스탠리'])
# ('스페이스X', [r'spacex', r'스페이스x'])

# 그리고 footer용도 추가
# ('#MorganStanley', [r'morgan stanley', r'모건스탠리'])
# ('#SpaceX', [r'spacex', r'스페이스x'])
