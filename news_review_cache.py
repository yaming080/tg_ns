"""Persist exact review results and measured API usage; never mark a story posted.

Only validated, completed responses are reusable. Keys include model, complete
request, editorial context and policy version. No credentials or image bytes are
persisted. A changed source/prompt/history/image always causes a new review.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import time
from functools import lru_cache
from pathlib import Path
from news_review_identity import canonical_scope

VERSION = 'review-cache-v29-1'
MAX_ENTRIES = 1500
TTL = 72 * 3600
NEGATIVE_TTL = 7 * 86400
CONTENT_TTL = 7 * 86400  # Exceeds the 72-hour article eligibility window.
MAX_CONTENT_RESULTS = 4000
# Standard API USD / million tokens, Luna checked 2026-10-08.
# Estimates, not invoices; historical model rates retained for old records.
PRICES = {'gpt-5.4': (2.50, .25, 15.0), 'gpt-5.4-mini': (.75, .075, 4.50),
          'gpt-6-luna': (.10, .01, .50)}
_STORE = ContextVar('news_review_store', default=None)
_CONTEXT = ContextVar('news_review_context', default={})


class ReviewQuotaError(RuntimeError):
    pass


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    default=str).encode('utf-8')).hexdigest()


@contextmanager
def review_context(stage, scope=None, validator=None):
    previous = _CONTEXT.get().get('scope')
    if isinstance(previous,dict) and isinstance(scope,dict):
        scope = dict(previous, **scope)
    token = _CONTEXT.set(dict(stage=stage, scope=scope, validator=validator))
    try:
        yield
    finally:
        _CONTEXT.reset(token)


def valid_checks(text, flag, fields):
    try:
        result = json.loads(text)
        return (isinstance(result, dict) and type(result.get(flag)) is bool
                and isinstance(result.get('reason'), str) and bool(result['reason'].strip())
                and isinstance(result.get('checks'), dict)
                and all(type(result['checks'].get(k)) is bool for k in fields))
    except (ValueError, TypeError):
        return False


def _negative_response(text):
    try:
        obj = json.loads(text)
        return isinstance(obj, dict) and (obj.get('publish') is False
            or obj.get('approved') is False or obj.get('decision') == 'uncertain')
    except ValueError:
        return text.upper() in {'SKIP', '제외', '스킵'}


def _value(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def _number(value):
    return value if type(value) is int and value >= 0 else None


def request_options(model):
    # Keep the same Responses endpoint and prompts. Bound reasoning + visible
    # output together; incomplete reviews are held, never auto-escalated.
    if model == 'gpt-6-luna':
        return {'reasoning': {'effort': 'low'}, 'max_output_tokens': 4096,
                'service_tier': 'default'}
    return {}


class ReviewStore:
    def __init__(self, state, persist, logger=print, clock=time.time):
        self.state, self.persist, self.log, self.clock = state, persist, logger, clock
        self.data = state.setdefault('ai_review', {})
        if self.data.get('version') != VERSION:
            self.data['entries'] = {}
        self.data['version'] = VERSION
        self.entries = self.data.setdefault('entries', {})
        self.usage = self.data.setdefault('usage_by_day_utc', {})
        self.calls = self.hits = self.errors = 0
        self.started = self.clock()
        self.published = self.missing_usage = self.unpriced_calls = 0
        self.estimated_usd = 0.0
        self.quota_error = ''
        self.prune()

    def prune(self):
        now = self.clock()
        self.entries = {k:v for k,v in self.entries.items()
                        if isinstance(v,dict) and isinstance(v.get('expires'),(int,float))
                        and v['expires'] > now and isinstance(v.get('text'),str)}
        self.entries = dict(sorted(self.entries.items(), key=lambda kv:kv[1]['expires'])[-MAX_ENTRIES:])
        self.data['entries'] = self.entries
        # Daily aggregate only: bound repository state growth.
        for day in sorted(self.usage)[:-90]:
            del self.usage[day]

    def bucket(self, model, stage):
        day = datetime.fromtimestamp(self.clock(), timezone.utc).date().isoformat()
        return self.usage.setdefault(day, {}).setdefault(model, {}).setdefault(stage, {
            'api_calls':0, 'cache_hits':0, 'errors':0, 'missing_usage':0,
            'input_tokens':0, 'cached_input_tokens':0, 'output_tokens':0,
            'reasoning_tokens':0, 'estimated_usd':0.0, 'unpriced_calls':0})

    def record_usage(self, response, model, stage, bucket):
        usage = _value(response, 'usage')
        inp = _number(_value(usage, 'input_tokens'))
        out = _number(_value(usage, 'output_tokens'))
        if inp is None or out is None:
            bucket['missing_usage'] += 1
            self.missing_usage += 1
            self.log(f'[AI 사용량] {stage} | {model} | 토큰 정보 없음 (비용 미확정)')
            return
        cached = _number(_value(_value(usage,'input_tokens_details'), 'cached_tokens')) or 0
        cached = min(cached, inp)
        reasoning = _number(_value(_value(usage,'output_tokens_details'), 'reasoning_tokens')) or 0
        for key,value in [('input_tokens',inp),('cached_input_tokens',cached),
                          ('output_tokens',out),('reasoning_tokens',reasoning)]:
            bucket[key] += value
        rates = PRICES.get(model)
        if rates:
            cost = ((inp-cached)*rates[0] + cached*rates[1] + out*rates[2])/1_000_000
            if model == 'gpt-6-luna':
                # Cached reads and cache writes are distinct. Add the write
                # premium only; their base input cost is already counted.
                writes = _number(_value(_value(usage,'input_tokens_details'), 'cache_write_tokens')) or 0
                writes = min(writes, inp-cached)
                bucket['cache_write_tokens'] = bucket.get('cache_write_tokens', 0) + writes
                input_cost = ((inp-cached)*rates[0] + cached*rates[1] + writes*.025)
                cost = (input_cost*(2 if inp > 272000 else 1)
                        + out*rates[2]*(1.5 if inp > 272000 else 1))/1_000_000
            bucket['estimated_usd'] = round(bucket['estimated_usd'] + cost, 9)
            self.estimated_usd += cost
            price = f'단가계산=${cost:.6f}'
        else:
            bucket['unpriced_calls'] += 1
            self.unpriced_calls += 1
            price = '모델 단가 미등록 (비용 미확정)'
        self.log(f'[AI 사용량] {stage} | {model} | 입력={inp} 캐시입력={cached} 출력={out} | {price}')

    def request(self, client, model, payload, stage, scope, validator):
        if self.quota_error:
            raise ReviewQuotaError(self.quota_error)
        key_parts = [VERSION,model,stage,scope,payload]
        options = request_options(model)
        if options:
            key_parts.append(options)
        key = fingerprint(key_parts)
        bucket = self.bucket(model,stage)
        # Keep completed negative decisions out of the high-churn request LRU.
        # The key still contains exact prompt/source/image/model/options.
        durable = content_result('negative_request', key)
        if durable and isinstance(durable.get('text'), str) and validator(durable['text']):
            self.hits += 1
            bucket['cache_hits'] += 1
            self.log(f'[제외 판정 재사용] {stage} | {key[:12]}')
            return durable['text']
        entry = self.entries.get(key)
        if entry and entry['expires'] > self.clock() and validator(entry['text']):
            if _negative_response(entry['text']):
                # Promote still-valid old six-hour entries without another call.
                content_result('negative_request', key, {'text': entry['text']})
                entry['expires'] = self.clock() + NEGATIVE_TTL
            self.hits += 1
            bucket['cache_hits'] += 1
            self.log(f'[AI 검토 재사용] {stage} | {key[:12]}')
            return entry['text']
        self.calls += 1
        bucket['api_calls'] += 1
        try:
            response = client.responses.create(model=model, input=payload, **options)
        except Exception as exc:
            self.errors += 1
            bucket['errors'] += 1
            code = _value(exc,'code')
            body = _value(exc,'body',{})
            if not isinstance(code,str) and isinstance(body,dict):
                code = body.get('code') or _value(body.get('error',{}),'code')
            if code in {'credit_balance_exhausted','insufficient_quota',
                        'organization_spend_limit_exceeded','project_spend_limit_exceeded',
                        'organization_usage_limit_exceeded'}:
                self.quota_error = 'OpenAI 사용 중단: ' + code
            self.persist()
            raise
        self.record_usage(response,model,stage,bucket)
        text = str(_value(response,'output_text','') or '').strip()
        status = _value(response,'status')
        completed = status is None or status == 'completed'
        if completed and text and len(text) <= 16000 and validator(text):
            ttl = NEGATIVE_TTL if _negative_response(text) else TTL
            self.entries[key] = {'text':text,'expires':self.clock()+ttl}
            if ttl == NEGATIVE_TTL:
                content_result('negative_request', key, {'text': text})
            self.prune()
        self.persist()
        # Partial output must never be treated as a completed review.
        return text if completed else ''


def request_text(client, model, payload, *, stage=None, scope=None, validator=None):
    context = _CONTEXT.get()
    stage = stage or context.get('stage','summary')
    scope = scope if scope is not None else context.get('scope')
    validator = validator or context.get('validator') or (lambda value: bool(value.strip()))
    store = _STORE.get()
    if store is not None:
        return store.request(client,model,payload,stage,scope,validator)
    response = client.responses.create(model=model,input=payload, **request_options(model))
    status = _value(response,'status')
    if status is not None and isinstance(status,str) and status != 'completed':
        return ''
    return str(_value(response,'output_text','') or '').strip()


def record_publication():
    """Call only after Telegram confirms delivery; never count held candidates."""
    store = _STORE.get()
    if store is not None:
        store.published += 1


def repair_memory(scope, result=None):
    """Reserve one correction per source/model/policy, persisted before paid work.

    None means no record. An empty summary means held/pending, never approved.
    Seven days exceeds article freshness; a changed source has a new identity.
    """
    store = _STORE.get()
    if store is None:
        return None
    records = store.data.setdefault('summary_repairs_v1', {})
    now = store.clock()
    records = {k: v for k, v in records.items() if isinstance(v, dict)
               and isinstance(v.get('expires'), (int, float)) and v['expires'] > now
               and isinstance(v.get('summary'), str)}
    scope = canonical_scope(scope)
    key = fingerprint(scope)
    if result is not None:
        records[key] = {'summary': result, 'expires': now + 7 * 86400}
    store.data['summary_repairs_v1'] = dict(sorted(
        records.items(), key=lambda pair: pair[1]['expires'])[-500:])
    if result is not None:
        store.persist()
    return records.get(key)


def has_review_store():
    return _STORE.get() is not None


@lru_cache(maxsize=1)
def editorial_identity():
    """Invalidate semantic results on any deployed editorial code/policy change.

    State/history files and the wall clock are deliberately not policy inputs.
    A process restart after deployment recomputes this identity.
    """
    root = Path(__file__).resolve().parent
    paths = sorted(set(root.glob('news_*.py')) | {
        root / 'doorinews_editor.py', root / 'doorinews_bot.py'})
    return fingerprint([(p.name, hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths])


@lru_cache(maxsize=1)
def compatible_identity():
    """Allow audited release migrations only with the complete release intact.

    The manifest is outside the Python policy identity to avoid a self-hash.
    Any future/mixed source edit disables migration, including cache code edits.
    """
    try:
        root = Path(__file__).resolve().parent
        manifest = json.loads((root / 'news_cache_compatibility.json').read_text(encoding='utf8'))
        if manifest['current_identity'] == editorial_identity():
            previous = manifest.get('previous_identities', [manifest['previous_identity']])
            if isinstance(previous, list) and all(isinstance(p, str) for p in previous):
                return tuple(previous)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def content_result(kind, scope, result=None):
    """Persist a completed pipeline outcome independently of request-cache churn.

    Callers must validate verdicts before writing. This is never a posted record,
    a network-error blacklist, or permission to skip final publication checks.
    """
    scope = canonical_scope(scope)
    store = _STORE.get()
    if store is None:
        return None
    now = store.clock()
    records = store.data.setdefault('content_results_v1', {})
    records = {k: v for k, v in records.items() if isinstance(v, dict)
               and type(v.get('expires')) in (int, float) and v['expires'] > now
               and isinstance(v.get('result'), dict)}
    key = fingerprint([VERSION, editorial_identity(), kind, scope])
    if result is not None:
        records[key] = {'result': result, 'expires': now + CONTENT_TTL}
    entry = records.get(key)
    migrated = False
    if entry is None and result is None and kind in {
            'source_summary', 'image_held', 'event_rejected', 'negative_request', 'event_search_index'}:
        previous = compatible_identity()
        # Check the live identity too: a changed policy never inherits this release.
        try:
            manifest = json.loads((Path(__file__).resolve().parent /
                                   'news_cache_compatibility.json').read_text(encoding='utf8'))
        except (OSError, ValueError):
            manifest = {}
        if previous and manifest.get('current_identity') == editorial_identity():
            for identity in previous:
                old_key = fingerprint([VERSION, identity, kind, scope])
                entry = records.get(old_key)
                if entry is not None:
                    records[key] = records.pop(old_key)  # Preserve original expiration.
                    migrated = True
                    break
    store.data['content_results_v1'] = dict(sorted(
        records.items(), key=lambda pair: pair[1]['expires'])[-MAX_CONTENT_RESULTS:])
    if result is not None or migrated:
        store.persist()
    return dict(entry['result']) if entry else None


def audit_source_identity(scope, reused):
    """Bounded input-hash diagnostics; never retain source text or credentials."""
    store = _STORE.get()
    if store is None:
        return
    now = store.clock()
    records = store.data.setdefault('source_identity_v1', {})
    records = {k: v for k, v in records.items()
               if isinstance(v, dict) and isinstance(v.get('expires'), (int, float))
               and v['expires'] > now}
    key = fingerprint(scope.get('url', ''))
    current = {k: fingerprint(v) for k, v in scope.items() if k != 'url'}
    current['policy'] = editorial_identity()
    old = records.get(key, {}).get('inputs', {})
    changed = sorted(k for k in set(old) | set(current) if old.get(k) != current.get(k))
    if not reused:
        reason = ','.join(changed) if old and changed else (
            '동일 입력: 저장 결과 없음/만료 또는 미완료' if old else '입력 추적 첫 기록')
        store.log('[재검토 후보 입력] ' + reason + ' | ' +
                  ' '.join(str(scope.get('title', '')).split())[:160])
    records[key] = {'inputs': current, 'expires': now + CONTENT_TTL}
    store.data['source_identity_v1'] = dict(sorted(
        records.items(), key=lambda pair: pair[1]['expires'])[-1000:])
    store.persist()


def record_content_reuse(kind, model, reason):
    store = _STORE.get()
    if store is not None:
        store.hits += 1
        store.bucket(model or 'unconfigured', kind)['cache_hits'] += 1
        # Log a bounded reason, never a full source or image payload.
        store.log(f'[내용 판정 재사용] {kind} | ' + ' '.join(str(reason).split())[:240])


@contextmanager
def review_session(state, persist, logger=print):
    store = ReviewStore(state,persist,logger)
    token = _STORE.set(store)
    completed = False
    try:
        yield store
        if store.quota_error:
            raise ReviewQuotaError(store.quota_error)
        completed = True
    finally:
        try:
            runs = store.data.setdefault('recent_runs', [])
            runs.append({'started_at_utc':datetime.fromtimestamp(store.started,timezone.utc).isoformat(),
                         'elapsed_seconds':round(store.clock()-store.started,3),
                         'status':'completed' if completed else 'failed',
                         'api_calls':store.calls,'cache_hits':store.hits,'errors':store.errors,
                         'published':store.published,'estimated_usd':round(store.estimated_usd,9),
                         'missing_usage':store.missing_usage,'unpriced_calls':store.unpriced_calls})
            del runs[:-168]
            store.prune()
            persist()
            logger(f'[AI 실행 합계] API 요청={store.calls} 재사용={store.hits} 오류={store.errors} '
                   f'게시={store.published} 단가계산=${store.estimated_usd:.6f} '
                   f'비용미확정={store.missing_usage+store.unpriced_calls}')
        finally:
            _STORE.reset(token)
