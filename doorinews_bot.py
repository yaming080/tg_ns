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
]

PORTFOLIO_COINS = ['BTC','ETH','XRP','XLM','ADA','TRX','BNB','BCH','SHIB','ETC','FLR','ATHENA','ETNA','USDC','USDT']

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
    '비트코인','이더리움','리플','스텔라','에이다','트론','바이낸스코인','비트코인캐시','시바이누','스테이블코인','토큰화','수탁','시드문구',
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
    '시장에 따르면',
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
    'timestabloid에 처음 게재'
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
    'Swift': 'SWIFT',

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
    'BAZAN': '바잔'
}

ENTITY_TAGS = {
    'Gold': {'en': 'Gold', 'ko': '금', 'aliases': ['gold', 'bullion', '금'], 'inject': True},
    'Silver': {'en': 'Silver', 'ko': '은', 'aliases': ['silver', '은'], 'inject': True},
    'Iran': {'en': 'Iran', 'ko': '이란', 'aliases': ['iran', '이란'], 'inject': True},
    'Israel': {'en': 'Israel', 'ko': '이스라엘', 'aliases': ['israel', '이스라엘'], 'inject': True},
    'Turkey': {'en': 'Turkey', 'ko': '터키', 'aliases': ['turkey', 'türkiye', 'turkiye', '튀르키예', '터키'], 'inject': True},
    'US': {'en': 'US', 'ko': '미국', 'aliases': ['united states', 'u.s.', 'usa', 'us ', ' us', 'america', 'american', '미국'], 'inject': True},
    'Japan': {'en': 'Japan', 'ko': '일본', 'aliases': ['japan', '일본'], 'inject': True},
    'Korea': {'en': 'Korea', 'ko': '한국', 'aliases': ['korea', 'south korea', '한국'], 'inject': True},
    'China': {'en': 'China', 'ko': '중국', 'aliases': ['china', '중국'], 'inject': True},
    'Brazil': {'en': 'Brazil', 'ko': '브라질', 'aliases': ['brazil', '브라질'], 'inject': True},
    'Canada': {'en': 'Canada', 'ko': '캐나다', 'aliases': ['canada', '캐나다'], 'inject': True},
    'Mexico': {'en': 'Mexico', 'ko': '멕시코', 'aliases': ['mexico', '멕시코'], 'inject': True},
    'UK': {'en': 'UK', 'ko': '영국', 'aliases': ['uk', 'britain', 'british', 'united kingdom', '영국'], 'inject': True},
    'Qatar': {'en': 'Qatar', 'ko': '카타르', 'aliases': ['qatar', '카타르'], 'inject': True},

    'ElonMusk': {'en': 'ElonMusk', 'ko': '일론머스크', 'aliases': ['elon musk', '일론 머스크', '일론머스크', 'musk'], 'inject': True},
    'SpaceX': {'en': 'SpaceX', 'ko': '스페이스X', 'aliases': ['spacex', 'space x', '스페이스x', '스페이스 엑스', '스페이스엑스'], 'inject': True},
    'Tether': {'en': 'Tether', 'ko': '테더', 'aliases': ['tether', '테더', 'usdt'], 'inject': True},
    'Circle': {'en': 'Circle', 'ko': '서클', 'aliases': ['circle', '서클', 'usdc issuer'], 'inject': True},
    'Bithumb': {'en': 'Bithumb', 'ko': '빗썸', 'aliases': ['bithumb', '빗썸'], 'inject': True},
    'Upbit': {'en': 'Upbit', 'ko': '업비트', 'aliases': ['upbit', '업비트'], 'inject': True},
    'Robinhood': {'en': 'Robinhood', 'ko': '로빈후드', 'aliases': ['robinhood', '로빈후드'], 'inject': True},
    'GoldmanSachs': {'en': 'GoldmanSachs', 'ko': '골드만삭스', 'aliases': ['goldman sachs', '골드만삭스'], 'inject': True},
    'JPMorgan': {'en': 'JPMorgan', 'ko': 'JPMorgan', 'aliases': ['j.p. morgan', 'jp morgan', 'jpmorgan'], 'inject': True},
    'Fed': {'en': 'Fed', 'ko': '연준', 'aliases': ['federal reserve', 'fed', '연준'], 'inject': True},
    'Treasury': {'en': 'Treasury', 'ko': '재무부', 'aliases': ['treasury', '재무부'], 'inject': True},
    'SEC': {'en': 'SEC', 'ko': 'SEC', 'aliases': ['sec'], 'inject': True},
    'CFTC': {'en': 'CFTC', 'ko': 'CFTC', 'aliases': ['cftc'], 'inject': True},
    'ETF': {'en': 'ETF', 'ko': 'ETF', 'aliases': ['etf'], 'inject': True},
    'DeFi': {'en': 'DeFi', 'ko': 'DeFi', 'aliases': ['defi', '디파이'], 'inject': True},
    'Liquidity': {'en': 'Liquidity', 'ko': '유동성', 'aliases': ['liquidity', '유동성'], 'inject': True},
    'Stablecoin': {'en': 'Stablecoin', 'ko': '스테이블코인', 'aliases': ['stablecoin', 'stable coin', '스테이블코인'], 'inject': True},
    'AI': {'en': 'AI', 'ko': 'AI', 'aliases': ['artificial intelligence', 'ai'], 'inject': False},
    'Anthropic': {'en': 'Anthropic', 'ko': 'Anthropic', 'aliases': ['anthropic'], 'inject': True},

    'BTC': {'en': 'BTC', 'ko': '비트코인', 'aliases': ['btc', 'bitcoin', '비트코인'], 'inject': False},
    'ETH': {'en': 'ETH', 'ko': '이더리움', 'aliases': ['eth', 'ethereum', '이더리움'], 'inject': False},
    'XRP': {'en': 'XRP', 'ko': '리플', 'aliases': ['xrp', 'ripple', '리플'], 'inject': False},
    'XLM': {'en': 'XLM', 'ko': '스텔라', 'aliases': ['xlm', 'stellar', '스텔라'], 'inject': False},
    'ADA': {'en': 'ADA', 'ko': '에이다', 'aliases': ['ada', 'cardano', '에이다', '카르다노'], 'inject': False},
    'TRX': {'en': 'TRX', 'ko': '트론', 'aliases': ['trx', 'tron', '트론'], 'inject': False},
    'BNB': {'en': 'BNB', 'ko': '바이낸스코인', 'aliases': ['bnb'], 'inject': False},
    'BCH': {'en': 'BCH', 'ko': '비트코인캐시', 'aliases': ['bch', 'bitcoin cash'], 'inject': False},
    'SHIB': {'en': 'SHIB', 'ko': '시바이누', 'aliases': ['shib', 'shiba inu', '시바이누', '시바 이누', '시바견'], 'inject': True},
    'ETC': {'en': 'ETC', 'ko': '이더리움클래식', 'aliases': ['etc', 'ethereum classic'], 'inject': False},
    'FLR': {'en': 'FLR', 'ko': '플레어', 'aliases': ['flr', 'flare', '플레어'], 'inject': False},
    'ATHENA': {'en': 'ATHENA', 'ko': '아테나', 'aliases': ['athena', '아테나'], 'inject': False},
    'ETNA': {'en': 'ETNA', 'ko': '에트나', 'aliases': ['etna', '에트나'], 'inject': False},
    'USDC': {'en': 'USDC', 'ko': 'USDC', 'aliases': ['usdc'], 'inject': False},
    'USDT': {'en': 'USDT', 'ko': 'USDT', 'aliases': ['usdt'], 'inject': False},
}

