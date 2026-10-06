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

VERSION = 'review-cache-v29-1'
MAX_ENTRIES = 6000
TTL = 72 * 3600
NEGATIVE_TTL = 6 * 3600
MEMORY_TTL = 30 * 24 * 3600
MAX_EVENT_MEMORIES = 120
DURABLE_STAGES = {'summary', 'compression', 'source_review', 'image_review',
                  'event_search', 'event_decision'}
# Standard API USD / million tokens, checked 2026-10-05. Estimates, not invoices.
PRICES = {'gpt-5.4': (2.50, .25, 15.0), 'gpt-5.4-mini': (.75, .075, 4.50)}
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


def _value(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def _number(value):
    return value if type(value) is int and value >= 0 else None


def result_ttl(stage, text):
    """Keep completed verdicts, including holds, until evidence changes/expiry."""
    if stage in DURABLE_STAGES:
        return MEMORY_TTL
    obj = None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and obj.get('decision') == 'uncertain':
            return NEGATIVE_TTL
    except ValueError:
        pass
    if isinstance(obj, dict) and (obj.get('publish') is False or obj.get('approved') is False):
        return NEGATIVE_TTL
    if text.upper() in {'SKIP', '제외', '스킵'}:
        return NEGATIVE_TTL
    return TTL


class ReviewStore:
    def __init__(self, state, persist, logger=print, clock=time.time):
        self.state, self.persist, self.log, self.clock = state, persist, logger, clock
        self.data = state.setdefault('ai_review', {})
        if self.data.get('version') != VERSION:
            self.data['entries'] = {}
            self.data['event_memory_v33'] = {}
        self.data['version'] = VERSION
        self.entries = self.data.setdefault('entries', {})
        self.usage = self.data.setdefault('usage_by_day_utc', {})
        self.calls = self.hits = self.errors = 0
        self.started = self.clock()
        self.published = self.missing_usage = self.unpriced_calls = 0
        self.estimated_usd = 0.0
        self.event_records_reused = self.event_records_reviewed = 0
        self.quota_error = ''
        self.prune()

    def prune(self):
        now = self.clock()
        self.entries = {k:v for k,v in self.entries.items()
                        if isinstance(v,dict) and isinstance(v.get('expires'),(int,float))
                        and v['expires'] > now and isinstance(v.get('text'),str)}
        self.entries = dict(sorted(self.entries.items(), key=lambda kv:kv[1]['expires'])[-MAX_ENTRIES:])
        self.data['entries'] = self.entries
        memories = self.data.get('event_memory_v33', {})
        if not isinstance(memories, dict):
            memories = {}
        memories = {k:v for k,v in memories.items() if isinstance(v,dict)
                    and isinstance(v.get('expires'),(int,float)) and v['expires'] > now
                    and isinstance(v.get('value'),dict)}
        self.data['event_memory_v33'] = dict(sorted(memories.items(),
            key=lambda kv:kv[1]['expires'])[-MAX_EVENT_MEMORIES:])
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
        key = fingerprint([VERSION,model,stage,scope,payload])
        bucket = self.bucket(model,stage)
        entry = self.entries.get(key)
        if entry and entry['expires'] > self.clock() and validator(entry['text']):
            if result_ttl(stage, entry['text']) == MEMORY_TTL:
                entry['expires'] = self.clock() + MEMORY_TTL
            self.hits += 1
            bucket['cache_hits'] += 1
            self.log(f'[AI 검토 재사용] {stage} | {key[:12]}')
            return entry['text']
        self.calls += 1
        bucket['api_calls'] += 1
        try:
            response = client.responses.create(model=model, input=payload)
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
            ttl = result_ttl(stage, text)
            self.entries[key] = {'text':text,'expires':self.clock()+ttl}
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
    response = client.responses.create(model=model,input=payload)
    status = _value(response,'status')
    if status is not None and isinstance(status,str) and status != 'completed':
        return ''
    return str(_value(response,'output_text','') or '').strip()


def record_publication():
    """Call only after Telegram confirms delivery; never count held candidates."""
    store = _STORE.get()
    if store is not None:
        store.published += 1


def load_event_memory(identity):
    store = _STORE.get()
    if store is None:
        return {}
    entry = store.data.get('event_memory_v33', {}).get(identity)
    if not entry or entry['expires'] <= store.clock():
        return {}
    # Work on a copy; only explicitly validated progress is persisted.
    return json.loads(json.dumps(entry['value']))


def save_event_memory(identity, value):
    store = _STORE.get()
    if store is not None:
        store.data.setdefault('event_memory_v33', {})[identity] = {
            'value':value, 'expires':store.clock()+MEMORY_TTL}
        store.prune()
        store.persist()


def record_event_progress(reused=0, reviewed=0):
    store = _STORE.get()
    if store is not None:
        store.event_records_reused += reused
        store.event_records_reviewed += reviewed
        store.log(f'[사건 비교 기억] 재사용 기록={reused} 검사 대상 기록={reviewed}')


def load_local_event_index(version):
    store = _STORE.get()
    if store is None:
        return {}
    index = store.data.get('local_event_index', {})
    if not isinstance(index,dict) or index.get('version') != version:
        return {}
    entries = index.get('entries', {})
    return entries if isinstance(entries,dict) else {}


def save_local_event_index(version, entries):
    store = _STORE.get()
    if store is not None:
        store.data['local_event_index'] = {'version':version, 'entries':dict(list(entries.items())[-6000:])}
        # v33's all-history pair ledger is superseded by the local index. Keep
        # paid exact responses and confirmed publication history untouched.
        memories = store.data.get('event_memory_v33', {})
        for key in list(memories):
            if 'checked' in memories[key].get('value', {}):
                del memories[key]
        store.persist()


def record_local_retrieval(stats, held=False):
    store = _STORE.get()
    if store is not None:
        store.log('[사건 로컬 검색] 전체={total} 인덱스 재사용={index_reused} '
                  '관련={matched} AI 비교 대상={sent} 보류='.format(**stats)+str(held))


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
            runs[-1].update(event_records_reused=store.event_records_reused,
                            event_records_reviewed=store.event_records_reviewed)
            del runs[:-168]
            store.prune()
            persist()
            logger(f'[AI 실행 합계] API 요청={store.calls} 재사용={store.hits} 오류={store.errors} '
                   f'게시={store.published} 단가계산=${store.estimated_usd:.6f} '
                   f'비용미확정={store.missing_usage+store.unpriced_calls}')
        finally:
            _STORE.reset(token)
