#!/usr/bin/env python3
import asyncio
import hashlib
import html
import json
import os
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from inspect import iscoroutine

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8347089705:AAHyKhlvRCNOY5wJqbg8yDvSuQWHSS1zTVs")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@YamingNews")
INITIAL_RUN = os.environ.get("INITIAL_RUN", "false").strip().lower() == "true"

FEEDS = [
    ('CryptoBriefing', 'https://cryptobriefing.com/feed/'),
    ('Cointelegraph', 'https://cointelegraph.com/rss'),
    ('CryptoSlate', 'https://cryptoslate.com/feed'),
    ('TheBlock', 'https://www.theblock.co/rss.xml'),
    ('위처', 'https://watcher.guru/news/feed'),
    ('크립토폴리탄', 'https://www.cryptopolitan.com/feed/'),
    ('더크립토베이식', 'https://thecryptobasic.com/feed/'),
    ('코인게이프', 'https://coingape.com/feed/'),
    ('타입스베틀로이드', 'https://timestabloid.com/feed/'),
    ('데일리호들', 'https://dailyhodl.com/feed/'),
    ('베인크립토', 'https://beincrypto.com/feed/'),
    ('블루밍비트', 'https://bloomingbit.io/rss.xml'),
    ('뉴스비트코인', 'https://news.bitcoin.com/rss'),
    ('코인터크', 'https://en.coin-turk.com/feed/'),
]

PORTFOLIO_COINS = ['BTC','ETH','XRP','XLM','ADA','TRX','BNB','BCH','SHIB','ETC','FLR','ATHENA','ETNA','DOGE']
ECON_KEYWORDS = ['sec','etf','regulation','law','bill','inflation','interest rate','economy','government','bank','approval','legislation','policy']
NEGATIVE_KEYWORDS = []
FINAL_HASHTAGS = ['BTC','비트코인','dooridoori','도리도리','doorinati','도리나티']
MANUAL_TRANSLATIONS = {
    'Ironlight':'아이언라이트','Vorhees':'보어히스','Erik Vorhees':'에릭보어히스',
    'Michael Saylor':'마이클셰일러','Saylor':'셰일러','ShapeShift':'셰이프시프트',
    'Ripple':'리플','Flare':'플레어','FLR':'플레어','ATHENA':'아테나','ETNA':'에테나',
    'Ethena':'에테나','Metaplanet':'메타플래닛','DooriNews':'도리뉴스','Shiba Inu':'시바이누',
    'Shiba':'시바'
}
IGNORED_WORDS = {
    'raises','posts','reports','appeared','appears','launches','launch','publishes','reveals',
    'acquires','funds','boosts','first','second','third','study','trial','trials','tests',
    'report','announces','announced','article','post','tokenized','markets','crypto','briefing',
    'listings','products','platform','analysis','market','digital','security','securities',
    'blockchain','regulated','marketplace','exchange','trading','website','visit'
}
SITE_NAMES = {
    'CryptoBriefing','Cointelegraph','CryptoSlate','TheBlock','WatcherGuru','Cryptopolitan',
    'TheCryptoBasic','CoinGape','TimesTabloid','DailyHodl','BeInCrypto','BloomingBit','NewsBitcoin','CoinTurk'
}
CRYPTO_ACRONYMS = {'XRP','SEC','BTC','ETH','DEFI','NFT','WEB3','ETP','ETF','USDC','USDT','DAO'}
STATE_FILE = 'news_state.json'
MAX_ITEMS_PER_FEED = 12
SUMMARY_SENTENCES = 2

def log(msg: str) -> None:
    print(msg, flush=True)

def http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; DooriNewsBot/2.1)'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')

def normalize_text(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9 ]+', ' ', text).lower()

def story_hash(title: str) -> str:
    clean = re.sub(r'[^a-z0-9 ]', '', title.lower().strip())
    return hashlib.md5(clean.encode('utf-8')).hexdigest()[:12]

