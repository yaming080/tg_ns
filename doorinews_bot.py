
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
from difflib import SequenceMatcher

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
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
    ('토큰포스트', 'https://www.tokenpost.kr/rss'),
	('코인데스크', 'https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml'),
	('크립토타임즈', 'https://www.cryptotimes.io/feed/'),
	('비트코이니스트', 'https://bitcoinist.com/feed/'),
	('크립토뉴스', 'https://cryptonews.com/rss/'),
	('코인에디션', 'https://coinedition.com/feed/'),
	('크립토포테이토', 'https://cryptopotato.com/feed/'),
	('크립토뉴스플레쉬', 'https://crypto-news-flash.com/feed/'),
	('더뉴스크립토', 'https://thenewscrypto.com/feed/'),
	('유투데이', 'https://u.today/rss.php'),
	('비트저널', 'https://thebitjournal.com/feed/'),
	
]

PORTFOLIO_COINS = ['BTC','ETH','XRP','XLM','ADA','TRX','BNB','BCH','SHIB','ETC','FLR','ATHENA','ENA','USDC','USDT']

OTHER_COINS = [
    'HYPE','HYPERLIQUID','SOL','DOGE','AVAX','DOT','MATIC','POL','LINK','LTC','ATOM',
    'ARB','OP','SUI','APT','PEPE','WIF','BONK','INJ','RNDR','NEAR',
    'FIL','HBAR','TIA','KAS','TAO','ICP','UNI','AAVE','MKR','TRUMP',
    'METAWIN','PI','WLD','RIVER','G COIN','PLAYNANCES','LDO', 'LIDO', 'AKT', 'AKASH', 'AKASH NETWORK'
]

ECON_KEYWORDS = ['sec','etf','regulation','law','bill','inflation','interest rate','economy','government','bank','approval','legislation','policy','tariff','Fed','korea','stablecoin','tokenization','custody','seed phrase','treasury','cftc','occ','ipo',
    'basel','basel iii','liquidity','hqla','odl','on-demand liquidity',
'hearing','senate','house','committee','license','margin','collateral','oil','crude','lng','sanction','tariff','tax','income tax','unemployment',
    'jobs','claims','fed','rate hike','treasury strategy','geopolitics','war','gold','digital gold','quantum','bip360','recovery trust','creditor','distribution',
    'ipo','lawsuit','treasury strategy','predictive market']

KOREAN_KEYWORDS = [
    '비트코인','이더리움','리플','스텔라','에이다','트론','바이낸스코인','비트코인캐시','시바이누','시바','스테이블코인','토큰화','수탁','시드문구',
    'ETF','현물 ETF','SEC','CFTC','OCC',
    '규제','법안','입법','정책','승인','소송',
    '연준','금리','금리인상','금리인하','인플레이션',
    '경제','정부','은행','국채','재무부',
    '관세','제재','유가','원유','LNG',
    '상원','하원','청문회','위원회',
    '한국','국내','브라질','중국','일본','미국','이란','이스라엘','카타르',
    '실업수당','고용','고용지표','기관','유동성','배당금','채권자',
    '양자','컴퓨팅','공격','방지','배포','금','디지털 금','세계금협회',
    '예측시장','차량공유','카풀','거래소','감독'
]

NEGATIVE_KEYWORDS = [
    'newsletter', 'the daily', '더데일리', '뉴스레터', '발췌', '발췌한 것임',
    '다음은', '게스트 게시물', '오늘의 토큰운세',
    '토큰운세', '띠별 토큰 운세',
    '투자참고용이 아닌',
    '심리적 환기와 재미를 위해',
    '투자 조언도 아님',
    '일일 동향 및 이벤트',
    '토큰포스트마켓에 따르면',
    '소식통에 따르면',
    '관계자에 따르면',
    '업계에 따르면',
    '시장에 따르면', '처음 등장함',
    '본 콘텐츠는 특정 종목이나 자산에 대한 투자 조언이 아니며',
    '변동성 높은 시장에서 흔들리지 않는 투자 마인드를 가꾸기 위한 심리적 환기 목적으로 제공됩니다',
    '심리적 환기 목적으로 제공됩니다',
    'daily events',
    'crypto today',
    'what happened in crypto today',
    'guest post', 'guest article', 'op-ed', 'analysis by',
    'daily update', 'economic update', 'market update',
    'how to build', 'platform infrastructure', 'investment platform',
    'price prediction', 'forecast', 'will it reach', 'can it reach',
    'presale', 'pre-sale', 'launch week', 'turns launch week',
    'pi network', 'g coin', 'playnances', 'metawin', 'river', 'wld', 'avax', 'solana', 'dogwifhat', 'wif',
    'hyperliquid', 'hype token', 'hype etf',
    'alex bores', 'sam bankman-fried', 'democratic primary',
    'first appeared on',
    '처음 게재되었',
    '처음 게재되었습니다',
    'times tabloid에 처음 게재',
    'timestabloid에 처음 게재',
    'ATH 대비',
    '토큰포스트',
    '투자 심리',
    '본 콘텐츠는','과매수 신호가','과매도 신호','코인데스크에 따르면',
    'coindesk에 따르면',
    'cryptonews 에 처음 등장함',
    'cryptonews에 처음 등장함',
    'crypto biz:',
    'crypto biz',
    'coindesk according to',
    'cryptonews first appeared','CryptoBriefing','Crypto Briefing','Cointelegraph','CryptoSlate','TheBlock','WatcherGuru','Cryptopolitan','처음으로 게재되었음','데드크로스','Death Cross',
    'TheCryptoBasic','CoinGape','TimesTabloid','DailyHodl','BeInCrypto','BloomingBit','NewsBitcoin','CoinTurk', '.com News', '코인 소식 중 중요한 내용만 PiCK 해서 보세요', '뉴스 속보를 제공해요','게시물임','청산','하락','급락','Crypto Briefing 에서','황정수의 글로벌 체크인','defillama.com','하락함','청산됨','매도 압력',
    
]
FINAL_HASHTAGS = ['BTC','비트코인','dooridoori','도리도리','doorinati','도리나티']


