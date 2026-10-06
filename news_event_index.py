"""Deterministic candidate retrieval. No model, network, or publication calls."""
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from urllib.parse import urlsplit, unquote

from news_review_cache import fingerprint, load_local_event_index, save_local_event_index

INDEX_VERSION = 'local-event-index-v34-1'
MAX_RELATED = 12
MAX_HISTORY_CHARS = 18000
STOP = set('the a an in on to for of and with by as from at is are has have new news crypto cryptocurrency bitcoin ethereum says said will can it its this that launches launch announced announces unveils'.split())
STOP |= {'기사','뉴스','발표','밝힘','전함','설명','출시','관련','위해','통해','대한','있는','있다','했다','한다','따르면'}


def words(text):
    text = unicodedata.normalize('NFKC', str(text or '')).casefold()
    result = set()
    for word in re.findall(r'[a-z][a-z0-9]{2,}|[가-힣]{2,}|\d{3,}', text):
        if re.fullmatch('[가-힣]+', word):
            word = re.sub(r'(에서는|에서|으로|에게|에는|은|는|이|가|을|를|의|와|과)$','',word)
        if len(word) >= 2 and word not in STOP:
            result.add(word)
    return result


@lru_cache(maxsize=6000)
def _feature(title, summary, url, token_builder, version):
    # Reuse the editorial bilingual aliases and event patterns. Footer tags and
    # publisher host names do not become evidence for topic matching.
    tokens = sorted(token_builder(dict(title=title, desc=summary, article_text=summary)))
    path = unquote(urlsplit(url).path).replace('-',' ')
    return {'tokens':tokens, 'words':sorted(words(title+' '+summary+' '+path)),
            'title_words':sorted(words(title))}


def feature(record, token_builder, version):
    return _feature(str(record.get('title','')), str(record.get('summary','')),
                    str(record.get('url','')), token_builder, version)


def select_related(candidate, records, token_builder, feature_version):
    """Return all plausible local matches within the budget, or explicitly hold.

    Retrieval never declares a match to be a duplicate. Same-asset presence
    alone is insufficient; stage/date differences rank but do not exclude.
    """
    version = fingerprint([INDEX_VERSION, feature_version])
    saved = load_local_event_index(version)
    index = {}
    built = 0
    for record in records:
        key = fingerprint({k:record.get(k,'') for k in ('id','title','summary','url','source_pub','ts')})
        value = saved.get(key)
        if not (isinstance(value,dict) and all(isinstance(value.get(k),list)
                and all(isinstance(t,str) for t in value[k]) for k in ('tokens','words','title_words'))):
            value = feature(record, token_builder, version)
            built += 1
        index[key] = value
    save_local_event_index(version, index)
    cur = feature(candidate, token_builder, version)
    ct, cw = set(cur['tokens']), set(cur['words'])
    entities = {t for t in ct if t.startswith('entity_')}
    anchors = {t for t in ct if t.startswith(('event_','reference_','subject_'))}
    df = Counter(w for f in index.values() for w in f['words'])
    scored = []
    for record, old in zip(records,index.values()):
        ot, ow = set(old['tokens']), set(old['words'])
        shared = ct & ot
        se = entities & ot
        sa = anchors & ot
        actions = {t for t in shared if t.startswith('action_')}
        objects = {t for t in shared if t.startswith('object_')} - {'object_disclosure'}
        assets = {t for t in shared if t.startswith('asset_')}
        geo = {t for t in shared if t.startswith('geo_')}
        overlap = cw & ow
        rare = {w for w in overlap if df[w] <= max(3,len(records)*.10)}
        title_overlap = set(cur['title_words']) & set(old['title_words'])
        # Broad bilingual recall for the same actor + action/product. Do not
        # discard an old plan when the candidate announces an actual launch.
        old_entities = {t for t in ot if t.startswith('entity_')}
        disjoint_actors = entities and old_entities and not se
        plausible = bool(sa or (se and (objects or (actions and (assets or len(rare)>=2))))
                         or (not disjoint_actors and assets and objects and
                             (actions or 'object_accounting_integration' in objects))
                         or len(rare) >= 3 or len(title_overlap) >= 3)
        if not plausible:
            continue
        lexical = sum(math.log(1+len(records)/(1+df[w])) for w in overlap)
        score = 12*len(sa)+8*len(se)+3*len(objects)+2*len(actions)+len(assets)+len(geo)+lexical
        scored.append((score,record))
    scored.sort(key=lambda row:(-row[0],row[1]['id']))
    stats = {'total':len(records),'indexed_new':built,'index_reused':len(records)-built,
             'matched':len(scored),'sent':0}
    if len(scored)>MAX_RELATED:
        return {'status':'hold','reason':'관련 사건 후보가 비교 한도 12건을 초과해 보류', 'records':[], 'stats':stats}
    # Stable prompt order: an unrelated new article must not invalidate the
    # paid verdict merely because document-frequency scores changed.
    selected = sorted((r for _,r in scored), key=lambda r:r['id'])
    # Do not silently truncate a decisive caveat or send an unbounded history.
    if sum(len(str(r.get('title','')))+len(str(r.get('summary',''))) for r in selected)>MAX_HISTORY_CHARS:
        return {'status':'hold','reason':'관련 사건 근거가 비교 길이 한도를 초과해 보류', 'records':[], 'stats':stats}
    if not selected and records and not (entities or anchors):
        return {'status':'hold','reason':'주체·사건 식별 근거가 부족해 중복 검색 확인 보류', 'records':[], 'stats':stats}
    stats['sent'] = len(selected)
    return {'status':'ok','records':selected,'stats':stats}