EVENT_ALIASES = {
    'lawsuit': ['lawsuit', 'sues', 'sued', '소송', '제소', '제기'],
    'freeze': ['freeze', 'frozen', '동결'],
    'swap': ['swap', '스왑'],
    'buy': ['buy', 'bought', 'purchase', 'purchased', 'acquire', 'acquired', '인수', '매입', '구매'],
    'funding': ['raise', 'raised', 'funding', 'secured', '확보', '조달'],
    'launch': ['launch', 'launched', '출시', '발표'],
    'approval': ['approval', 'approved', '승인'],
    'treasury': ['treasury', '재무부'],
    'centralbank': ['central bank', 'cbtr', '중앙은행'],
    'war': ['war', '전쟁'],
    'inflation': ['inflation', '인플레이션'],
    'liquidity': ['liquidity', '유동성'],
    'extend': ['extend', 'extended', '연장'],
    'sale': ['sale', 'selling', 'sold', '판매', '매각'],
}

GENERIC_BLOCKED_TAG_WORDS = {
    'highlights','surprise','underpriced','needs','run','hitting','fall','mean','errors','peak',
    'insufficient','deals','game','escrow','top','early','about','what','will','passes','says',
    'this','hard','level','trigger','million','long','squeeze','could','edge','side','corner',
    'border','big','new','latest','price','prices','market','markets'
}