def load_state(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(path: str, state: dict):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def is_duplicate(title: str, posted: dict) -> bool:
    return story_hash(title) in posted

def update_posted(title: str, posted: dict):
    posted[story_hash(title)] = {'title': title, 'ts': datetime.now(timezone.utc).isoformat()}

def is_weak_text(text: str) -> bool:
    low = text.lower().strip()
    return (not low) or len(low) < 50 or 'visit website' in low or '웹사이트 방문' in low or bool(re.fullmatch(r'https?://\S+', low))

def extract_meta(html_text: str, names: list[str]) -> str:
    for name in names:
        pats = [
            rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\'](.*?)["\']',
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\'](.*?)["\']',
            rf'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']{re.escape(name)}["\']',
            rf'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']{re.escape(name)}["\']',
        ]
        for pat in pats:
            m = re.search(pat, html_text, re.I | re.S)
            if m:
                return html.unescape(m.group(1)).strip()
    return ""

def fetch_article_meta(url: str) -> tuple[str, str]:
    try:
        html_text = http_get(url, timeout=20)
    except Exception:
        return "", ""
    return (
        extract_meta(html_text, ['og:description','description','twitter:description']),
        extract_meta(html_text, ['og:image','twitter:image'])
    )

def fetch_rss(url: str, max_items: int = MAX_ITEMS_PER_FEED):
    stories = []
    try:
        data = http_get(url, timeout=20)
        root = ET.fromstring(data)
        for item in root.findall('.//item')[:max_items]:
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = (item.findtext('description') or '').strip()
            pub = (item.findtext('pubDate') or '').strip()
            desc_clean = re.sub(r'<[^>]+>', ' ', unescape(desc))
            desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
            image_url = ''
            try:
                media = item.find('{http://search.yahoo.com/mrss/}content') or item.find('{http://search.yahoo.com/mrss/}thumbnail')
                if media is not None and media.attrib.get('url'):
                    image_url = media.attrib['url']
                else:
                    enclosure = item.find('enclosure')
                    if enclosure is not None and enclosure.attrib.get('url'):
                        image_url = enclosure.attrib['url']
            except Exception:
                image_url = ''
            article_desc, article_img = ('','')
            if link:
                article_desc, article_img = fetch_article_meta(link)
            if not image_url and article_img:
                image_url = article_img
            if is_weak_text(desc_clean) and article_desc:
                desc_clean = article_desc
            if title and link:
                stories.append({'title': unescape(title), 'url': link, 'desc': desc_clean, 'pub': pub, 'image_url': image_url})
    except Exception as e:
        log(f"Error fetching {url}: {e}")
    return stories

def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str]) -> bool:
    text = normalize_text(story['title'] + ' ' + story.get('desc', ''))
    for neg in NEGATIVE_KEYWORDS:
        if normalize_text(neg) in text:
            return False
    for coin in coins:
        if normalize_text(coin) in text:
            return True
    for kw in econ_keywords:
        if normalize_text(kw) in text:
            return True
    return False