MANUAL_TRANSLATIONS = {
    'Ironlight': '아이언라이트',
    'Vorhees': '보어히스',
    'Erik Vorhees': '에릭보어히스',
    'Michael Saylor': '마이클세일러',
    'Saylor': '세일러',
    'Robert Kiyosaki': '로버트기요사키',
    'Paul Atkins': '폴앳킨스',
    'David Schwartz': '데이비드슈워츠',
    'Mike Novogratz': '마이크노보그라츠',
    'Sam Altman': '샘알트만',
    'Elon Musk': '일론머스크',
    'ShapeShift': '셰이프시프트',
    'Brad Garlinghouse': '갈링하우스',
    'David Schwartz': '데이비드슈워츠',
    'Monica Long': '모니카롱',
    'Vitalik Buterin': '비탈릭부텔린',
    'Satoshi Nakamoto': '사토시나카모토',
    'Elon Musk': '일론머스크',
    'Justin Sun': '저스틴썬',
    'Jed McCaleb': '제드맥케일럽',
    'Charles Hoskinson': '찰스호스킨슨',    
    'Goldman Sachs': '골드만삭스',
    'Goldman':'골드만',
    'coinbase':'코인베이스',
    'Strategy': '스트래티지',
    'Donald Trump': '도널드트럼프',
    'Trump': '트럼프',
    'Robinhood': '로빈후드',
    'Tether': '테더',
    'Ripple': '리플',
    'Flare': '플레어',
    'FLR': 'FLR',
    'ATHENA': '아테나',
    'ENA': '에테나',
    'Ethena': '에테나',
    'Metaplanet': '메타플래닛',
    'DooriNews': '도리뉴스',
    'Shiba Inu': '시바이누',
    '시바견':'시바이누',
    '시바 이누':'시바이누',
    '시바 이 누':'시바이누',
    '시바이 누':'시바이누',
    'Shibarium':'시바리움',
    'Swift': 'SWIFT',
    'Genius Act':'지니어스법안',
	'Genius':'지니어스',
	'Act':'법안',
    'ICE':'ICE',
    'CLARITY':'클래리티',
    'stablecoin':'스테이블코인',
    'Blackrock':'블랙록',
	'MoonPay':'문페이',
    
    

    'Fed': '연준',
    'Federal Reserve': '연준',
    'Treasury': '재무부',
    'White House': '백악관',
    'Brazil': '브라질',
    'China': '중국',
    'Japan': '일본',
    'Korea': '한국',
    'South Korea': '한국',
    'United States': '미국',
    'Iran': '이란',
    'Israel': '이스라엘',
    'Qatar': '카타르',
    'india':'인도',
    'myanmar':'미얀마',
    'mastercard': '마스터카드',
    'Google':'구글',
    'SEC': 'SEC',
    'CFTC': 'CFTC',
    'OCC': 'OCC',
    'ETF': 'ETF',
    'IPO': 'IPO',
    'CTO': 'CTO',
    'XRP': 'XRP',
    'XLM': 'XLM',
    'BTC': 'BTC',
    'ETH': 'ETH',
    'SHIB': 'SHIB',
    'USDC': 'USDC',
    'USDT': 'USDT',
    'XAUT': 'XAUT',
    'SOL': 'SOL',
    'DOGE': 'DOGE',

    'Bitcoin': '비트코인',
    'Ethereum': '이더리움',
    'Stablecoin': '스테이블코인',
    'Tokenization': '토큰화',
    'Custody': '수탁',
    'Seed Phrase': '시드문구',
    'Lawsuit': '소송',
    'Regulation': '규제',
    'Interpretation': '해석',

    'DeFi': 'DeFi',
    'NFT': 'NFT',
    'Web3': 'Web3',

    'BitMine': 'BitMine',
    'Tom Lee': '톰리',
    'Thomasg.eth': 'Thomasgeth',
    'Time Traveler': 'TimeTraveler',
    'John Squire': 'JohnSquire',

    'Uniswap': '유니스왑',
    'Hayden Adams': 'HaydenAdams',

    'Jerome Powell': '제롬파월',
    'Powell': '파월',
    
    'Japan': '일본',
    'United States': '미국',
    'US': '미국',
    'America': 'America',
    '미국': '미국',

    'Nevada': '네비다주',

    'J.P. Morgan': 'JPMorgan',
    'JP Morgan': 'JPMorgan',
    'JPMorgan': 'JPMorgan',
    'Ryde': '라이드',
    'Bybit': '바이비트',
    'Tether': '테더',
    'Ledger': 'Ledger',
    'Circle': '서클',
    'MoneyGram': '머니그램',
    'Upbit': '업비트',
    'Bithumb': '빗썸',    
    'Binance': '바이낸스',
    'Apple': 'Apple',
    'PayPal': '페이팔',
    'Robinhood': '로빈후드',
    'Stripe': '스트라이프',
    'Gemini': '제미니',
    'Kalshi': '칼시',
    'Zedxion': '제드시온',
    'Evernorth Holdings': '에버노스',
    'Evernorth': '에버노스',
    'XRPLedger': 'XRPLedger',
    'World Gold Council': '세계금협회',
    'Gold': '금',
    'Digital Gold': '디지털금',
    'Silver':'은',
    'Bitcoin Quantum': '비트코인퀀텀',
    'BIP360': 'BIP360',
    'OpenAI': 'OpenAI',
    'Anthropic': 'Anthropic',
    'Google': 'Google',
    'Super Micro': '슈퍼마이크로',
    'AI': 'AI',
    'LNG': 'LNG',
    'BAZAN': '바잔',
    'California': '캘리포니아',
    'Morgan Stanley': '모건스탠리',
    'Kraken': '크라켄',
    'coinbase':'코인베이스',
    'Hidden Road': '히든로드',
    'MorganStanley':'모건스탠리',


}
IGNORED_WORDS = {
    'raises','posts','reports','appeared','appears','launches','launch','publishes','reveals',
    'acquires','funds','boosts','first','second','third','study','trial','trials','tests',
    'report','announces','announced','article','post','tokenized','markets','crypto','briefing',
    'listings','products','platform','analysis','market','digital','security','securities',
    'blockchain','regulated','marketplace','exchange','trading','website','visit',
    'records','record','says','said','say',
    'bridge','bridges','unlocks','unlock',
    'spikes','spike','activity','recent',
    'true','traditional','network',
    'here','what','about','if','daily','newsletter','excerpt','excerpts',
    'underpriced','asset','highlights','early','top','news',
    'regulation','EconomicGrowth', 'MarketsAreBetting', 'this','level','could','trigger','million','long','squeeze',
    'here','what','about','if','will','run','top','highlights','passes',
    'surprise','you','says','underpriced','asset','needs','hit',
    'does','this','mean','reserve','errors','year','peak','above',
    'insufficient','institutional','deals','long','game','hitting',
'metals','investments','hard','prices','fall','early','except','before','time','traveler','sell','one','time', 'hours', 'hour', 'market', 'markets', 'today', 'update',
    'daily', 'briefing', 'analysis', 'guest', 'post', 'article',
    'gas', 'prices', 'bond', 'panic', 'campaign', 'event', 'launch'
}
SITE_NAMES = {
    'CryptoBriefing','Cointelegraph','CryptoSlate','TheBlock','WatcherGuru','Cryptopolitan',
    'TheCryptoBasic','CoinGape','TimesTabloid','DailyHodl','BeInCrypto','BloomingBit','NewsBitcoin','CoinTurk'
}
CRYPTO_ACRONYMS = {'XRP','XLM','SEC','CFTC','OCC','BTC','ETH','USDC','USDT','XAUT',
    'DEFI','NFT','WEB3','ETP','ETF','DAO','IPO','CTO','LNG','AI',
}
STATE_FILE = 'news_state.json'
MAX_ITEMS_PER_FEED = 8
SUMMARY_SENTENCES = 4