def strip_inline_hashtags(text: str) -> str:
    text = re.sub(r'(?<!\w)#([A-Za-z0-9_가-힣]+)', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def alias_in_text(text: str, alias: str) -> bool:
    alias_low = alias.lower()
    if re.fullmatch(r'[a-z0-9]{2,6}', alias_low):
        return re.search(r'(?<![a-z0-9])' + re.escape(alias_low) + r'(?![a-z0-9])', text) is not None
    return alias_low in text

def alias_position(text: str, alias: str) -> int:
    alias_low = alias.lower()
    if re.fullmatch(r'[a-z0-9]{2,6}', alias_low):
        m = re.search(r'(?<![a-z0-9])' + re.escape(alias_low) + r'(?![a-z0-9])', text)
        return m.start() if m else 10**9
    pos = text.find(alias_low)
    return pos if pos >= 0 else 10**9

def extract_event_keys(text: str) -> list[str]:
    low = normalize_for_duplicate(text)
    found = []
    for key, aliases in EVENT_ALIASES.items():
        if any(alias_in_text(low, a) for a in aliases):
            found.append(key)
    return found[:6]

def extract_numbers_for_signature(text: str) -> list[str]:
    low = text.lower()
    nums = re.findall(r'\b\d+(?:\.\d+)?\s*(?:million|billion|trillion|만|억|조|%|달러|usd)?', low)
    out = []
    for n in nums:
        n = re.sub(r'\s+', '', n)
        if n and n not in out:
            out.append(n)
    return out[:4]


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
    'DEFI','NFT','WEB3','ETP','ETF','DAO','IPO','CTO','LNG','AI'}
STATE_FILE = 'news_state.json'
MAX_ITEMS_PER_FEED = 5
SUMMARY_SENTENCES = 2

def log(msg: str) -> None:
    print(msg, flush=True)

def http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; DooriNewsBot/2.1)'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')

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
    text = re.sub(r'([가-힣])([A-Z][a-zA-Z]+)', r'\1 \2', text)
    text = re.sub(r'([가-힣])(#)', r'\1 #', text)
    text = re.sub(r'(#\w+)([가-힣])', r'\1 \2', text)
    return text

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

def summarize_text(text: str, title: str = "", max_sentences: int = SUMMARY_SENTENCES) -> str:
    text = cleanup_text(text)

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

    return ' '.join(picked) if picked else cleanup_text(title)

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
		(r'습니다\.?', ''),
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
    text = f"{story.get('title', '')} {story.get('desc', '')}"
    low = normalize_for_duplicate(text)
    matches = []
    for key, meta in ENTITY_TAGS.items():
        positions = [alias_position(low, alias) for alias in meta['aliases'] if alias_in_text(low, alias)]
        if positions:
            matches.append((min(positions), key))

    matches.sort(key=lambda x: x[0])
    result = []
    seen = set()
    for _, key in matches:
        if key not in seen:
            seen.add(key)
            result.append(key)
        if len(result) >= max_tags:
            break
    return result

def entity_korean_name(entity: str) -> str:
    meta = ENTITY_TAGS.get(entity)
    if meta:
        return meta['ko']
    if entity in MANUAL_TRANSLATIONS:
        return MANUAL_TRANSLATIONS[entity]
    translated = translate_text_to_korean(entity).replace(' ', '')
    return translated or entity.replace(' ', '')

