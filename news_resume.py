"""Do not replay the credit-outage backlog after the October 5 restart."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# Fixed incident boundary (2026-10-05 14:38:43 KST), not a moving hourly window.
# Keep this boundary on later scheduled runs so old unposted stories stay excluded.
PUBLISH_NOT_BEFORE = datetime(2026, 10, 5, 5, 38, 43, tzinfo=timezone.utc)


def publication_time(story):
    value = story.get('pub')
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        try:
            published = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            published = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if published.tzinfo is None:
            return None
        return published.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def resume_exclusion_reason(story):
    published = publication_time(story)
    if published is None:
        return '재개 기준 확인 불가: 발행 시각 누락 또는 오류'
    if published < PUBLISH_NOT_BEFORE:
        return '충전 전 밀린 기사 제외: 2026-10-05 14:38:43 KST 이전 발행'
    return ''


def select_resume_candidates(stories, log):
    eligible = []
    for story in stories:
        reason = resume_exclusion_reason(story)
        if reason:
            log(f"[재개 제외] {story.get('title', '')} | {reason}")
        else:
            eligible.append(story)
    return sorted(eligible, key=publication_time, reverse=True)