def log(msg: str) -> None:
    print(msg, flush=True)

def http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; DooriNewsBot/2.1)'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')

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
        html_text = http_get(url, timeout=8)
    except Exception:
        return "", ""
    return (
        extract_meta(html_text, ['og:description','description','twitter:description']),
        extract_meta(html_text, ['og:image','twitter:image'])
    )

def fetch_rss(url: str, max_items: int = MAX_ITEMS_PER_FEED):
    stories = []
    try:
        data = http_get(url, timeout=12)
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

                if not image_url:
                    for child in item:
                        tag = str(child.tag).lower()
                        if 'thumbnail' in tag or 'content' in tag:
                            cand = child.attrib.get('url', '').strip()
                            if cand.startswith('http'):
                                image_url = cand
                                break
            except Exception:
                image_url = ''

            # 속도 개선용: 기사 원문 메타 추가 수집 비활성화
            article_desc, article_img = ('', '')
            if (not image_url) or is_weak_text(desc_clean):
                article_desc, article_img = fetch_article_meta(link)

            if not image_url and article_img:
                image_url = article_img

            if is_weak_text(desc_clean) and article_desc:
                desc_clean = article_desc

            if title and link:
                stories.append({
                    'title': unescape(title),
                    'url': link,
                    'desc': desc_clean,
                    'pub': pub,
                    'image_url': image_url
                })
    except Exception as e:
        log(f"Error fetching {url}: {e}")
    return stories

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'[^a-z0-9가-힣\s]', ' ', text)

    noise_words = [
        'says', 'said', 'claims', 'claim', 'predicts', 'predict', 'analyst', 'analysts',
        'expert', 'experts', 'report', 'reports', 'reported',
        'according to', 'could', 'may', 'might', 'will',
        'price prediction', 'forecast', 'outlook',
        'surges', 'jumps', 'rises', 'falls', 'drops',
        'here is', 'here’s', 'what this means', 'what it means'
    ]

    for w in noise_words:
        text = text.replace(w, ' ')

    text = re.sub(r'\s+', ' ', text).strip()
    return text

def contains_exact_term(text: str, term: str) -> bool:
    norm_text = normalize_text(text)
    norm_term = normalize_text(term)

    if not norm_term:
        return False

    pattern = rf'(^|\s){re.escape(norm_term)}($|\s)'
    return re.search(pattern, norm_text) is not None

