
# 로그 강화 패치 (OpenAI 뉴스봇용)
# 적용 목표:
# - 예전처럼 feed별 수집 수, 필터 통과 수, 제외 사유, 최종 전송 수가 GitHub Actions 로그에 잘 보이게
# - 조용히 끝나는 것처럼 보이는 문제 해소

# 1) log_stats 헬퍼 추가
# log(msg) 아래에 바로 추가

def log_stats(label: str, count: int) -> None:
    log(f"[통계] {label}: {count}개")


# 2) main() 전체를 아래 버전으로 교체
def main():
    log("Bot starting...")
    log(f"모델: {OPENAI_MODEL}")
    log(f"INITIAL_RUN={INITIAL_RUN}")

    state = load_state(STATE_FILE)
    posted = state.get('posted', {})
    collected = []

    log(f"기존 posted 상태: {len(posted)}개")

    # feed별 수집
    for name, feed_url in FEEDS:
        stories = fetch_rss(feed_url, max_items=MAX_ITEMS_PER_FEED)
        log(f"{name}: {len(stories)}개 수집")
        if stories:
            for story in stories[:2]:
                log(f"  └ 수집 예시: {story.get('title', '')[:120]}")
        collected.extend(stories)

    log_stats("전체 수집", len(collected))

    # 필터 통과
    filtered = []
    negative_count = 0

    for s in collected:
        ok = matches_keywords(s, PORTFOLIO_COINS, ECON_KEYWORDS, KOREAN_KEYWORDS)
        if ok:
            filtered.append(s)
        else:
            negative_count += 1

    log_stats("필터 통과", len(filtered))
    log_stats("필터 제외", negative_count)

    new_stories = []
    seen_titles = [
        normalize_for_duplicate(item.get('title', ''))
        for item in posted.values()
        if item.get('title')
    ]
    seen_signatures = [
        item.get('signature', '')
        for item in posted.values()
        if item.get('signature')
    ]
    seen_urls = {
        item.get('url', '').strip()
        for item in posted.values()
        if item.get('url')
    }
    seen_topic_keys = {
        item.get('signature', '')
        for item in posted.values()
        if item.get('signature')
    }
    seen_canonical_keys = {
        item.get('canonical_key', '')
        for item in posted.values()
        if item.get('canonical_key')
    }

    dup_topic = 0
    dup_canonical = 0
    dup_url = 0
    dup_title = 0
    dup_semantic = 0

    for s in filtered:
        title = s.get('title', '')
        norm_title = normalize_for_duplicate(title)
        signature = build_story_signature(s)
        canonical_key = build_canonical_topic_key(s)
        url = s.get('url', '').strip()

        if (
            signature
            and len(signature.split('|')) >= 3
            and signature in seen_topic_keys
        ):
            dup_topic += 1
            log(f"[토픽중복 제외] {title}")
            log(f"  └ 시그니처: {signature}")
            continue

        if is_canonical_duplicate(canonical_key, seen_canonical_keys):
            dup_canonical += 1
            log(f"[정규토픽중복 제외] {title}")
            log(f"  └ canonical_key: {canonical_key}")
            continue

        if url and url in seen_urls:
            dup_url += 1
            log(f"[URL중복 제외] {title}")
            continue

        if is_duplicate(title, posted, url):
            dup_title += 1
            log(f"[제목/URL중복 제외] {title}")
            continue

        if is_semantically_duplicate(s, seen_signatures, seen_titles):
            dup_semantic += 1
            log(f"[의미중복 제외] {title}")
            log(f"  └ 정규화제목: {norm_title}")
            log(f"  └ 시그니처: {signature}")
            continue

        log(f"[통과] {title}")
        log(f"  └ 정규화제목: {norm_title}")
        log(f"  └ 시그니처: {signature}")

        new_stories.append(s)
        seen_titles.append(norm_title)
        seen_signatures.append(signature)

        if signature and len(signature.split('|')) >= 3:
            seen_topic_keys.add(signature)

        if canonical_key:
            seen_canonical_keys.add(canonical_key)

        if url:
            seen_urls.add(url)

    log_stats("토픽중복 제외", dup_topic)
    log_stats("정규토픽중복 제외", dup_canonical)
    log_stats("URL중복 제외", dup_url)
    log_stats("제목/URL중복 제외", dup_title)
    log_stats("의미중복 제외", dup_semantic)
    log_stats("최종 전송 대상", len(new_stories))

    state['posted'] = posted
    save_state(STATE_FILE, state)

    if INITIAL_RUN:
        log("INITIAL_RUN=true 상태라 텔레그램 발송 없이 종료")
        return

    posted_count = 0
    failed_count = 0

    for i, story in enumerate(new_stories, start=1):
        title = story.get('title', '')
        log(f"[전송 시도 {i}/{len(new_stories)}] {title}")

        msg = build_message(story)
        log(f"  └ 메시지 길이: {len(msg)}자")
        if story.get('image_url'):
            log(f"  └ 이미지 있음: {story.get('image_url')[:120]}")
        else:
            log("  └ 이미지 없음")

        ok = send_telegram_photo(
            TELEGRAM_BOT_TOKEN,
            TELEGRAM_CHANNEL_ID,
            story.get('image_url', ''),
            msg
        )

        if ok:
            signature = build_story_signature(story)
            canonical_key = build_canonical_topic_key(story)
            update_posted(
                story['title'],
                posted,
                story.get('url', ''),
                signature,
                canonical_key
            )
            state['posted'] = posted
            save_state(STATE_FILE, state)
            posted_count += 1
            log(f"[POST 성공] {story['title']}")
        else:
            failed_count += 1
            log(f"[POST 실패] {story['title']}")

        time.sleep(0.3)

    log("=" * 60)
    log(f"실행 요약 | 전체수집={len(collected)} | 필터통과={len(filtered)} | 전송대상={len(new_stories)} | 성공={posted_count} | 실패={failed_count}")
    log("=" * 60)


# 3) 선택사항: send_telegram_photo / send_telegram_message 로그 강화
# 아래처럼 보내기 직전 로그를 추가하면 원인 파악 쉬움

# send_telegram_message() 안 payload 만들기 직전에 추가
# log(f"[텔레그램 텍스트 전송] 길이={len(message)}")

# send_telegram_photo() 안 payload 만들기 직전에 추가
# log(f"[텔레그램 사진 전송] image_url={image_url[:120]} | caption_len={len(caption)}")