def clean_source_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'The post.*', ' ', text, flags=re.I)
    text = re.sub(r'first appeared on.*', ' ', text, flags=re.I)
    text = re.sub(r'\b(?:' + '|'.join(map(re.escape, SITE_NAMES)) + r')\b', ' ', text, flags=re.I)
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'웹사이트 방문', ' ', text)
    text = re.sub(r'visit website', ' ', text, flags=re.I)
    text = re.sub(r'\[\.\.\.\]|\[\]|\.\.\.|…', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_bad_line(line: str) -> bool:
    low = line.lower().strip()
    return (not low) or ('visit website' in low) or ('웹사이트 방문' in low) or ('?' in line) or ('？' in line) or bool(re.fullmatch(r'https?://\S+', low))

def summarize_text(text: str, title: str = "", max_sentences: int = SUMMARY_SENTENCES) -> str:
    text = clean_source_text(text)
    if is_weak_text(text):
        text = title
    sentences = re.split(r'(?<=[.!?])\s+', text)
    picked = []
    for s in sentences:
        s = s.strip()
        if not s or is_bad_line(s):
            continue
        picked.append(s)
        if len(picked) >= max_sentences:
            break
    return ' '.join(picked) if picked else clean_source_text(title)

def translate_text_to_korean(text: str) -> str:
    if not text:
        return ""
    try:
        from googletrans import Translator  # type: ignore
        translator = Translator()
        result = translator.translate(text, dest='ko')
        if iscoroutine(result):
            result = asyncio.run(result)
        return result.text
    except Exception:
        try:
            from googletrans import Translator  # type: ignore
            async def _translate(src: str) -> str:
                async with Translator() as trans:
                    r = await trans.translate(src, dest='ko')
                    return r.text
            return asyncio.run(_translate(text))
        except Exception:
            return text

def normalize_style(text: str) -> str:
    rules = [
        (r'사용됩니다\.?', '사용됨'),
        (r'있습니다\.?', '있음'),
        (r'내렸다\.?', '내림'),
        (r'늘렸습니다\.?', '늘림'),
        (r'불러일으킵니다\.?', '불러일으킴'),
        (r'미칩니다\.?', '미침'),
        (r'나타냅니다\.?', '나타냄'),
        (r'했습니다\.?', '함'),
        (r'하였습니다\.?', '함'),
        (r'합니다\.?', '함'),
        (r'하고 있습니다\.?', '하고 있음'),
        (r'하고 있다\.?', '하고 있음'),
        (r'기록했습니다\.?', '기록'),
        (r'승인했습니다\.?', '승인'),
        (r'였습니다\.?', '임'),
        (r'입니다\.?', '임'),
        (r'이었습니다\.?', '임'),
        (r'이다\.?', '임'),
    ]
    leftovers = re.findall(r'[\w가-힣]+(?:했습니다|하였습니다|합니다|있습니다|됩니다|나타냅니다|미칩니다)', text)
    if leftovers:
        log("말투 치환 추가 필요 후보: " + ", ".join(leftovers[:10]))
    for pat, rep in rules:
        text = re.sub(pat, rep, text)
    text = re.sub(r'\[\.\.\.\]|\.\.\.|…', ' ', text)
    text = re.sub(r'\s*:\s*\[\s*\]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fix_truncated_phrases(text: str) -> str:
    fixes = {
        'USDC는': 'USDC는 전송량 경쟁 구도 변화의 중심에 섬',
        '잡담이': '관련 논의도 이어지는 중',
        '공급을': '공급 확대 흐름도 이어지는 중',
        'JPMorgan은 또한 일부 민간 신용을 인하함': 'JPMorgan은 일부 민간 신용도 함께 인하',
        '위태로운 것은 달러 연계 여부이다': '핵심 변수는 달러 연계 유지 여부로 좁혀짐',
    }
    for k, v in fixes.items():
        text = re.sub(r'\b' + re.escape(k), v, text)
    text = re.sub(r'\[\.\.\.\]|\.\.\.|…', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_entities(story: dict, max_tags: int = 3) -> list[str]:
    title = story.get('title', '')
    desc = story.get('desc', '')
    text = title + " " + desc
    entities = []
    for key in sorted(MANUAL_TRANSLATIONS.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(key) + r'\b', text, re.I):
            entities.append(key)
    for coin in PORTFOLIO_COINS:
        if re.search(r'\b' + re.escape(coin) + r'\b', text, re.I):
            entities.append(coin)
    grouped = re.findall(r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}|[A-Z]{2,6})\b', title)
    for token in grouped:
        if token in SITE_NAMES or token.lower() in {w.lower() for w in IGNORED_WORDS}:
            continue
        entities.append(token)
    seen = set()
    result = []
    for ent in entities:
        k = ent.lower()
        if k not in seen:
            result.append(ent)
            seen.add(k)
    result.sort(key=lambda e: text.lower().find(e.lower()) if text.lower().find(e.lower()) >= 0 else 99999)
    return result[:max_tags]

def entity_korean_name(entity: str) -> str:
    if entity in MANUAL_TRANSLATIONS:
        return MANUAL_TRANSLATIONS[entity]
    translated = translate_text_to_korean(entity).replace(' ', '')
    return translated or entity.replace(' ', '')

def inject_entity_hashtags(summary: str, entities: list[str]) -> tuple[str, list[str]]:
    text = summary
    final_tags = []
    for ent in sorted(entities, key=len, reverse=True):
        ent_upper = ent.upper()
        if ent_upper in PORTFOLIO_COINS or ent_upper in CRYPTO_ACRONYMS:
            tag = f'#{ent_upper}'
            if tag not in final_tags:
                final_tags.append(tag)
            continue
        korean = entity_korean_name(ent)
        tag_text = '#' + korean.replace(' ', '')
        eng_tag = '#' + ent.replace(' ', '')
        if eng_tag not in final_tags:
            final_tags.append(eng_tag)
        replaced = False
        for base in [korean, ent]:
            for p in ['가','이','은','는','를','을','의','와','과','로']:
                new_text, count = re.subn(re.escape(base + p), f'{tag_text} {p}', text, count=1)
                if count:
                    text = new_text
                    replaced = True
                    break
            if replaced:
                break
        if not replaced:
            for base in [korean, ent]:
                new_text, count = re.subn(re.escape(base), tag_text, text, count=1)
                if count:
                    text = new_text
                    break
    return text, final_tags

def build_message(story: dict) -> str:
    raw_summary = summarize_text(story.get('desc', ''), title=story.get('title', ''), max_sentences=SUMMARY_SENTENCES)
    summary_ko = translate_text_to_korean(raw_summary)
    summary_ko = fix_truncated_phrases(summary_ko)
    summary_ko = normalize_style(summary_ko)
    entities = extract_entities(story, max_tags=3)
    summary_ko, dynamic_tags = inject_entity_hashtags(summary_ko, entities)
    lines = []
    for line in re.split(r'(?<=[.!?])\s+|\n+', summary_ko):
        line = line.strip()
        if line and not is_bad_line(line):
            lines.append(line)
    if not lines:
        lines = [normalize_style(translate_text_to_korean(clean_source_text(story.get('title', ''))))]
    summary = re.sub(r'\s+', ' ', '\n'.join(lines)).strip()
    footer_tags = dynamic_tags + [f'#{t}' for t in FINAL_HASHTAGS]
    seen = set()
    dedup = []
    for t in footer_tags:
        if t not in seen:
            dedup.append(t)
            seen.add(t)
    parts = [
        html.escape(summary),
        '🌐 <a href="http://t.me/Doorinews">공식 글로벌 실시간 도리뉴스</a>',
        f'<a href="{html.escape(story["url"])}">출처</a>',
        ' '.join(html.escape(t) for t in dedup)
    ]
    return '\n\n'.join(parts)

def send_telegram_message(token: str, channel: str, message: str) -> bool:
    if not token or not channel:
        log("Telegram token or channel not set")
        return False
    payload = json.dumps({
        'chat_id': channel,
        'text': message[:4000],
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }).encode('utf-8')
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            log(resp.read().decode('utf-8', errors='ignore'))
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        log(f"Error sending message: HTTP {e.code} {e.reason} | {body}")
        return False
    except Exception as e:
        log(f"Error sending message: {e}")
        return False

def send_telegram_photo(token: str, channel: str, image_url: str, caption: str) -> bool:
    if not token or not channel:
        log("Telegram token or channel not set")
        return False
    if not image_url:
        return send_telegram_message(token, channel, caption)
    while len(caption.encode('utf-8')) > 1000:
        caption = caption[:-1]
    payload = json.dumps({
        'chat_id': channel,
        'photo': image_url,
        'caption': caption,
        'parse_mode': 'HTML'
    }).encode('utf-8')
    url = f'https://api.telegram.org/bot{token}/sendPhoto'
    try:
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=25) as resp:
            log(resp.read().decode('utf-8', errors='ignore'))
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        log(f"Error sending photo: HTTP {e.code} {e.reason} | {body}. Falling back to text message.")
        return send_telegram_message(token, channel, caption)
    except Exception as e:
        log(f"Error sending photo: {e}. Falling back to text message.")
        return send_telegram_message(token, channel, caption)

def main():
    log("Bot starting...")
    state = load_state(STATE_FILE)
    posted = state.get('posted', {})
    collected = []
    for name, feed_url in FEEDS:
        stories = fetch_rss(feed_url, max_items=MAX_ITEMS_PER_FEED)
        log(f"{name}: {len(stories)}개 수집")
        collected.extend(stories)
    filtered = [s for s in collected if matches_keywords(s, PORTFOLIO_COINS, ECON_KEYWORDS)]
    log(f"전체 수집 {len(collected)}개 / 필터 통과 {len(filtered)}개")
    new_stories = []
    for s in filtered:
        if not is_duplicate(s['title'], posted):
            new_stories.append(s)
            update_posted(s['title'], posted)
    log(f"중복 제거 후 {len(new_stories)}개")
    state['posted'] = posted
    save_state(STATE_FILE, state)
    for story in new_stories:
        if INITIAL_RUN:
            log(f"Initial run skip: {story['title']}")
            continue
        msg = build_message(story)
        ok = send_telegram_photo(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, story.get('image_url', ''), msg)
        if ok:
            log(f"Posted: {story['title']}")
        else:
            log(f"Failed: {story['title']}")
        time.sleep(1)

if __name__ == '__main__':
    main()