def inject_entity_hashtags(summary: str, entities: list[str]) -> tuple[str, list[str]]:
    text = strip_inline_hashtags(summary)
    final_tags: list[str] = []
    particles = ['가','이','은','는','를','을','의','와','과','로','도','만','에서','에게','까지']

    for ent in entities:
        meta = ENTITY_TAGS.get(ent, {'en': ent.replace(' ', ''), 'ko': entity_korean_name(ent), 'inject': True})
        en_tag = '#' + meta['en'].replace(' ', '')
        ko_tag = '#' + meta['ko'].replace(' ', '')
        for tag in [en_tag, ko_tag]:
            if tag not in final_tags:
                final_tags.append(tag)

        if not meta.get('inject', True):
            continue

        bases = [meta['ko'], ent.replace('_', ' '), meta['en']]
        replaced = False
        for base in bases:
            if not base:
                continue
            for p in particles:
                pattern = re.escape(base + p)
                new_text, count = re.subn(pattern, f'{ko_tag} {p}', text, count=1)
                if count:
                    text = new_text
                    replaced = True
                    break
            if replaced:
                break
        if not replaced:
            for base in bases:
                new_text, count = re.subn(re.escape(base), ko_tag, text, count=1)
                if count:
                    text = new_text
                    break

    text = re.sub(r'(?<!\w)#(가장자리(?:에|의|로)?)', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text, final_tags


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
    text = strip_inline_hashtags(text)

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

    text = text.replace('포스트가 ', '')
    text = text.replace('게시물이 ', '')
    text = text.replace('게재물이 ', '')
    text = text.replace('라는 포스트가 ', '')
    text = text.replace('라는 게시물이 ', '')

    text = re.sub(r'^[^.!?\n]{0,40}에 따르면[, ]*', '', text)
    text = re.sub(r'본 콘텐츠는 특정 종목이나 자산에 대한 투자 조언이 아니며[^.!?\n]*', '', text)
    text = re.sub(r'변동성 높은 시장에서 흔들리지 않는 투자 마인드를 가꾸기 위한 심리적 환기 목적으로 제공됩니다[^.!?\n]*', '', text)

    text = re.sub(r'\[\s*\]|\[\.\.\.\]|\[…\]', ' ', text)
    text = re.sub(r'\s*:\s*\[\s*\]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fix_translation_terms(text: str) -> str:
    text = strip_inline_hashtags(text)
    replacements = {
        '시바견': '시바이누',
        '시바 이 누': '시바이누',
        '시바 이누': '시바이누',
        '시바이누 은': '#시바이누 는',
        '시바이누 는': '#시바이누 는',
        '시바이누 가': '#시바이누 가',
        '톰 리': '#톰리',
        '제롬 파월': '#제롬파월',
        '연방 준비 제도': '#연방준비제도',
        '네비다주는': '#네비다주 는',
        '네비다주가': '#네비다주 가',
        'DeFi가': '#DeFi 가',
        'DeFi는': '#DeFi 는',
        'NFT가': '#NFT 가',
        'NFT는': '#NFT 는',
        'Web3가': '#Web3 가',
        'Web3는': '#Web3 는',
        '디파이가': '#DeFi 가',
        '이란은': '#이란 은',
        '이란이': '#이란 이',
        '미국은': '#미국 은',
        '미국이': '#미국 이',
        '터키는': '#터키 는',
        '터키가': '#터키 가',
        '연준은': '#연준 은',
        '연준이': '#연준 이',
        '테더의': '#테더 의',
        '테더는': '#테더 는',
        '서클은': '#서클 은',
        '서클이': '#서클 이',
        '빗썸은': '#빗썸 은',
        '빗썸이': '#빗썸 이',
        '빗썸의': '#빗썸 의',
        '금은': '#금 은',
        '금이': '#금 이',
        '업비트에서': '#업비트 에서',
        '업비트는': '#업비트 는',
        '업비트가': '#업비트 가',
        '업비트의': '#업비트 의',
        '골드만 삭스': '골드만삭스',
        '일론 머스크': '#일론머스크',
        '스페이스 엑스': '#스페이스X',
        '스페이스엑스': '#스페이스X',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r'(?<!\w)#가장자리(?:에|의|로)?', lambda m: m.group(0).replace('#', ''), text)
    text = re.sub(r'([가-힣])(#)', r'\1 \2', text)
    text = re.sub(r'(#\w+)([가-힣])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z0-9])([가-힣])', r'\1 \2', text)
    text = re.sub(r'([가-힣])([A-Z][a-zA-Z]+)', r'\1 \2', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def filter_final_tags(tags: list[str]) -> list[str]:
    cleaned = []
    allowed_from_catalog = {'#' + meta['en'] for meta in ENTITY_TAGS.values()} | {'#' + meta['ko'] for meta in ENTITY_TAGS.values()}
    allowed_from_catalog |= {f'#{t}' for t in FINAL_HASHTAGS}

    for tag in tags:
        if not tag:
            continue
        tag = tag.replace('.', '').strip()
        if not tag.startswith('#'):
            continue
        body = tag[1:]
        if len(body) < 2:
            continue
        if any(b.lower() == body.lower() for b in GENERIC_BLOCKED_TAG_WORDS):
            continue
        if re.fullmatch(r'[A-Za-z0-9가-힣]+', body):
            cleaned.append('#' + body)

    ordered = []
    seen = set()
    for tag in cleaned:
        if tag in allowed_from_catalog or tag.upper() in {f'#{c}' for c in PORTFOLIO_COINS}:
            if tag not in seen:
                seen.add(tag)
                ordered.append(tag)
    return ordered


def normalize_for_duplicate(text: str) -> str:
    text = text.lower()
    noise_words = [
        'says', 'said', 'claims', 'claim', 'predicts', 'predict', 'analyst', 'analysts',
        'expert', 'experts', 'report', 'reports', 'reported', 'according to', 'could',
        'may', 'might', 'will', 'price prediction', 'forecast', 'outlook', 'surges',
        'jumps', 'rises', 'falls', 'drops', 'here is', 'here’s', 'what this means',
        'what it means'
    ]
    for w in noise_words:
        text = text.replace(w, ' ')
    text = strip_inline_hashtags(text)
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'\[\s*\]|\[\.\.\.\]|\[…\]', ' ', text)
    text = re.sub(r'[^a-z0-9가-힣\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def build_story_signature(story: dict) -> str:
    raw = f"{story.get('title', '')} {story.get('desc', '')}"
    entities = extract_entities(story, max_tags=10)
    numbers = extract_numbers_for_signature(raw)
    events = extract_event_keys(raw)
    signature_parts = [
        'ENT:' + '|'.join(sorted(entities[:6])),
        'NUM:' + '|'.join(numbers[:3]),
        'EV:' + '|'.join(sorted(events[:3])),
    ]
    return ' || '.join(signature_parts)


def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = normalize_for_duplicate(story.get('title', ''))
    signature = build_story_signature(story)

    for old_title in seen_titles:
        ratio = SequenceMatcher(None, title, old_title).ratio()
        if ratio >= 0.84:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    def unpack(sig: str) -> tuple[set[str], set[str], set[str]]:
        entities, numbers, events = set(), set(), set()
        for part in sig.split(' || '):
            if part.startswith('ENT:'):
                entities = {x for x in part[4:].split('|') if x}
            elif part.startswith('NUM:'):
                numbers = {x for x in part[4:].split('|') if x}
            elif part.startswith('EV:'):
                events = {x for x in part[3:].split('|') if x}
        return entities, numbers, events

    cur_entities, cur_numbers, cur_events = unpack(signature)
    if len(cur_entities) < 1:
        return False

    for old_sig in seen_signatures:
        old_entities, old_numbers, old_events = unpack(old_sig)
        entity_overlap = len(cur_entities & old_entities)
        number_overlap = len(cur_numbers & old_numbers)
        event_overlap = len(cur_events & old_events)

        ratio = SequenceMatcher(None, signature, old_sig).ratio()
        if ratio >= 0.93:
            log(f"[시그니처 유사도 중복] {signature} <> {old_sig} / {ratio:.2f}")
            return True
        if entity_overlap >= 2 and (number_overlap >= 1 or event_overlap >= 1):
            log(f"[엔티티중심 중복] {signature} <> {old_sig} / ent={entity_overlap} num={number_overlap} ev={event_overlap}")
            return True

    return False


def build_message(story: dict) -> str:
    raw_summary = summarize_text(
        story.get('desc', ''),
        title=story.get('title', ''),
        max_sentences=SUMMARY_SENTENCES
    )

    summary_ko = translate_text_to_korean(raw_summary)
    summary_ko = cleanup_text(summary_ko)
    summary_ko = fix_translation_terms(summary_ko)
    summary_ko = fix_truncated_phrases(summary_ko)
    summary_ko = normalize_style(summary_ko)
    summary_ko = cleanup_text(summary_ko)
    summary_ko = re.sub(r'접수되었\s*$', '접수되었음', summary_ko)
    summary_ko = re.sub(r'([가-힣]+)되었\s*$', r'\1되었음', summary_ko)
    summary_ko = re.sub(r'\[\s*\]|\[\.\.\.\]|\[…\]', '', summary_ko).strip()

    entities = extract_entities(story, max_tags=10)
    summary_ko, dynamic_tags = inject_entity_hashtags(summary_ko, entities)

    title_text = normalize_for_duplicate(story.get('title', '') + ' ' + story.get('desc', ''))
    for key, meta in ENTITY_TAGS.items():
        if any(alias_in_text(title_text, alias) for alias in meta['aliases']):
            dynamic_tags.extend(['#' + meta['en'], '#' + meta['ko']])

    dynamic_tags = filter_final_tags(dynamic_tags)

    lines = []
    for line in re.split(r'(?<=[.!?])\s+|\n+', summary_ko):
        line = line.strip()
        if line and not is_bad_line(line):
            lines.append(line)

    if not lines:
        lines = [normalize_style(translate_text_to_korean(cleanup_text(story.get('title', ''))))]

    summary = re.sub(r'\s+', ' ', '\n'.join(lines)).strip()
    summary = summary.replace('자동뉴스', '').replace('다음 기사는', '').replace('뉴스레터', '').strip()
    summary = strip_inline_hashtags(summary)
    summary, inline_tags = inject_entity_hashtags(summary, entities[:4])

    footer_tags = filter_final_tags(dynamic_tags + inline_tags + [f'#{t}' for t in FINAL_HASHTAGS])

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
