"""Fail closed after an interrupted publication; no Telegram or AI calls.

The remote pending marker must be durable before any send. State and the
completion marker are then committed together. A failed push leaves the
remote marker pending and blocks the next run instead of replaying posts.
"""
import argparse
import json
import os
import subprocess
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from doorinews_editor import story_hash

STATE = 'news_state.json'
MARKER = 'news_publication_guard.json'
ROOT = Path(__file__).resolve().parent


def validate_state(state):
    if not isinstance(state, dict) or not isinstance(state.get('posted'), dict):
        raise ValueError('게시 이력 누락/손상: 빈 이력으로 발송하지 않습니다')
    if any(not isinstance(v, dict) or not isinstance(v.get('title'), str) or not v['title'].strip()
           for v in state['posted'].values()):
        raise ValueError('게시 이력 항목 손상: 발송 중단')


def recover_confirmed(state, now=None, records=None):
    validate_state(state)
    now = now or datetime.now(timezone.utc)
    if records is None:
        records = json.loads((ROOT/'news_confirmed_sends.json').read_text(encoding='utf8'))['records']
    added = 0
    for record in records:
        sent_at = datetime.fromisoformat(record['ts'])
        if not sent_at <= now <= sent_at + timedelta(days=30):
            continue
        key = story_hash(record['title'])
        if key in state['posted'] or any(story_hash(v['title']) == key for v in state['posted'].values()):
            continue
        state['posted'][key] = dict(record)
        added += 1
    return added


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write_json(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, encoding='utf8')
    if result.returncode:
        # Do not print remote URLs or authentication-bearing Git output.
        error = (result.stderr or '').lower()
        category = 'unclassified'
        for label, patterns in (
                ('remote_changed', ('non-fast-forward', 'fetch first', 'rejected')),
                ('authorization', ('authentication failed', 'permission denied', '403', '401')),
                ('connection', ('could not resolve', 'timed out', 'connection reset', 'unable to access'))):
            if any(p in error for p in patterns):
                category = label
                break
        raise RuntimeError('Git ' + args[0] + ' 실패 [' + category + ']: 게시 중단, 저장 이력/진행 표식 확인 필요')
    return result.stdout.strip()


def validate_marker(marker):
    if (not isinstance(marker, dict) or marker.get('schema') != 1
            or marker.get('status') not in ('pending', 'complete')
            or not isinstance(marker.get('run_id'), str)
            or not isinstance(marker.get('attempt'), str)):
        raise ValueError('게시 진행 표식 손상: 발송 중단')


def persist(root, message):
    # Only these two files are staged. Never force-push or resolve state conflicts
    # by choosing one side: a rejected push must keep the remote pending marker.
    git(root, 'add', '--', STATE, MARKER)
    git(root, 'commit', '-m', message, '--', STATE, MARKER)
    parent = git(root, 'rev-parse', 'HEAD^')
    for attempt in range(3):
        try:
            git(root, 'push', 'origin', 'HEAD:main')
            return
        except RuntimeError as error:
            print('STATE_PUSH_RETRY: attempt=' + str(attempt + 1) + '; ' + str(error))
            try:
                git(root, 'fetch', 'origin', 'main')
                remote = git(root, 'rev-parse', 'FETCH_HEAD')
                if remote == git(root, 'rev-parse', 'HEAD'):
                    return  # Server accepted the push, but response was lost.
                changed = git(root, 'diff', '--name-only', parent, remote, '--', STATE, MARKER)
                if changed:
                    raise ValueError('원격 게시 이력이 변경됨: 자동 덮어쓰기 금지')
                # Only our two state files are committed, and neither changed
                # remotely. Preserve unrelated remote code commits without force.
                if remote != parent:
                    git(root, 'merge-base', '--is-ancestor', parent, remote)
                    git(root, 'rebase', remote)
                    parent = remote
            except ValueError:
                raise
            except RuntimeError:
                if attempt == 2:
                    raise RuntimeError('Git push 재시도 실패: 검증된 백업으로 다음 실행에서 복구 필요') from None
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError('Git push 재시도 실패: 검증된 백업으로 다음 실행에서 복구 필요')


def begin(root, run_id, attempt, now=None, records=None):
    root = Path(root)
    git(root, 'fetch', 'origin', 'main')
    if git(root, 'rev-parse', 'HEAD') != git(root, 'rev-parse', 'FETCH_HEAD'):
        raise RuntimeError('실행 준비 중 main이 변경됨: 최신 코드와 이력으로 다음 실행을 시작하세요')
    marker_path = root/MARKER
    if marker_path.exists():
        marker = read_json(marker_path)
        validate_marker(marker)
        if marker['status'] == 'pending':
            from news_state_recovery import recover_previous
            if not recover_previous(root, marker):
                raise RuntimeError('이전 게시 기록 저장 미완료: 실행 ' + marker['run_id'] +
                                   '. 자동 발송 중단. 해당 실행의 state 백업과 성공 로그를 복구하세요')
    state = read_json(root/STATE)
    recovered = recover_confirmed(state, now, records)
    now = now or datetime.now(timezone.utc)
    write_json(root/STATE, state)
    write_json(marker_path, {'schema': 1, 'status': 'pending', 'run_id': str(run_id),
                            'attempt': str(attempt), 'started_at_utc': now.isoformat(),
                            'state_before_sha256': hashlib.sha256((root/STATE).read_bytes()).hexdigest()})
    persist(root, 'Begin guarded news run ' + str(run_id))
    print('PUBLICATION_GUARD_ARMED; recovered=' + str(recovered))


def finish(root, run_id, attempt):
    root = Path(root)
    marker = read_json(root/MARKER)
    validate_marker(marker)
    if (marker['status'], marker['run_id'], marker['attempt']) != ('pending', str(run_id), str(attempt)):
        raise RuntimeError('다른 실행의 게시 표식: 완료 처리 거부')
    validate_state(read_json(root/STATE))
    marker.update(status='complete', completed_at_utc=datetime.now(timezone.utc).isoformat())
    write_json(root/MARKER, marker)
    persist(root, 'Complete guarded news run ' + str(run_id))
    print('PUBLICATION_STATE_SAVED')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('begin', 'finish', 'checkpoint'))
    args = parser.parse_args()
    run_id, attempt = os.environ.get('GITHUB_RUN_ID'), os.environ.get('GITHUB_RUN_ATTEMPT')
    if not run_id or not attempt:
        raise RuntimeError('GitHub 실행 식별자가 없어 게시 보호 절차를 시작할 수 없습니다')
    from news_state_recovery import checkpoint
    {'begin': begin, 'finish': finish, 'checkpoint': checkpoint}[args.command](Path.cwd(), run_id, attempt)


if __name__ == '__main__':
    main()