def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
    raw_text = (story.get('title', '') + ' ' + story.get('desc', '')).strip()
    text = normalize_text(raw_text)
    raw_lower = raw_text.lower()

    for neg in NEGATIVE_KEYWORDS:
        if neg.lower() in raw_lower:
            print(f"[NEGATIVE 제외] {story.get('title', '')} / {neg}")
            return False

    allowed_coin_found = any(contains_exact_term(raw_text, c) for c in coins)
    if allowed_coin_found:
        print(f"[허용코인 통과] {story.get('title', '')}")
        return True

    other_coin_found = any(contains_exact_term(raw_text, c) for c in OTHER_COINS)
    if other_coin_found:
        print(f"[기타코인 제외] {story.get('title', '')}")
        return False

    ai_allow_terms = ['openai', 'nvidia', 'amazon', 'google', 'alphabet', 'meta', 'anthropic', 'xai', 'grok']
    if any(contains_exact_term(raw_text, term) for term in ai_allow_terms):
        print(f"[AI/기업기사 통과] {story.get('title', '')}")
        return True

    policy_allow_terms = ['stablecoin', 'sec', 'cftc', 'etf', 'law', 'regulation', 'fed', 'inflation', 'bank', 'treasury']
    policy_hits = sum(1 for term in policy_allow_terms if contains_exact_term(raw_text, term))
    if policy_hits >= 2:
        print(f"[정책/거시 통과] {story.get('title', '')}")
        return True

    for kw in econ_keywords:
        if normalize_text(kw) in text:
            print(f"[경제키워드 통과] {story.get('title', '')} / {kw}")
            return True

    for kw in korean_keywords:
        if kw.lower() in raw_lower:
            print(f"[한글키워드 통과] {story.get('title', '')} / {kw}")
            return True

    print(f"[필터미통과] {story.get('title', '')}")
    return False
	
def is_bad_line(line: str) -> bool:
    low = line.lower().strip()
    return (not low) or ('visit website' in low) or ('웹사이트 방문' in low) or ('?' in line) or ('？' in line) or bool(re.fullmatch(r'https?://\S+', low))

def score_sentence(s: str, title: str = "") -> int:
    low = s.lower()
    score = 0

    important_terms = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'xrp', 'ripple',
        'etf', 'sec', 'fed', 'inflation', 'interest rate',
        'stablecoin', 'tokenization', 'lawsuit', 'approval',
        'exchange', 'binance', 'coinbase', 'blackrock'
    ]

    for term in important_terms:
        if term in low:
            score += 3

    if re.search(r'\d', s):
        score += 2

    if len(s) < 25:
        score -= 1
    if len(s) > 140:
        score -= 1

    title_words = set(re.findall(r'[A-Za-z0-9가-힣]+', title.lower()))
    sent_words = set(re.findall(r'[A-Za-z0-9가-힣]+', low))
    score += len(title_words & sent_words)

    if 'according to' in low or 'first appeared' in low:
        score -= 5

    return score

def summarize_text(text: str, title: str = "", max_sentences: int = SUMMARY_SENTENCES) -> str:
    text = cleanup_text(text)
    title = cleanup_text(title)

    if is_weak_text(text):
        text = title

    sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
    usable = []

    for s in sentences:
        s = s.strip()
        if not s or is_bad_line(s):
            continue
        usable.append(s)

    if not usable:
        return title

    # 중요도 높은 문장부터 정렬
    usable.sort(key=lambda s: score_sentence(s, title), reverse=True)

    picked = []
    for s in usable:
        if s not in picked:
            picked.append(s)
        if len(picked) >= max_sentences:
            break

    summary = ' '.join(picked)
    summary = re.sub(r'\s+', ' ', summary).strip()

    # 너무 길 때만 완화된 제한
    if len(summary) > 220:
        summary = summary[:220].rsplit(' ', 1)[0].strip()

    return summary
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
        (r'습니다\.?', '음'),
        (r'알려졌습니다\.?', '알려짐'),
        (r'알려졌다\.?', '알려짐'),
        (r'밀렸다\.?', '밀림'),
        (r'밀렸습니다\.?', '밀림'),
        (r'했다\.?', '했음'),
        (r'됐다\.?', '됨'),
        (r'알려졌습니다\.?', '알려짐'),
        (r'졌다\.?', '졌음'),
        (r'됩니다\.?', '됨'),
        (r'있다\.?', '있음'),
    ]

    leftovers = re.findall(r'[\w가-힣]+(?:했습니다|하였습니다|합니다|있습니다|됩니다|나타냅니다|미칩니다)', text)
    if leftovers:
        log("말투 치환 추가 필요 후보: " + ", ".join(leftovers[:10]))

    for pat, rep in rules:
        text = re.sub(pat, rep, text)

    text = re.sub(r'\[\.\.\.\]|\.\.\.|…', ' ', text)
    text = re.sub(r'\s*:\s*\[\s*\]', ' ', text)
    text = re.sub(r'([가-힣])([A-Z][a-zA-Z]+)', r'\1 \2', text)
    text = re.sub(r'([가-힣])(#)', r'\1 #', text)
    text = re.sub(r'(#\w+)([가-힣])', r'\1 \2', text)
    text = re.sub(r'\s+', ' ', text).strip()

    text = re.sub(r'([가-힣]+)음고 말함', r'\1음', text)
    text = re.sub(r'([가-힣]+)음고 밝힘', r'\1음', text)
    text = re.sub(r'([가-힣]+)다고 말함', r'\1', text)
    text = re.sub(r'([가-힣]+)다고 밝힘', r'\1', text)
    text = re.sub(r'([가-힣]+)라고 말함', r'\1', text)
    text = re.sub(r'([가-힣]+)라고 밝힘', r'\1', text)
    text = re.sub(r'했다고 말함$', '했음', text)
    text = re.sub(r'했다고 밝힘$', '했음', text)
    text = re.sub(r'했다고 전함$', '했음', text)
    text = re.sub(r'이어질 것으로 봄고 말함$', '이어질 것으로 봄', text)

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

