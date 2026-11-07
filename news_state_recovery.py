"""Recover only certified completed processing; never retry uncertain sends."""
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RECEIPT = 'news_completion_receipt.json'
CHECKPOINT_STEP = 'Certify completed news processing'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checkpoint(root, run_id, attempt):
    from news_state_guard import STATE, MARKER, read_json, write_json, validate_state, validate_marker
    root = Path(root)
    marker = read_json(root/MARKER)
    validate_marker(marker)
    if (marker['status'], marker['run_id'], marker['attempt']) != ('pending', str(run_id), str(attempt)):
        raise ValueError('완료 증명 실행 불일치')
    if not re.fullmatch(r'[0-9a-f]{64}', marker.get('state_before_sha256', '')):
        raise ValueError('시작 상태 검증값 없음')
    validate_state(read_json(root/STATE))
    write_json(root/RECEIPT, dict(schema=1, run_id=str(run_id), attempt=str(attempt),
        state_sha256=digest(root/STATE), marker_sha256=digest(root/MARKER),
        completed_at_utc=datetime.now(timezone.utc).isoformat()))
    print('PROCESSING_COMPLETION_CERTIFIED')


def validated_snapshot(folder, current_marker, current_state_path):
    from news_state_guard import STATE, MARKER, read_json, validate_state
    folder = Path(folder)
    receipt = read_json(folder/RECEIPT)
    marker = read_json(folder/MARKER)
    if marker != current_marker or marker.get('state_before_sha256') != digest(current_state_path):
        raise ValueError('복구 기준 이력/표식 불일치')
    if (receipt.get('schema'), receipt.get('run_id'), receipt.get('attempt')) != (
            1, marker['run_id'], marker['attempt']):
        raise ValueError('복구 완료 증명 실행 불일치')
    if receipt.get('state_sha256') != digest(folder/STATE) or receipt.get('marker_sha256') != digest(folder/MARKER):
        raise ValueError('복구 파일 검증값 불일치')
    state = read_json(folder/STATE)
    validate_state(state)
    return state


def gh(*args):
    result = subprocess.run(['gh', *args], capture_output=True, text=True, encoding='utf8', timeout=90)
    if result.returncode:
        raise RuntimeError('GitHub 복구 자료 조회 실패: 비밀값/원격 응답은 출력하지 않음')
    return result.stdout


def fetch_completed_snapshot(repo, marker, folder):
    """Actions metadata and checkpoint success must agree before download."""
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        return False
    run_id, attempt = marker['run_id'], marker['attempt']
    if not run_id.isdigit() or not attempt.isdigit():
        return False
    base = 'repos/' + repo + '/actions/runs/' + run_id
    run = json.loads(gh('api', base))
    if (run.get('id') != int(run_id) or run.get('head_branch') != 'main'
            or run.get('repository', {}).get('full_name') != repo
            or run.get('status') != 'completed' or run.get('conclusion') != 'failure'
            or run.get('run_attempt') != int(attempt)):
        return False
    jobs = json.loads(gh('api', base + '/attempts/' + attempt + '/jobs?per_page=100'))
    certified = any(j.get('status') == 'completed' and any(
        s.get('name') == CHECKPOINT_STEP and s.get('conclusion') == 'success'
        for s in j.get('steps', [])) for j in jobs.get('jobs', []))
    if not certified:
        return False
    name = 'publication-state-' + run_id + '-' + attempt
    artifacts = json.loads(gh('api', base + '/artifacts?per_page=100'))
    matches = [a for a in artifacts.get('artifacts', []) if a.get('name') == name and not a.get('expired')]
    if len(matches) != 1 or matches[0].get('workflow_run', {}).get('id') != int(run_id):
        return False
    gh('run', 'download', run_id, '--repo', repo, '--name', name, '--dir', str(folder))
    return True


def recover_previous(root, marker):
    from news_state_guard import STATE, MARKER, write_json, persist
    # Old/incomplete snapshots require manual audit. Never clear a bare marker.
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if not repo or not os.environ.get('GH_TOKEN') or not marker.get('state_before_sha256'):
        return False
    with tempfile.TemporaryDirectory() as folder:
        if not fetch_completed_snapshot(repo, marker, folder):
            return False
        state = validated_snapshot(folder, marker, Path(root)/STATE)
    # Do not release articles accumulated while persistence was unavailable.
    now = datetime.now(timezone.utc)
    from news_resume import publication_time
    prior = publication_time({'pub': state.get('publish_not_before_utc')})
    state['publish_not_before_utc'] = max(now, prior or now).isoformat()
    write_json(Path(root)/STATE, state)
    completed = dict(marker, status='complete', completed_at_utc=now.isoformat(),
                     recovered_from_run=marker['run_id'])
    write_json(Path(root)/MARKER, completed)
    persist(root, 'Recover certified completed news run ' + marker['run_id'])
    print('CERTIFIED_STATE_RECOVERED; backlog blocked before ' + now.isoformat())
    return True