def extract_entities(story: dict, max_tags: int = 8) -> list[str]:
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

    NO_TAG_WORDS = {'데이터','환','새로운','계략','가격','천재','행동','등장함','선도적인','올해에도','더','소송','승인','솔라나',
					'SOL','수요','세부','연구원','실패','북극성','개선','경고하는','순간','역할','여기요','피바다','실행자'}

    for ent in sorted(entities, key=len, reverse=True):
        ent = ent.strip()
        if not ent:
            continue

        if ent.lower() in {w.lower() for w in NO_TAG_WORDS}:
            continue

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
            for p in ['가','이','은','는','를','을','의','와','과','로','도','만','에서','에게','까지']:
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

def cleanup_text(text: str) -> str:
    text = re.sub(r'@([A-Za-z0-9_\.]+)', r'\1', text)

    bad_phrases = [
        '다음 기사는',
        '뉴스레터',
        '발췌한 것임',
        '[]로 시작됩니다',
        '[]를 제외하고',
        '[]'
    ]

    for p in bad_phrases:
        text = text.replace(p, '')

    text = re.sub(r'.*?Crypto Briefing에 처음 등장(?:함|했다)\.?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*?크립토 브리핑\(Crypto Briefing\)에 처음 등장(?:함|했다)\.?', '', text)
    text = re.sub(r'.*?Crypto Briefing에 처음 게재되(?:었음|었다|었습니?다)\.?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*?크립토 브리핑\(Crypto Briefing\)에 처음 게재되(?:었음|었다|었습니?다)\.?', '', text)

    text = re.sub(r'.*?first appeared on.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*?처음 게재되(?:었|었습|었음).*', '', text)
    text = re.sub(r'.*?Times Tabloid에 처음 게재되(?:었|었습|었음).*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*?TimesTabloid에 처음 게재되(?:었|었습|었음).*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'코인데스크에 따르면[, ]*', '', text, flags=re.I)
    text = re.sub(r'cryptonews\s*에?\s*처음 등장함', '', text, flags=re.I)
    text = re.sub(r'crypto\s*biz:\s*', '', text, flags=re.I)

    text = text.replace('포스트가 ', '')
    text = text.replace('게시물이 ', '')
    text = text.replace('게재물이 ', '')
    text = text.replace('라는 포스트가 ', '')
    text = text.replace('라는 게시물이 ', '')
    text = text.replace('Crypto Briefing 에 처음 등장함', '')

    text = re.sub(r'^[^.!?\n]{0,40}에 따르면[, ]*', '', text)
    text = re.sub(r'본 콘텐츠는 특정 종목이나 자산에 대한 투자 조언이 아니며[^.!?\n]*', '', text)
    text = re.sub(r'변동성 높은 시장에서 흔들리지 않는 투자 마인드를 가꾸기 위한 심리적 환기 목적으로 제공됩니다[^.!?\n]*', '', text)
    text = re.sub(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]+', '', text)
    text = re.sub(r'\[\s*\]', '', text)     # [ ] 또는 [] 제거
    text = re.sub(r'\[[^\]]{0,3}\]', '', text)  # 너무 짧은 괄호 찌꺼기 제거
    text = re.sub(r'#시바\s*이\s*누', '#시바이누', text)
    text = re.sub(r'시바\s*이\s*누', '시바이누', text)
    text = re.sub(r'#시바리\s*움', '#시바리움', text)
    text = re.sub(r'시바리\s*움', '시바리움', text)
    text = re.sub(r'#바이\s*낸\s*스', '#바이낸스', text)
    text = re.sub(r'바이\s*낸\s*스', '바이낸스', text)
    text = re.sub(r'#바이낸\s*스', '#바이낸스', text)
    text = re.sub(r'바이낸\s*스', '바이낸스', text)
    
    text = re.sub(r'\s+', ' ', text).strip()

    text = re.sub(r'\s+', ' ', text).strip()
    return text

def remove_cjk_hanja(text: str) -> str:
    text = re.sub(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fix_translation_terms(text: str) -> str:
    replacements = {
        '비트코인에':'#비트코인 에',
        '시바견': '#시바이누',
        '시바이누 은': '#시바이누 는',
        '시바이누 는': '#시바이누 는',
        '시바이누 가': '#시바이누 가',
        '시바 이 누':'#시바이누',
        '톰 리': '#톰리',
        '제롬 파월': '#제롬파월',
        '연방 준비 제도': '#연방준비제도',
        '네비다주는': '#네비다주 는',
        '네비다주가': '#네비다주 가',
        'Google':'#구글',
        'DeFi가': '#DeFi 가',
        'DeFi는': '#DeFi 는',
        'NFT가': '#NFT 가',
        'NFT는': '#NFT 는',
        'Web3가': '#Web3 가',
        'Web3는': '#Web3 는',
        '디파이가': '#DeFi 가',
        '이란은': '#이란 은',
        '이란이': '#이란 이',
        '이란':'#이란',
		'이 란':'#이란',
		'이란에':'#이란 에',
        '호주에':'#호주 에',
        '호주는':'#호주 는',
        '호주가':'#호주 가',
        '호주의':'#호주 의',
        '부탄은':'#부탄 은',
        '부탄이':'#부탄 이',
        '현 물':'현물',
        '구 글':'#구글',
        '미국은': '#미국 은',
        '미국이': '#미국 이',
		'미국에':'#미국 에',
        '미 국':'#미국',
		'영국은':'#영국 은',
		'영국이':'#영국 이',
		'영국에':'#영국 에',
        '영 국':'#영국',
        '연준은': '#연준 은',
        '연준이': '#연준 이',
		'연준에':'#연준 에',
        '테더의': '#테더 의',
        '테더는': '#테더 는',
		'테더에':'#테더 에',
        '환율이': '#환율 이',
        '환율은': '#환율 은',
		'환율에':'#환율 에',
        '골드만 삭스': '골드만삭스',
        '골드만삭스는': '#골드만삭스 는',
        '스트래티지는': '#스트래티지 는',
        '스트래티지가': '#스트래티지 가',
        '도널드트럼프는': '#도널드트럼프 는',
        '도널드트럼프가': '#도널드트럼프 가',
        '도널드 트럼프': '#도널드트럼프',
        '제롬파월은': '#제롬파월 은',
        '제롬파월이': '#제롬파월 이',
        'SoftBank는': '#SoftBank 는',
        'JPMorgan은': '#JP모건 은',
        'JPMorgan이': '#JP모건 이',
		'JPMorgan에':'JP모건 에',
        '금은': '#금 은',
        '은은': '#은 은',
        '업비트에서': '#업비트 에서',
        '업비트는': '#업비트 는',
        '업비트가': '#업비트 가',
        '업비트의': '#업비트 의',
		'업비트에':'#업비트 에',
        '빗썸에서': '#빗썸 에서',
        '빗썸은': '#빗썸 은',
        '빗썸이': '#빗썸 이',
        '빗썸의': '#빗썸 의',
		'빗썹에':'#빗썸 에',
        '바이낸스는': '#바이낸스 는',
        '바이낸스가': '#바이낸스 가',
        '바이 낸 스':'#바이낸스',
        '바이낸 스':'#바이낸스',
        '바이 낸스':'#바이낸스',
		'바이낸스에':'#바이낸스 에',
        'Apple은': '#Apple 은',
        'Apple이': '#Apple 이',
        '애플은': '#Apple 은',
        '애플이': '#Apple 이',
        '갈링하우스는': '#갈링하우스 는',
        '갈링하우스가': '#갈링하우스 가',
        '데이비드슈워츠는': '#데이비드슈워츠 는',
        '데이비드슈워츠가': '#데이비드슈워츠 가',
        '모니카롱은': '#모니카롱 은',
        '모니카롱이': '#모니카롱 이',
        '비탈릭부텔린은': '#비탈릭부텔린 은',
        '비탈릭부텔린이': '#비탈릭부텔린 이',
        '사토시나카모토는': '#사토시나카모토 는',
        '사토시나카모토가': '#사토시나카모토 가',
        '일론머스크는': '#일론머스크 는',
        '일론머스크가': '#일론머스크 가',
        '저스틴썬은': '#저스틴썬 은',
        '저스틴썬이': '#저스틴썬 이',
        '제드맥케일럽은': '#제드맥케일럽 은',
        '제드맥케일럽이': '#제드맥케일럽 이',
        '찰스호스킨슨은': '#찰스호스킨슨 은',
        '찰스호스킨슨이': '#찰스호스킨슨 이',
        '크라켄에': '#크라켄 에',
        '월스트리트':'#월스트리트',
        '월스트리트가':'#월스트리트 가',
        '월스트리트는':'#월스트리트 는',
        '월스트리트에서':'#월스트리트 에서',
        '월스트 리 트':'#월스트리트',
        '월스트리 트':'#월스트리트',
        '월스트 리트':'#월스트리트',
        '월스트리트저널은':'#월스트리트 저널은',
		'히든로드':'#히든로드',
		'히든로드 가':'#히든로드 가',
		'히든로드 는':'#히든로드 는',
		'히든로드에서':'#히든로드 에서',
        '갈링하 우스': '#갈링하우스',
        '#갈링하 우스': '#갈링하우스',
        '갈링하 우 스': '#갈링하우스',

        '히든 로드': '#히든로드',
        '히든 로 드': '#히든로드',
        'CLARITY':'#클래리티',
        'CLARITY Act':'#클래리티법안',
		'클래 리 티':'#클래리티',
		'클래리 티':'#클래리티',
        '코인베이스는':'#코인베이스 는',
        '코인베이스가':'#코인베이스 가',    
        '코인베이스 에서':'#코인베이스 에서',
        '마이크로소프트':'#마이크로소프트',
        'Google':'#구글',
        '비트메인에':'#비트메인 에',
        '현물':'#현물',
        'Cynthia Lummis':'#신시아루미스',
        '신시아루미스는':'#신시아루미스 는',
        '신시아루미스가':'#신시아루미스 가',
        'BRICS':'#브릭스',
        'Wells Fago':'#웰스파고',
        'gamestop':'#게임스탑',
        'game stop':'#게임스탑',
        'ChatGPT':'#ChatGPT',
        'David Sacks':'#데이비드삭스',
        'DavidSacks':'#데이비드삭스',
		'천재 행동':'#지니어스법안',


}

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r'([가-힣])(#)', r'\1 #', text)
    text = re.sub(r'(#\w+)([가-힣])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z0-9])([가-힣])', r'\1 \2', text)
    text = re.sub(r'([가-힣])([A-Z][a-zA-Z]+)', r'\1 \2', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def filter_final_tags(tags: list[str]) -> list[str]:
    allowed_exact = {
        '#BTC','#ETH','#XRP','#XLM','#ADA','#TRX','#BNB','#BCH','#SHIB','#ETC','#FLR','#ATHENA','#ETNA','#USDC','#USDT', '#Ethereum',
        '#SoftBank','#JPMorgan','#TomLee','#JeromePowell','#Iran','#Israel','#US','#DeFi','#NFT','#Web3','#Stablecoin','#MorganStanley','#shibarium',
        '#BitMine','#Silver','#Gold','#Uniswap','#Ripple','#XRPL','#ETF','#AI','#SEC','#VR','#TimeTraveler','#JohnSquire','#Nvidia','#Ohio','#Coinbase','#DeFi','#NFT', '#Web3','#CFTC','#IPO','#Korea','#Cardano','#GoldmanSachs','#Strategy','#DonaldTrump','#Trump','#Robinhood', '#Japan', '#Tether','#Evernorth', '#Upbit', '#Bithumb','#BradGarlinghouse', '#DavidSchwartz', '#MonicaLong',
'#VitalikButerin', '#SatoshiNakamoto', '#ElonMusk',
'#JustinSun', '#JedMcCaleb', '#CharlesHoskinson','#US','#Ledger','#Circle','#Fed', '#Treasury', '#BlackRock', '#Binance', '#Mining', '#Blockchain',
'#Crypto', '#Altcoin', '#Liquidity', '#FSS', '#OpenAI', '#JPMorgan', '#FX', '#RWA', '#Gamestop', '#Citigroup','#Mastercard','#NYSE','#LatinAmerica','#WellsFargo','#CLARITY','#Russia','#BRICS','#WellsFago','#Microsoft'
    }

    blocked_contains = [
        'Highlights','Surprise','Underpriced','Needs','Run','Hitting','Fall',
        'Mean','Errors','Peak','Insufficient','Deals','Game','Escrow','Top',
        'Early','About','What','Will','Passes','Says','This','Hard',
        'Level','Trigger','Million','Long','Squeeze','Could'
    ]
    cleaned = []
    for tag in tags:
        tag = tag.replace('.', '')

        if any(b.lower() in tag.lower() for b in blocked_contains):
            continue

        if tag in allowed_exact:
            cleaned.append(tag)
            continue

    return list(dict.fromkeys(cleaned))

def normalize_for_duplicate(text: str) -> str:
    text = text.lower()

    noise_words = [
        'says', 'said', 'claims', 'claim', 'predicts', 'predict', 'analyst', 'analysts',
        'expert', 'experts', 'report', 'reports', 'reported',
        'according to', 'could', 'may', 'might', 'will',
        'price prediction', 'forecast', 'outlook',
        'surges', 'jumps', 'rises', 'falls', 'drops',
        'here is', 'here’s', 'what this means', 'what it means'
    ]

    for w in noise_words:
        text = text.replace(w, ' ')

    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'[^a-z0-9가-힣\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def build_story_signature(story: dict) -> str:
    raw = f"{story.get('title', '')} {story.get('desc', '')}"
    text = normalize_for_duplicate(raw)

    important_terms = []

    term_pool = [
        'btc', 'eth', 'xrp', 'xlm', 'ada', 'trx', 'bnb', 'bch', 'shib', 'etc', 'flr', 'athena', 'etna', 'usdc', 'usdt',
        'ethereum', 'cardano', 'stablecoin', 'tether',

        'softbank', 'jpmorgan', 'morgan stanley', 'goldman sachs', 'coinbase',
        'robinhood', 'upbit', 'bithumb', 'bitmine', 'uniswap', 'ripple', 'xrpl', 'xrp ledger',

        'nvidia', 'ohio', 'korea', 'japan', 'iran', 'israel',

        'defi', 'nft', 'web3', 'etf', 'sec', 'cftc', 'ipo', 'vr',
        'fed', 'federal reserve', 'gold', 'silver',

        'tom lee', 'jerome powell', 'time traveler', 'john squire',
        'brad garlinghouse', 'david schwartz', 'monica long', 'vitalik buterin',
        'satoshi nakamoto', 'elon musk', 'justin sun', 'jed mccaleb', 'charles hoskinson','openai', 'anthropic', 'google', 'xai', 'grok','x','github', 'phishing', 'wallet', 'openclaw', 'developer', 'developers', 'scam',

        'donald trump', 'trump', 'strategy', 'evernorth','brazil', 'finance minister', 'crypto tax', 'election',
    ]

    for term in term_pool:
        if term in text:
            important_terms.append(term)

    if len(important_terms) >= 2:
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        important_terms.extend(numbers[:2])

    return ' '.join(sorted(set(important_terms)))


def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = normalize_for_duplicate(story.get('title', ''))
    signature = build_story_signature(story)

    for old_title in seen_titles:
        ratio = SequenceMatcher(None, title, old_title).ratio()
        if ratio >= 0.82:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    sig_words = signature.split()
    if len(sig_words) < 3:
        return False

    for old_sig in seen_signatures:
        old_words = old_sig.split()
        if len(old_words) < 3:
            continue

        ratio = SequenceMatcher(None, signature, old_sig).ratio()
        if ratio >= 0.95:
            log(f"[시그니처 유사도 중복] {signature} <> {old_sig} / {ratio:.2f}")
            return True

    return False

def finalize_summary_ending(text: str) -> str:
    text = re.sub(r'좋은\s*덩어리$', '', text)
    text = re.sub(r'([가-힣]+)음고 말함$', r'\1음', text)
    text = re.sub(r'([가-힣]+)음고 밝힘$', r'\1음', text)
    text = re.sub(r'([가-힣]+)고 말함$', r'\1', text)
    text = re.sub(r'([가-힣]+)고 밝힘$', r'\1', text)
    text = re.sub(r'매도가 있었음.*$', '매도가 있었음', text)
    text = re.sub(r'커졌음.*$', '커졌음', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
	
def build_message(story: dict) -> str:
    raw_source = f"{story.get('title', '')}. {story.get('desc', '')}"
    raw_summary = summarize_text(
        raw_source,
        title=story.get('title', ''),
        max_sentences=SUMMARY_SENTENCES
    )

    summary_ko = translate_text_to_korean(raw_summary)
    summary_ko = cleanup_text(summary_ko)
    summary_ko = fix_translation_terms(summary_ko)
    summary_ko = fix_truncated_phrases(summary_ko)
    summary_ko = normalize_style(summary_ko)
    summary_ko = cleanup_text(summary_ko)
    summary_ko = remove_cjk_hanja(summary_ko)

    entities = extract_entities(story, max_tags=8)
    summary_ko, dynamic_tags = inject_entity_hashtags(summary_ko, entities)
    dynamic_tags = filter_final_tags(dynamic_tags)

    extra_footer_tags = []
    title_text = (story.get('title', '') + ' ' + story.get('desc', '')).lower()

    footer_map = {
        'nvidia': '#Nvidia',
        'softbank': '#SoftBank',
        'ohio': '#Ohio',
        'coinbase': '#Coinbase',
        'goldman sachs': '#GoldmanSachs',
        'tom lee': '#TomLee',
        'strategy': '#Strategy',
        'donald trump': '#DonaldTrump',
        'trump': '#Trump',
        'iran': '#Iran',
        'israel': '#Israel',
        'robinhood': '#Robinhood',
        'japan': '#Japan',
        'tether': '#Tether',
        'defi': '#DeFi',
        'nft': '#NFT',
        'web3': '#Web3',
        'silver': '#Silver',
        'gold': '#Gold',
        'bitmine': '#BitMine',
        'uniswap': '#Uniswap',
        'ripple': '#Ripple',
        'xrpl': '#XRPL',
        'sec': '#SEC',
        'binance': '#Binance',
        'apple': '#Apple',
        'vr': '#VR',
        'time traveler': '#TimeTraveler',
        'upbit': '#Upbit',
        'bithumb': '#Bithumb',
        'brad garlinghouse': '#BradGarlinghouse',
        'david schwartz': '#DavidSchwartz',
        'monica long': '#MonicaLong',
        'vitalik buterin': '#VitalikButerin',
        'satoshi nakamoto': '#SatoshiNakamoto',
        'elon musk': '#ElonMusk',
        'justin sun': '#JustinSun',
        'jed mccaleb': '#JedMcCaleb',
        'charles hoskinson': '#CharlesHoskinson',
        'ledger': '#Ledger',
        'blackrock': '#Blackrock',
        'fed': '#Fed',
        'federal reserve': '#Fed',
        'treasury': '#Treasury',
        'rwa': '#RWA',
        'mining': '#Mining',
        'california': '#California',
        'morgan stanley': '#MorganStanley',
        'kraken': '#Kraken',
        'india':'#India',
        '미얀마':'#Myanmar',
        '미국':'#US',
        '디르함으로':'#디르함 으로',
        
    }

    for key, tag in footer_map.items():
        if contains_exact_term(title_text, key) and tag not in dynamic_tags:
            extra_footer_tags.append(tag)

    dynamic_tags.extend(extra_footer_tags)

    summary_ko = finalize_summary_ending(summary_ko)

    lines = [summary_ko] if summary_ko else [story.get('title', '')]
    summary = re.sub(r'\s+', ' ', '\n'.join(lines)).strip()
    summary = summary.replace('자동뉴스', '').strip()
    summary = summary.replace('다음 기사는', '').strip()
    summary = summary.replace('뉴스레터', '').strip()

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
        f'<a href="{html.escape(story.get("url", ""))}">출처</a>',
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
        log("No image_url -> text message로 전송")
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

    filtered = [s for s in collected if matches_keywords(s, PORTFOLIO_COINS, ECON_KEYWORDS, KOREAN_KEYWORDS)]
    log(f"전체 수집 {len(collected)}개 / 필터 통과 {len(filtered)}개")

    new_stories = []
    seen_titles = []
    seen_signatures = []
    seen_urls = set()

    for s in filtered:
        title = s.get('title', '')
        norm_title = normalize_for_duplicate(title)
        signature = build_story_signature(s)
        url = s.get('url', '').strip()

        if url and url in seen_urls:
            log(f"[URL중복 제외] {title}")
            continue

        if is_duplicate(title, posted):
            log(f"[제목중복 제외] {title}")
            continue

        if is_semantically_duplicate(s, seen_signatures, seen_titles):
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
        if url:
            seen_urls.add(url)

    log(f"중복 제거 후 {len(new_stories)}개")
    state['posted'] = posted
    save_state(STATE_FILE, state)

    if INITIAL_RUN:
        log("INITIAL_RUN=true 상태라 텔레그램 발송 없이 종료")
        return

    for story in new_stories:
        msg = build_message(story)
        ok = send_telegram_photo(
            TELEGRAM_BOT_TOKEN,
            TELEGRAM_CHANNEL_ID,
            story.get('image_url', ''),
            msg
        )

        if ok:
            update_posted(story['title'], posted)
            state['posted'] = posted
            save_state(STATE_FILE, state)
            log(f"Posted: {story['title']}")
        else:
            log(f"Failed: {story['title']}")

        time.sleep(0.3)


if __name__ == '__main__':
    main()
