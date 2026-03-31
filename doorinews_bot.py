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

from google import genai


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
INITIAL_RUN = os.environ.get("INITIAL_RUN", "false").strip().lower() == "true"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

FEEDS = [
    ('CryptoBriefing', 'https://cryptobriefing.com/feed/'),
    ('Cointelegraph', 'https://cointelegraph.com/rss'),
    ('TheBlock', 'https://www.theblock.co/rss.xml'),
    ('크립토폴리탄', 'https://www.cryptopolitan.com/feed/'),
    ('더크립토베이식', 'https://thecryptobasic.com/feed/'),
    ('코인게이프', 'https://coingape.com/feed/'),
    ('타입스베틀로이드', 'https://timestabloid.com/feed/'),
    ('블루밍비트', 'https://bloomingbit.io/rss.xml'),
    ('토큰포스트', 'https://www.tokenpost.kr/rss'),
	('코인데스크', 'https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml'),
	('크립토타임즈', 'https://www.cryptotimes.io/feed/'),
	('비트코이니스트', 'https://bitcoinist.com/feed/'),
	('코인에디션', 'https://coinedition.com/feed/'),
	('크립토포테이토', 'https://cryptopotato.com/feed/'),
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
KOREAN_TAG_KEYWORDS = [
    '비트코인', '이더리움', '리플', '스텔라', '에이다', '트론',
'시바이누', '스테이블코인',
'미국', '이란', '이스라엘', '일본', '한국', '중국', '브라질',
'연준', '환율', '유동성', '재무부',
'ETF', 'SEC', 'CFTC', 'OCC',
'업비트', '빗썸', '바이낸스', '코인베이스',
'모건스탠리', '골드만삭스', '크라켄', '로빈후드',
'일론머스크', '갈링하우스', '제롬파월', '트럼프',
'아이언라이트', '보어히스', '에릭보어히스', '마이클세일러', '세일러', '로버트기요사키', '폴앳킨스',
'데이비드슈워츠', '마이크노보그라츠', '샘알트만', '셰이프시프트', '브래드갈링하우스', '모니카롱',
'비탈릭부텔린', '사토시나카모토', '저스틴썬', '제드맥케일럽', '찰스호스킨슨',
'스트래티지', '도널드트럼프', '테더', '플레어', 'FLR', '에테나', '에테나', '메타플래닛', '도리뉴스',
'시바리움', 'SWIFT', '백악관', '카타르', '마스터카드',
'IPO', 'CTO', 'XRP', 'XLM', 'BTC', 'ETH', 'SHIB', 'USDC', 'USDT', 'XAUT', 'SOL', 'DOGE',
'토큰화', '수탁', '시드문구', '소송', '규제', '해석',
'DeFi', 'NFT', 'Web3', 'BitMine', '톰리', 'Thomasgeth', 'TimeTraveler', 'JohnSquire',
'유니스왑', 'HaydenAdams', '파월', 'America', '네비다주', 'JPMorgan', '라이드', '바이비트', 'Ledger',
'서클', '머니그램', 'Apple', '페이팔', '스트라이프', '제미니', '칼시', '제드시온', '에버노스',
'XRPLedger', '세계금협회', '디지털금', '비트코인퀀텀', 'BIP360', 'OpenAI', 'Anthropic',
'슈퍼마이크로', 'AI', 'LNG', '바잔', '캘리포니아', '지니어스법안', '지니어스', '법안', 'ICE',
'클래리티', '블랙록', '문페이', '히든로드', '게임스탑', '구글', '인도', '웰스파고', '피터쉬프', '패니매','ICE', 'EEZ', '현물', '서울', '부산',
	'휘발유', '경유', '대전', '인천', '대구','경기도', '울산', '강원도', '석유', '비트코인캐시','월스트리트',
	'매수', '기관자금', '디파이', '오픈크레딧', '스마트계약', '프라이빗크레딧','비트코인캐시', '노동부', '401k',
	'밈코인','레이어2','금융', '암호화폐', '트론', 'TRX', 'TRON', '호주', '미국',
'프랭클린템플턴', '토니피코어','위즈덤트리', '클래리티법',
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
    'times tabloid에 처음 게재', 'Times Tabloid 에 처음으로 게재되었음',
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
    'cryptonews first appeared','CryptoBriefing','Crypto Briefing','Cointelegraph','CryptoSlate','TheBlock','WatcherGuru',
	'Cryptopolitan','처음으로 게재되었음','데드크로스','Death Cross',
    'TheCryptoBasic','CoinGape','TimesTabloid','DailyHodl','BeInCrypto','BloomingBit','NewsBitcoin','CoinTurk', '.com News',
	'코인 소식 중 중요한 내용만 PiCK 해서 보세요', '뉴스 속보를 제공해요','게시물임','청산','하락','급락','Crypto Briefing 에서',
	'황정수의 글로벌 체크인','defillama.com','하락함','청산됨','매도 압력', '이 작성함', '이재명','bristol myers squibb', 'bmy', 'biopharma', 'pharma', 'pharmaceutical',
'drug', 'therapy', 'treatment', 'clinical', 'trial', 'patient',
'medicine', 'healthcare', 'biotech', 'phase 1', 'phase 2', 'phase 3','제약', '바이오', '임상', '치료제', '약물', '환자',
	'의약품', '헬스케어','price drop', 'market drop', 'drops below', 'decline', 'declined','fell', 'fall below', 'slump',
	'sell-off', 'bearish','극단적인 공포','extreme fear','Conjecture', 'could impact bitcoin', 'could impact bitcoin',
'could affect bitcoin',
'how weakening us labor data',
'what this means',
'what it means',
'might impact bitcoin',
'may impact bitcoin',
'could affect bitcoin',
'how weakening us labor data',
'what this means',
'what it means',
'might impact bitcoin',
'may impact bitcoin',
	'first appeared on times tabloid',
    'appeared first on times tabloid',
    'first published on times tabloid',
    'published first on times tabloid',
    'first appeared on timestabloid',
    'appeared first on timestabloid',
    'first published on timestabloid',
    'published first on timestabloid',
    'morning crypto report',
'weak price action',
'rising leverage',
'unstable setup',
'가격조정', '가격 조정',
'레버리지','온톨로지','TxFlow','제트캐시', 'zcash','practical guide', 'practical guide to', 'guide to choosing', 'market maker guide',
'실용 가이드', '실용가이드',

'lido dao', 'ldo', 'redemption', 'proposed sale', 'token sale',
'환매', '매각 제안', '매각',

'surge', 'spike', 'jumps', 'rally', 'best quarter', 'worst quarter', 'buying opportunity',
'급등', '상승폭', '최악', '분기', '매수 기회',

'metals.io', 'metals io', 'trillitech', 'trili tech',
'crypto tax', 'customers don’t understand crypto tax', 'customers do not understand crypto tax',
'암호화폐 세금', '고객의 절반 이상이 암호화폐 세금을 이해하지 못함',

'raised', 'raise', 'raising', 'funding', 'series a', 'fundraise', 'fundraising',
'모금', '모금함', '자금조달', '시리즈', 'critical thinking', '비판적 사고',
'blasts xrp community', '폭파함',
'breaks macro model', '다시 깨뜨립니다',
'payment cost', '지불 비용', '지불비용',
'bounce zone', '반등 구간', '반등구간',
'selling pressure', 'sell pressure', '매도세',
'kucoin',
'hashrate', '해시레이트',
'bleeding', '출혈',
'불안을 촉발함',
'fundraise', 'fundraising', '모금', '모금함', '자금조달',
'리스크 오프',
'test support', '지지선 시험대',
'entry zone', '진입 구역',
'monthly chart', '월간 차트','reason', 'reasons',
'uncertain', 'uncertainty', '불확실', '불확실성','reason', 'reasons', 'why', '이유', 'oil', 'solar', 'renewable', 'dividend', 'shareholder', 'board reshuffle',
'주주총회', '배당', '태양광', '에너지 전환', '중장기 성장 전략', 'game ai', 'gaming ai', 'game content', 'series b', 'funding round',
'게임 ai', '게임 콘텐츠', '시리즈 b', '펀딩', '마케팅 자산', '자동화 툴', 'BitGo', 'listing', 'listings', 'delisting', 'delist', 'delisted',
'상장', '상장 소식', '상장 발표', '상장 폐지', '폐지 결정', '거래지원 종료',
'binance listing', 'binance delisting', '바이낸스 상장', '바이낸스 상장 폐지','analyst',
'analysis',
'correlation',
's&p correlation',
'hack',
'hacker',
'scam',
'fraud',
'social engineering',
'charged',
'prison sentence',
'canton network',
'iboxx',
'us treasuries',
	
]

BAD_SIGNAL_PATTERNS = [
    r'\bno bullish reversal\b',
    r'\bno bullish reversal signs\b',
    r'\bweak price action\b',
    r'\bbearish\b',
    r'\bprice react\b',
    r'\bbullish crossover\b',
    r'\bcrossover completes\b',
    r'\bprice analysis\b',
    r'\bdowntrend\b',
    r'강세 전환 신호 없음',
    r'반등 신호 없음',
    r'하락세',
    r'약세',
    r'가격 상승으로 이어지지 못',
    r'상승으로 이어지지 못',
    r'반등 실패',
    r'크로스오버',
]
BAD_TOPIC_PATTERNS = [
    # 가격/차트/기술적 분석
    r'\bprice analysis\b',
    r'\bprice prediction\b',
    r'\bforecast\b',
    r'\bchart\b',
    r'\btechnical analysis\b',
    r'\btrading setup\b',
    r'\bsupport\b',
    r'\bresistance\b',
    r'\bbreakout\b',
    r'\btrend line\b',
    r'\bentry zone\b',
    r'\btarget price\b',
    r'\bbullish\b',
    r'\bbearish\b',
    r'\bcrossover\b',
    r'\bdeath cross\b',
    r'\bgolden cross\b',

    # 기술/개발/업그레이드/인프라
    r'\bdeveloper\b',
    r'\bdevelopers\b',
    r'\bdevnet\b',
    r'\btestnet\b',
    r'\bmainnet\b',
    r'\bupgrade\b',
    r'\bprotocol\b',
    r'\binfrastructure\b',
    r'\bsmart contract\b',
    r'\bsmart contracts\b',
    r'\bwallet security\b',
    r'\bquantum resilience\b',
    r'\bquantum resistance\b',
    r'\bpost-quantum\b',
    r'\blayer 2\b',
    r'\blayer2\b',

    # 입출금/전송/지갑
    r'입금',
    r'출금',
    r'입출금',
    r'전송',
    r'송금',
    r'지갑',
    r'wallet',
    r'deposit',
    r'withdraw',
    r'withdrawal',
    r'transfer',
    r'bridge',

    # 한국어 가격/분석 표현
    r'가격 분석',
    r'기술적 분석',
    r'차트 분석',
    r'지지선',
    r'저항선',
    r'목표가',
    r'돌파',
    r'반등',
    r'추세',
    r'매수 구간',
    r'매도 구간',

    # 한국어 기술/개발 표현
    r'업그레이드',
    r'테스트넷',
    r'메인넷',
    r'프로토콜',
    r'개발자',
    r'기술',
    r'레이어2',

	r'\blisting\b',
    r'\blistings\b',
    r'\bdelisting\b',
    r'\bdelist\b',
    r'상장',
    r'상장 폐지',
    r'폐지 결정',
    r'거래지원 종료',
	# 시장 해설 / 분석 기사 제외
    r'\banalyst\b',
    r'\banalysis\b',
    r'\bcorrelation\b',
    r'\bsp correlation\b',
    r'\bs&p correlation\b',
    r'\bbull sign\b',
    r'\bnot the bull sign\b',
    r'강세 신호',
    r'분석이 나옴',
    r'상관관계',
    r'역상관',

    # 해킹 / 범죄 / 사기 기사 제외
    r'\bhack\b',
    r'\bhacker\b',
    r'\bhacked\b',
    r'\bscam\b',
    r'\bfraud\b',
    r'\bsocial engineering\b',
    r'\bcharged\b',
    r'\bprison sentence\b',
    r'\bstolen funds\b',
    r'해킹',
    r'사기',
    r'기소',
    r'검찰',
    r'징역',
    r'탈취',

    # 일반 금융 인프라 / 토큰화 일반 기사 제외
    r'\btokenized\b',
    r'\btokenization\b',
    r'\bdata infrastructure\b',
    r'\bcanton network\b',
    r'\bus treasuries\b',
    r'\biBoxx\b',
    r'\bs&p dow jones\b',
    r'토큰화',
    r'미국채',
    r'데이터 인프라',
    r'칸톤네트워크',
    r'금융 데이터',
]
NON_PORTFOLIO_ASSET_PATTERNS = [
    r'\bsol\b', r'\bsolana\b', r'\bdoge\b', r'\bdogecoin\b', r'\bavax\b',
    r'\bdot\b', r'\blink\b', r'\bltc\b', r'\bnear\b', r'\buni\b', r'\baave\b',
    r'\bpepe\b', r'\bwif\b', r'\bbonk\b', r'\bsui\b', r'\bapt\b', r'\batom\b',
    r'\bfil\b', r'\bhbar\b', r'\bkas\b', r'\btao\b', r'\bicp\b',
    r'솔라나', r'도지', r'아발란체', r'폴카닷', r'체인링크', r'라이트코인',
    r'니어', r'유니스왑', r'에이브', r'수이', r'앱토스', r'파일코인',
]
STOCK_PATTERNS = [
    r'\bstock\b',
    r'\bstocks\b',
    r'\bshare\b',
    r'\bshares\b',
    r'\bequity\b',
    r'\bdividend\b',
    r'\bearnings\b',
    r'\bshareholder\b',
    r'\bnasdaq\b',
    r'\bnyse\b',
    r'\bipo\b',
    r'주식',
    r'주가',
    r'배당',
    r'실적',
    r'주주',
    r'상장사',
]

def contains_non_portfolio_asset(text: str) -> bool:
    low = (text or "").lower()
    return any(re.search(p, low, re.I) for p in NON_PORTFOLIO_ASSET_PATTERNS)

def contains_stock_context(text: str) -> bool:
    low = (text or "").lower()
    return any(re.search(p, low, re.I) for p in STOCK_PATTERNS)

def contains_bad_signal(text: str) -> bool:
    low = (text or "").lower()
    return any(re.search(p, low, re.I) for p in BAD_SIGNAL_PATTERNS)

def contains_bad_topic(text: str) -> bool:
    low = (text or "").lower()
    return any(re.search(p, low, re.I) for p in BAD_TOPIC_PATTERNS)



FINAL_HASHTAGS = ['BTC','비트코인','dooridoori','도리도리','doorinati','도리나티']

INLINE_TAG_WHITELIST = {
    '미국', 'CFTC', 'Elizabeth Warren', '엘리자베스워런',
    '정부', '비트코인', 'BTC', 'ETH', 'XRP',
    '연준', 'SEC', 'ETF', '재무부', '상원', '하원',
    '아이언라이트', '보어히스', '에릭보어히스',
    '마이클세일러', '세일러', '로버트기요사키', '폴앳킨스',
    '데이비드슈워츠', '마이크노보그라츠', '샘알트만', '일론머스크',
    '셰이프시프트', '갈링하우스', '모니카롱', '비탈릭부텔린',
    '사토시나카모토', '저스틴썬', '제드맥케일럽', '찰스호스킨슨',
    '골드만삭스', '스트래티지', '도널드트럼프', '트럼프',
    '로빈후드', '테더', '리플', '플레어', '아테나', '에테나',
    '메타플래닛', '도리뉴스', '시바이누', '시바리움',
    '연준', '재무부', '백악관',
    '브라질', '중국', '일본', '한국', '미국', '이란', '이스라엘', '카타르',
    '마스터카드',
    'SEC', 'CFTC', 'OCC', 'ETF', 'IPO', 'CTO',
    'XRP', 'XLM', 'BTC', 'ETH', 'SHIB', 'USDC', 'USDT', 'XAUT', 'SOL', 'DOGE',
    '비트코인', '이더리움', '스테이블코인', '토큰화', '수탁', '시드문구', '소송', '규제', '해석',
    'DeFi', 'NFT', 'Web3', '디파이', '엑스알피',
    'BitMine', '비트마인',
    '톰리', '제롬파월', '파월',
    '네비다주', 'JPMorgan', '라이드', '바이비트', 'Ledger',
    '서클', '머니그램', '업비트', '빗썸', '바이낸스',
    '애플', '페이팔', '스트라이프', '제미니', '칼시', '제드시온',
    '에버노스', 'XRPLedger', '세계금협회',
     '디지털금', '비트코인퀀텀', 'BIP360',
    'OpenAI', 'Anthropic', '슈퍼마이크로', 'AI', 'LNG',
    '바잔', '캘리포니아', '모건스탠리', '크라켄',
    '지니어스법안', '지니어스', '법안', 'ICE', '클래리티',
    '블랙록', '문페이', '코인베이스', '히든로드', '게임스탑',
    '구글', '인도', '웰스파고', '피터쉬프', '패니매',
    'EEZ', '버핏',
    '스트라이브', '터틀', '스트라이브자산운용', 'STRC', 'SATA', '니움', '비자',
    '오픈크레딧', '스마트계약', '프라이빗크레딧', '기관자금',
	'Bitcoin', 'Ethereum', 'Ripple','United States', 'US', 'Government',
'Federal Reserve', 'Fed', 'Treasury', 'Senate', 'House', 'White House',

'Ironlight', 'Vorhees', 'Erik Vorhees',
'Michael Saylor', 'Saylor', 'Robert Kiyosaki', 'Paul Atkins',
'David Schwartz', 'Mike Novogratz', 'Sam Altman', 'Elon Musk',
'ShapeShift', 'Brad Garlinghouse', 'Garlinghouse', 'Monica Long', 'Vitalik Buterin',
'Satoshi Nakamoto', 'Justin Sun', 'Jed McCaleb', 'Charles Hoskinson',
'Goldman Sachs', 'Strategy', 'Donald Trump', 'Trump',
'Robinhood', 'Tether', 'Ripple', 'Flare', 'ATHENA', 'Ethena',
'Metaplanet', 'DooriNews', 'Shiba Inu', 'Shibarium',

'Brazil', 'China', 'Japan', 'Korea', 'South Korea', 'Iran', 'Israel', 'Qatar',
'Mastercard', 'Visa',

'SEC', 'CFTC', 'OCC', 'ETF', 'IPO', 'CTO',
'XRP', 'XLM', 'BTC', 'ETH', 'SHIB', 'USDC', 'USDT', 'XAUT', 'SOL', 'DOGE',

'Bitcoin', 'Ethereum', 'Stablecoin', 'Tokenization', 'Custody', 'Seed Phrase',
'Lawsuit', 'Regulation', 'Interpretation',

'DeFi', 'NFT', 'Web3',
'BitMine',
'Tom Lee', 'Jerome Powell', 'Powell',
'Nevada', 'JPMorgan', 'Ryde', 'Bybit', 'Ledger',
'Circle', 'MoneyGram', 'Upbit', 'Bithumb', 'Binance',
'Apple', 'PayPal', 'Stripe', 'Gemini', 'Kalshi', 'Zedxion',
'Evernorth', 'XRPLedger', 'World Gold Council',
'Gold', 'Digital Gold', 'Silver', 'Bitcoin Quantum', 'BIP360',
'OpenAI', 'Anthropic', 'Super Micro', 'AI', 'LNG',
'BAZAN', 'California', 'Morgan Stanley', 'Kraken',
'Genius Act', 'Genius', 'Act', 'ICE', 'CLARITY',
'BlackRock', 'MoonPay', 'Coinbase', 'Hidden Road', 'GameStop',
'Google', 'India', 'Wells Fargo', 'Peter Schiff', 'Fannie Mae',
'EEZ', 'Buffett',
'Strive', 'Tuttle', 'Strive Asset Management', 'STRC', 'SATA', 'Nium',
'Open Credit', 'Smart Contract', 'Smart Contracts', 'Private Credit', 'Private Credits', 'Institutional Capital',
'BCH', 'Bitcoin Cash', '비트코인캐시',
'노동부', 'U.S. Department of Labor', 'US Department of Labor', 'Department of Labor', 'Labor Department',
	'밈코인','Mimcoin','금융', '암호화폐', '트론', 'TRX', 'TRON', '호주', '미국',
'BitGo', 'TRON', 'TRX', 'Australia', 'Franklin Templeton', 'Tony Pecore',
'프랭클린템플턴', '토니피코어','WisdomTree', '위즈덤트리', 'CLARITY Act', '클래리티법',

	
}

MANUAL_TRANSLATIONS = {
    'Ironlight': '아이언라이트',
    '아이언라이트': '아이언라이트',

    'Vorhees': '보어히스',
    '보어히스': '보어히스',

    'Erik Vorhees': '에릭보어히스',
    '에릭보어히스': '에릭보어히스',

    'Michael Saylor': '마이클세일러',
    '마이클세일러': '마이클세일러',

    'Saylor': '세일러',
    '세일러': '세일러',

    'Robert Kiyosaki': '로버트기요사키',
    '로버트기요사키': '로버트기요사키',

    'Paul Atkins': '폴앳킨스',
    '폴앳킨스': '폴앳킨스',

    'David Schwartz': '데이비드슈워츠',
    '데이비드슈워츠': '데이비드슈워츠',

    'Mike Novogratz': '마이크노보그라츠',
    '마이크노보그라츠': '마이크노보그라츠',

    'Sam Altman': '샘알트만',
    '샘알트만': '샘알트만',

    'Elon Musk': '일론머스크',
    '일론머스크': '일론머스크',

    'ShapeShift': '셰이프시프트',
    '셰이프시프트': '셰이프시프트',

    'Brad Garlinghouse': '갈링하우스',
	'Grlinghouse':'갈링하우스',
    '갈링하우스': '갈링하우스',

    'Monica Long': '모니카롱',
    '모니카롱': '모니카롱',

    'Vitalik Buterin': '비탈릭부텔린',
    '비탈릭부텔린': '비탈릭부텔린',

    'Satoshi Nakamoto': '사토시나카모토',
    '사토시나카모토': '사토시나카모토',
	'Nakamoto': '나카모토',
    '나카모토': '나카모토',

    'Justin Sun': '저스틴썬',
    '저스틴썬': '저스틴썬',

    'Jed McCaleb': '제드맥케일럽',
    '제드맥케일럽': '제드맥케일럽',

    'Charles Hoskinson': '찰스호스킨슨',
    '찰스호스킨슨': '찰스호스킨슨',

    'Goldman Sachs': '골드만삭스',
    '골드만삭스': '골드만삭스',

    'Strategy': '스트래티지',
    '스트래티지': '스트래티지',

    'Donald Trump': '도널드트럼프',
    '도널드트럼프': '도널드트럼프',

    'Trump': '트럼프',
    '트럼프': '트럼프',

    'Robinhood': '로빈후드',
    '로빈후드': '로빈후드',

    'Tether': '테더',
    '테더': '테더',

    'Ripple': '리플',
    '리플': '리플',

	'TRX': '트론',
    'TRON': '트론',

    'Flare': '플레어',
    '플레어': '플레어',

    'FLR': 'FLR',
    'ATHENA': '아테나',
    '아테나': '아테나',

    'ENA': '에테나',
    'Ethena': '에테나',
    '에테나': '에테나',

    'Metaplanet': '메타플래닛',
    '메타플래닛': '메타플래닛',

    'DooriNews': '도리뉴스',
    '도리뉴스': '도리뉴스',

    'Shiba Inu': '시바이누',
    '시바이누': '시바이누',
    '시바견': '시바이누',

    'Shibarium': '시바리움',
    '시바리움': '시바리움',

    'Swift': 'SWIFT',

    'Fed': '연준',
    'Federal Reserve': '연준',
    '연준': '연준',

    'Treasury': '재무부',
    '재무부': '재무부',

    'White House': '백악관',
    '백악관': '백악관',

    'Brazil': '브라질',
    '브라질': '브라질',

    'China': '중국',
    '중국': '중국',

    'Japan': '일본',
    '일본': '일본',

    'Korea': '한국',
    'South Korea': '한국',
    '한국': '한국',

    'United States': '미국',
    'US': '미국',
    '미국': '미국',

    'Iran': '이란',
    '이란': '이란',

    'Israel': '이스라엘',
    '이스라엘': '이스라엘',

    'Qatar': '카타르',
    '카타르': '카타르',

    'mastercard': '마스터카드',
    'Mastercard': '마스터카드',
    '마스터카드': '마스터카드',

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
    '비트코인': '비트코인',

    'Ethereum': '이더리움',
    '이더리움': '이더리움',

    'Stablecoin': '스테이블코인',
    'stablecoin': '스테이블코인',
    '스테이블코인': '스테이블코인',

    'Tokenization': '토큰화',
    '토큰화': '토큰화',

    'Custody': '수탁',
    '수탁': '수탁',

    'Seed Phrase': '시드문구',
    '시드문구': '시드문구',

    'Lawsuit': '소송',
    '소송': '소송',

    'Regulation': '규제',
    '규제': '규제',

    'Interpretation': '해석',
    '해석': '해석',

    'DeFi': 'DeFi',
    '디파이': 'DeFi',

    'NFT': 'NFT',
    'Web3': 'Web3',

    'BitMine': '비트마인',
    '비트마인': '비트마인',

    'Tom Lee': '톰리',
    '톰리': '톰리',

    'Thomasg.eth': 'Thomasgeth',
    'Time Traveler': 'TimeTraveler',
    'John Squire': 'JohnSquire',

    'Uniswap': '유니스왑',
    '유니스왑': '유니스왑',

    'Hayden Adams': 'HaydenAdams',

    'Jerome Powell': '제롬파월',
    'Powell': '파월',
    '제롬파월': '제롬파월',
    '파월': '파월',

    'America': '미국',

    'Nevada': '네비다주',
    '네비다주': '네비다주',

    'J.P. Morgan': 'JPMorgan',
    'JP Morgan': 'JPMorgan',
    'JPMorgan': 'JPMorgan',
    '제이피모건': 'JPMorgan',

    'Ryde': '라이드',
    '라이드': '라이드',

    'Bybit': '바이비트',
    '바이비트': '바이비트',

    'Ledger': 'Ledger',
    '서클': '서클',
    'Circle': '서클',

    'MoneyGram': '머니그램',
    '머니그램': '머니그램',

    'Upbit': '업비트',
    '업비트': '업비트',

    'Bithumb': '빗썸',
    '빗썸': '빗썸',

    'Binance': '바이낸스',
    '바이낸스': '바이낸스',

    'Apple': '애플',
    '애플': '애플',

    'PayPal': '페이팔',
    '페이팔': '페이팔',

    'Stripe': '스트라이프',
    '스트라이프': '스트라이프',

    'Gemini': '제미니',
    '제미니': '제미니',

    'Kalshi': '칼시',
    '칼시': '칼시',

    'Zedxion': '제드시온',
    '제드시온': '제드시온',

    'Evernorth Holdings': '에버노스',
    'Evernorth': '에버노스',
    '에버노스': '에버노스',

    'XRPLedger': 'XRPLedger',
    'XRP Ledger': 'XRPLedger',

    'World Gold Council': '세계금협회',
    '세계금협회': '세계금협회',

    'Gold': '금',
    '금': '금',

    'Digital Gold': '디지털금',
    '디지털금': '디지털금',

    'Silver': '은',
    '은': '은',

    'Bitcoin Quantum': '비트코인퀀텀',
    '비트코인퀀텀': '비트코인퀀텀',

    'BIP360': 'BIP360',

    'OpenAI': 'OpenAI',
    '오픈에이아이': 'OpenAI',

    'Anthropic': 'Anthropic',
    '앤트로픽': 'Anthropic',

    'Super Micro': '슈퍼마이크로',
    '슈퍼마이크로': '슈퍼마이크로',

    'AI': 'AI',
    'LNG': 'LNG',

    'BAZAN': '바잔',
    '바잔': '바잔',

    'California': '캘리포니아',
    '캘리포니아': '캘리포니아',

    'Morgan Stanley': '모건스탠리',
    'MorganStanley': '모건스탠리',
    '모건스탠리': '모건스탠리',

    'Kraken': '크라켄',
    '크라켄': '크라켄',

    'Genius Act': '지니어스법안',
    '지니어스법안': '지니어스법안',
    'Genius': '지니어스',
    '지니어스': '지니어스',
    'Act': '법안',
    '법안': '법안',

    'ICE': 'ICE',

    'CLARITY': '클래리티',
    '클래리티': '클래리티',

    'Blackrock': '블랙록',
    'BlackRock': '블랙록',
    '블랙록': '블랙록',

    'MoonPay': '문페이',
    '문페이': '문페이',

    'coinbase': '코인베이스',
    'Coinbase': '코인베이스',
    '코인베이스': '코인베이스',

    'Hidden Road': '히든로드',
    '히든로드': '히든로드',

    'GameStop': '게임스탑',
    '게임스탑': '게임스탑',

    'Google': '구글',
    '구글': '구글',

    'India': '인도',
    '인도': '인도',

    'Wells Fargo': '웰스파고',
    '웰스파고': '웰스파고',

    'Peter Schiff':'Peter Schiff', 
    '피터 쉬프':'피터쉬프',

    'Fannie Mae':'FannieMae', 
    '패니 매':'패니매',

	'EEZ':'EEZ',

	'Buffett':'버핏',

	'Strive': '스트라이브',
    'Tuttle': '터틀',
    'Strive Asset Management': '스트라이브자산운용',
    'STRC': 'STRC',
    'SATA': 'SATA',
    'Nium': '니움',
    'NIUM': '니움',
	'Visa': '비자',
    'Mastercard': '마스터카드',
	'DeFi': '디파이',
    '디파이': '디파이',
    'Open Credit': '오픈크레딧',
    'OpenCredit': '오픈크레딧',
    '오픈크레딧': '오픈크레딧',
    'Smart Contract': '스마트계약',
    'Smart Contracts': '스마트계약',
    'Private Credit': '프라이빗크레딧',
    'Private Credits': '프라이빗크레딧',
    '프라이빗크레딧': '프라이빗크레딧',
    'Institutional Capital': '기관자금',
    '기관자금': '기관자금',
	'Elizabeth Warren': '엘리자베스워런',
    '엘리자베스 워런': '엘리자베스워런',
    '엘리자베스워런': '엘리자베스워런',
    'Government': '정부',
    '정부': '정부',
	'Bitcoin Cash': '비트코인캐시',
    '비트코인캐시': '비트코인캐시',
    'BCH': 'BCH',

    'U.S. Department of Labor': '노동부',
    'US Department of Labor': '노동부',
    'Department of Labor': '노동부',
    'Labor Department': '노동부',
    '노동부': '노동부',

    '401(k)': '401k',
	'401 k': '401k',
    '401K': '401k',
    '401k': '401k',
	'mim coin':'밈코인',
	'밈코인':'밈코',

	'TRON': '트론',
    'TRX': '트론',
    '트론': '트론',
    'Australia': '호주',
    'Australian': '호주',
    '호주': '호주',
    'Franklin Templeton': '프랭클린템플턴',
    '프랭클린템플턴': '프랭클린템플턴',
    'Tony Pecore': '토니피코어',
    '토니피코어': '토니피코어',
    'Crypto': '암호화폐',
    'crypto': '암호화폐',
    '암호화폐': '암호화폐',
    'Finance': '금융',
    'financial': '금융',
    '금융': '금융',
	'WisdomTree': '위즈덤트리',
    '위즈덤트리': '위즈덤트리',
    'CLARITY Act': '클래리티법',
    '클래리티법': '클래리티법',

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
SUMMARY_SENTENCES = 3
GEMINI_INPUT_COST_PER_1M = 0.30
GEMINI_OUTPUT_COST_PER_1M = 2.50
AVG_CHARS_PER_TOKEN = 4
SHOW_COST_LOG = True

def normalize_url(url: str) -> str:
    url = (url or '').strip().lower()
    url = re.sub(r'^https?://', '', url)
    url = url.rstrip('/')
    return url

def log(msg: str) -> None:
    print(msg, flush=True)
	
def estimate_tokens_from_text(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / AVG_CHARS_PER_TOKEN))


def log_gemini_cost(title: str, prompt: str, output: str) -> None:
    if not SHOW_COST_LOG:
        return

    input_tokens = estimate_tokens_from_text(prompt)
    output_tokens = estimate_tokens_from_text(output)

    input_cost = (input_tokens / 1_000_000) * GEMINI_INPUT_COST_PER_1M
    output_cost = (output_tokens / 1_000_000) * GEMINI_OUTPUT_COST_PER_1M
    total_cost = input_cost + output_cost

    log(
        f"[Gemini 비용] {title[:60]} | "
        f"입력토큰≈{input_tokens} | 출력토큰≈{output_tokens} | "
        f"예상비용≈${total_cost:.6f}"
    )

def has_precious_metal_context(text: str, metal: str) -> bool:
    raw = text or ""
    norm = normalize_text(raw)

    if metal == 'gold':
        patterns = [
            r'(^|\s)gold($|\s)',
            r'(^|\s)digital gold($|\s)',
            r'(^|\s)world gold council($|\s)',
            r'(^|\s)xaut($|\s)',
        ]
    elif metal == 'silver':
        patterns = [
            r'(^|\s)silver($|\s)',
        ]
    else:
        return False

    return any(re.search(p, norm, re.I) for p in patterns)

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

def is_duplicate(title: str, posted: dict, url: str = "") -> bool:
    title_key = story_hash(title)
    if title_key in posted:
        return True

    norm_url = normalize_url(url)
    if norm_url:
        for item in posted.values():
            old_url = normalize_url(item.get('url', ''))
            if old_url and old_url == norm_url:
                return True

    return False

def update_posted(title: str, posted: dict, url: str = "", signature: str = ""):
    posted[story_hash(title)] = {
        'title': title,
        'url': normalize_url(url),
        'signature': signature,
        'ts': datetime.now(timezone.utc).isoformat()
    }

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
    url = (story.get('url', '') or '').lower()

    portfolio_context_terms = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'xrp', 'ripple', 'xlm', 'stellar',
        'ada', 'cardano', 'trx', 'tron', 'bnb', 'bch', 'bitcoin cash',
        'shib', 'shiba inu', 'etc', 'flr', 'athena', 'ena', 'usdc', 'usdt',
        '비트코인', '이더리움', '리플', '스텔라', '에이다', '트론',
        '바이낸스코인', '비트코인캐시', '시바이누', '플레어', '에테나'
    ]

    has_portfolio_context = any(contains_exact_term(raw_text, t) for t in portfolio_context_terms)

    if 'tokenpost.kr/news/tech/' in url:
        return False

    for neg in NEGATIVE_KEYWORDS:
        if neg.lower() in raw_lower:
            print(f"[NEGATIVE 제외] {story.get('title', '')} / {neg}")
            return False

    if contains_bad_signal(raw_text):
        print(f"[부정시그널 제외] {story.get('title', '')}")
        return False

    allowed_coin_found = any(contains_exact_term(raw_text, c) for c in coins)
    if allowed_coin_found:
        print(f"[허용코인 통과] {story.get('title', '')}")
        return True

    if contains_non_portfolio_asset(raw_text):
        print(f"[포폴외코인 제외] {story.get('title', '')}")
        return False

    if contains_stock_context(raw_text):
        print(f"[주식기사 제외] {story.get('title', '')}")
        return False

    other_coin_found = any(contains_exact_term(raw_text, c) for c in OTHER_COINS)
    if other_coin_found:
        print(f"[기타코인 제외] {story.get('title', '')}")
        return False

    ai_allow_terms = []
    if any(contains_exact_term(raw_text, term) for term in ai_allow_terms):
        print(f"[AI/기업기사 통과] {story.get('title', '')}")
        return True

    policy_allow_terms = ['stablecoin', 'sec', 'cftc', 'etf', 'law', 'regulation', 'fed', 'inflation', 'bank', 'treasury']
    policy_hits = sum(1 for term in policy_allow_terms if contains_exact_term(raw_text, term))
    if has_portfolio_context and policy_hits >= 1:
        print(f"[포폴+정책 통과] {story.get('title', '')}")
        return True
  
    for kw in korean_keywords:
        if has_portfolio_context and kw.lower() in raw_lower:
            print(f"[포폴+한글키워드 통과] {story.get('title', '')} / {kw}")
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

def has_weak_reference(text: str) -> bool:
    low = f" {text.lower()} "
    weak_refs = [
        ' it ', ' they ', ' them ', ' this ', ' that ', ' these ', ' those ',
        ' its ', ' their ', ' his ', ' her ',
        '그것', '그들이', '그들', '이는', '이것', '저것', '해당', '이를', '그의', '그녀의'
    ]
    return any(x in low for x in weak_refs)

def summarize_text(text: str, title: str = "", max_sentences: int = 3) -> str:
    text = cleanup_text(text)
    title = cleanup_text(title)

    if is_weak_text(text):
        text = title

    raw_sentences = re.split(r'(?<=[.!?])\s+|\n+|(?<=다)\s+|(?<=임)\s+|(?<=음)\s+', text)

    indexed_sentences = []
    for idx, s in enumerate(raw_sentences):
        s = s.strip(" ,")
        if not s or is_bad_line(s):
            continue
        indexed_sentences.append((idx, s))

    if not indexed_sentences:
        return title

    ranked = sorted(
        indexed_sentences,
        key=lambda x: score_sentence(x[1], title),
        reverse=True
    )

    picked = []
    picked_idx = set()
    total_len = 0
    max_len = 180

    for idx, s in ranked:
        candidates = []

        if has_weak_reference(s) and idx > 0:
            prev_s = raw_sentences[idx - 1].strip(" ,")
            if prev_s and not is_bad_line(prev_s):
                candidates.append((idx - 1, prev_s))

        candidates.append((idx, s))

        stop_outer = False

        for cand_idx, cand_s in candidates:
            if cand_idx in picked_idx:
                continue

            if total_len + len(cand_s) > max_len and picked:
                stop_outer = True
                break

            picked.append((cand_idx, cand_s))
            picked_idx.add(cand_idx)
            total_len += len(cand_s)

            if len(picked) >= max_sentences:
                stop_outer = True
                break

        if stop_outer:
            break

    if not picked:
        return title

    picked.sort(key=lambda x: x[0])
    summary = ' '.join(s for _, s in picked)
    summary = re.sub(r'\s+', ' ', summary).strip()
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
		(r'밝혔다\.?', '밝힘'),
        (r'전했다\.?', '전함'),
        (r'설명했다\.?', '설명함'),
        (r'덧붙였다\.?', '덧붙임'),
    ]

    leftovers = re.findall(r'[\w가-힣]+(?:했습니다|하였습니다|합니다|있습니다|됩니다|나타냅니다|미칩니다)', text)
    if leftovers:
        log("말투 치환 추가 필요 후보: " + ", ".join(leftovers[:10]))

    for pat, rep in rules:
        text = re.sub(pat, rep, text)

    text = re.sub(r'\[\.\.\.\]|\.\.\.|…', ' ', text)
    text = re.sub(r'\s*:\s*\[\s*\]', ' ', text)
    text = re.sub(r'([가-힣])([A-Z][a-zA-Z]+)', r'\1 \2', text)
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

    for kw in KOREAN_TAG_KEYWORDS:
        # 금/은은 직접 포함 검사 금지
        if kw in {'금', '은'}:
            continue
        if kw in text:
            entities.append(kw)

    # gold/silver는 영어 문맥일 때만 수동 추가
    if has_precious_metal_context(text, 'gold'):
        entities.append('Gold')
    if has_precious_metal_context(text, 'silver'):
        entities.append('Silver')

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
    return entity.replace(' ', '')

def inject_entity_hashtags(summary: str, entities: list[str]) -> tuple[str, list[str]]:
    text = summary
    final_tags = []

    coin_inline_map = {
        'BTC': '비트코인',
        'ETH': '이더리움',
        'XRP': '리플',
        'XLM': '스텔라',
        'ADA': '에이다',
        'TRX': '트론',
        'BNB': '바이낸스',
        'BCH': '비트코인캐시',
        'SHIB': '시바이누',
        'USDC': 'USDC',
        'USDT': 'USDT',
    }

    for ent in sorted(entities, key=len, reverse=True):
        ent_upper = ent.upper()

        if ent_upper in PORTFOLIO_COINS or ent_upper in CRYPTO_ACRONYMS:
            if f'#{ent_upper}' not in final_tags:
                final_tags.append(f'#{ent_upper}')

            korean_name = coin_inline_map.get(ent_upper, ent_upper)
            tag_text = f'#{korean_name}'

            if tag_text in text:
                continue

            replaced = False
            for base in [korean_name, ent, ent_upper]:
                for p in ['가','이','은','는','를','을','의','와','과','로','도','만','에서','에게','까지']:
                    new_text, count = re.subn(re.escape(base + p), f'{tag_text} {p}', text, count=1)
                    if count:
                        text = new_text
                        replaced = True
                        break
                if replaced:
                    break

            if not replaced:
                for base in [korean_name, ent, ent_upper]:
                    new_text, count = re.subn(re.escape(base), tag_text, text, count=1)
                    if count:
                        text = new_text
                        break

            continue

        korean = entity_korean_name(ent)
        tag_text = '#' + korean.replace(' ', '')
        eng_tag = '#' + ent.replace(' ', '')
        if eng_tag not in final_tags:
            final_tags.append(eng_tag)

        normalized_korean_tag = '#' + korean.replace(' ', '')
        normalized_eng_tag = '#' + ent.replace(' ', '')

        if normalized_korean_tag in text or normalized_eng_tag in text:
            continue

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

def fix_broken_inline_hashtags(text: str) -> str:
    text = re.sub(r'#+', '#', text)
    text = re.sub(r'#\s+', '#', text)

    # 정말 깨진 해시태그만 수동 복구
    text = text.replace('#미 국', '#미국')
    text = text.replace('#비트 코 인', '#비트코인')
    text = text.replace('#이더 리 움', '#이더리움')
    text = text.replace('#시 바 이 누', '#시바이누')
    text = text.replace('#신 시 아 루 미 스', '#신시아루미스')

    return text


def remove_duplicate_inline_hashtags(text: str) -> str:
    seen = set()

    def repl(match):
        tag = match.group(0)
        key = tag.lower()
        if key in seen:
            return ''
        seen.add(key)
        return tag

    text = re.sub(r'#[가-힣A-Za-z0-9]+', repl, text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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

    text = re.sub(r'^[^.!?\n]{0,40}에 따르면[, ]*', '', text)
    text = re.sub(r'본 콘텐츠는 특정 종목이나 자산에 대한 투자 조언이 아니며[^.!?\n]*', '', text)
    text = re.sub(r'변동성 높은 시장에서 흔들리지 않는 투자 마인드를 가꾸기 위한 심리적 환기 목적으로 제공됩니다[^.!?\n]*', '', text)

    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fix_translation_terms(text: str) -> str:
    replacements = {
    '401(k)': '401k',
    '401 k': '401k',
    '401K': '401k',
    'U.S. Department of Labor': '미국 노동부',
    'US Department of Labor': '미국 노동부',
    'Department of Labor': '노동부',
    'Labor Department': '노동부',
    'Bitcoin Cash': '비트코인캐시',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r'\[\.\.\.\]|\.\.\.|…', ' ', text)
    text = re.sub(r'\s*:\s*\[\s*\]', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()

    return text

def filter_final_tags(tags: list[str]) -> list[str]:
    allowed_exact = {
        '#BTC','#ETH','#XRP','#XLM','#ADA','#TRX','#BNB','#BCH','#SHIB','#ETC','#FLR','#ATHENA','#ETNA','#USDC','#USDT', '#Ethereum',
        '#SoftBank','#JPMorgan','#TomLee','#JeromePowell','#Iran','#Israel','#US','#DeFi','#NFT','#Web3','#Stablecoin','#MorganStanley','#shibarium',
        '#BitMine','#Silver','#Gold','#Uniswap','#Ripple','#XRPL','#ETF','#AI','#SEC','#VR','#TimeTraveler','#JohnSquire','#Nvidia','#Ohio','#Coinbase','#DeFi','#NFT', '#Web3','#CFTC','#IPO','#Korea','#Cardano','#GoldmanSachs','#Strategy','#DonaldTrump','#Trump','#Robinhood', '#Japan', '#Tether',''#Evernorth', '#Upbit', '#Bithumb','#BradGarlinghouse', '#DavidSchwartz', '#MonicaLong',
'#VitalikButerin', '#SatoshiNakamoto', '#ElonMusk',
'#JustinSun', '#JedMcCaleb', '#CharlesHoskinson','#US','#Ledger','#Circle','#Fed', '#Treasury', '#BlackRock', '#Binance', '#Mining', '#Blockchain',
'#Crypto', '#Altcoin', '#Liquidity', '#FSS', '#OpenAI', '#JPMorgan', '#FX', '#RWA', '#Gamestop', '#Citigroup',
		'#Mastercard','#NYSE','#LatinAmerica','#WellsFargo','#CLARITY','#Russia','#BRICS','#Kalshi','#WellsFargo','#401k', '#노동부','Mimcoin',
		'#금융', '#암호화폐', '#트론', '#TRX', '#TRON', '#호주', '#미국',
'#프랭클린템플턴', '#토니피코어','#WisdomTree','#CLALITYAct',
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

def fetch_article_text(url: str) -> str:
    try:
        html_text = http_get(url, timeout=10)
    except Exception:
        return ""

    patterns = [
        r'<article[^>]*>(.*?)</article>',
        r'<main[^>]*>(.*?)</main>',
        r'<body[^>]*>(.*?)</body>',
    ]

    block = ""
    for pat in patterns:
        m = re.search(pat, html_text, re.I | re.S)
        if m:
            block = m.group(1)
            break

    if not block:
        block = html_text

    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', block, re.I | re.S)
    cleaned = []
    for p in paragraphs:
        t = re.sub(r'<[^>]+>', ' ', unescape(p))
        t = re.sub(r'\s+', ' ', t).strip()
        if len(t) >= 40:
            cleaned.append(t)

    text = "\n".join(cleaned[:20]).strip()
    text = cleanup_text(text)
    return text[:12000]


def rewrite_summary_with_gemini(title: str, article_text: str, fallback_text: str = "") -> str:
    source_text = (article_text or "").strip()
    if not source_text:
        source_text = (fallback_text or "").strip()
    if not source_text:
        source_text = title.strip()

    if not GEMINI_API_KEY:
        return ""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = f"""
너는 텔레그램 암호화폐 뉴스 채널 편집자다.

아래 기사 내용을 보고 한국어로 자연스럽게 2~3문장으로 다시 써라.

규칙:
- 텔레그램 업로드용 짧은 문장으로 작성
- 첫 문장부터 핵심 키워드를 강하게 시작(느낌표 물음표는 사용금지)
- 해시태그는 마지막 footer에서만 사용됨
- 사람 이름, 기관명, 코인명도 일반 텍스트로 자연스럽게 작성
- 해시태그 사용하면 띄어쓰기 필수
- 한국어 띄어쓰기를 자연스럽게 유지할 
- 반드시 2~3문장만 작성
- 각 문장은 짧게 작성
- 한 문장이 끝날 때마다 반드시 한 줄 띄울 것
- 전체 길이는 120자 안팎으로 유지
- 불필요한 배경 설명 금지
- 문장 끝은 텔레그램 축약형으로 정리할 것 (예: 밝혔다→밝힘, 전했다→전함, 설명했다→설명함)
- 필요하면 불릿(- 또는 ➖) 사용 가능
- 너무 딱딱한 기사체보다, 빠르게 읽히는 텔레그램 뉴스 톤으로 작성
- 직역투 금지
- 기사에 없는 내용은 추측해서 추가 금지
- 매체명, first appeared on, sponsor 문구 제거
- 문장은 너무 길지 않게 끊기
- 출력은 요약문만 작성
- 마지막 해시태그 줄, 출처, 링크 문구는 작성하지 말 것
- 사람 이름, 국가명, 브랜드명, 코인명은 중간 띄어쓰기 없이 자연스럽게 작성
- 해시태그 내부 단어를 분리하지 말 것
- 본문에는 해시태그를 넣지 말 것
- 아래 표현은 절대 쓰지 말 것:
  하락세, 약세, 급락, 반등 실패, 상승으로 이어지지 못함, 강세 전환 신호 없음, 불확실, 이유, 전망, 크로스오버
- 가격 차트 해설 기사나 기술적 분석 기사처럼 보이면 빈 문자열만 반환할 것

제목:
{title}

본문:
{source_text}
""".strip()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        text = getattr(response, "text", "") or ""
        text = cleanup_text(text)
        text = fix_translation_terms(text)
        text = fix_truncated_phrases(text)
        text = normalize_style(text)
        text = cleanup_text(text)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()

        log_gemini_cost(title, prompt, text)

        return text

    except Exception as e:
        log(f"Gemini 요약 실패: {e}")
        return ""


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

    tags = set()

    # 핵심 자산
    if 'btc' in text or 'bitcoin' in text or '비트코인' in text:
        tags.add('asset_btc')
    if 'eth' in text or 'ethereum' in text or '이더리움' in text:
        tags.add('asset_eth')
    if 'xrp' in text or 'ripple' in text or '리플' in text:
        tags.add('asset_xrp')
    if 'xrpl' in text or 'xrp ledger' in text or 'xrpledger' in text or '엑스알피레저' in text:
        tags.add('asset_xrpl')
    if 'bch' in text or 'bitcoin cash' in text or '비트코인캐시' in text:
        tags.add('asset_bch')
    if 'shib' in text or 'shiba inu' in text or '시바이누' in text:
        tags.add('asset_shib')
    if 'usdc' in text:
        tags.add('asset_usdc')
    if 'usdt' in text:
        tags.add('asset_usdt')

    # 기관/회사
    if 'coinbase' in text or '코인베이스' in text:
        tags.add('org_coinbase')
    if 'base' in text or '베이스' in text:
        tags.add('org_base')
    if 'google' in text or '구글' in text:
        tags.add('org_google')
    if 'labor department' in text or 'department of labor' in text or '노동부' in text:
        tags.add('org_labor')

    # 정책/주제
    if '401k' in text or '401 k' in text or '401(k)' in text or 'retirement' in text or '퇴직연금' in text or '퇴직계좌' in text:
        tags.add('topic_401k')

    if 'stablecoin' in text or '스테이블코인' in text:
        tags.add('topic_stablecoin')
    if 'tokenized market' in text or 'tokenized markets' in text or '토큰화 시장' in text:
        tags.add('topic_tokenized_market')
    if 'developer ecosystem' in text or 'developers' in text or '개발자 생태계' in text:
        tags.add('topic_developers')
    if 'ai agent' in text or 'ai agents' in text or 'agent economy' in text or 'ai 에이전트' in text:
        tags.add('topic_ai_agent')

    if 'quantum' in text or '양자' in text:
        tags.add('topic_quantum')
    if 'wallet' in text or '지갑' in text:
        tags.add('topic_wallet')
    if 'ledger' in text or '레저' in text:
        tags.add('topic_ledger')

    # 규제/거시
    if 'sec' in text:
        tags.add('macro_sec')
    if 'etf' in text:
        tags.add('macro_etf')
    if 'fed' in text or 'federal reserve' in text or '연준' in text:
        tags.add('macro_fed')
    if 'treasury' in text or '재무부' in text:
        tags.add('macro_treasury')

    # 숫자 소수만
    nums = re.findall(r'\b\d+(?:,\d+)?(?:\.\d+)?\b', text)
    for n in nums[:2]:
        tags.add(f'num_{n}')

    return ' | '.join(sorted(tags))


def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = normalize_for_duplicate(story.get('title', ''))
    signature = build_story_signature(story)

    for old_title in seen_titles:
        ratio = SequenceMatcher(None, title, old_title).ratio()
        if ratio >= 0.80:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    if len(signature.split('|')) < 2:
        return False

    for old_sig in seen_signatures:
        ratio = SequenceMatcher(None, signature, old_sig).ratio()
        if ratio >= 0.88:
            log(f"[시그니처 유사도 중복] {signature} <> {old_sig} / {ratio:.2f}")
            return True

    return False


def format_summary_for_telegram(text: str, max_sentences: int = 3, max_chars: int = 120) -> str:
    text = (text or "").strip()
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text).strip()

    # 문장 단위 분리
    sentences = re.split(r'(?<=[.!?])\s+|(?<=음)\s+|(?<=임)\s+|(?<=됨)\s+|(?<=함)\s+|(?<=밝힘)\s+|(?<=전함)\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    picked = []
    total = 0

    for s in sentences:
        if len(picked) >= max_sentences:
            break
        if picked and total + len(s) > max_chars:
            break
        picked.append(s)
        total += len(s)

    if not picked and text:
        picked = [text[:max_chars].rstrip()]

    # 문장 끝마다 한 줄 띄우기
    return '\n\n'.join(picked).strip()

def finalize_summary_ending(text: str) -> str:
    text = re.sub(r'좋은\s*덩어리$', '', text)
    text = re.sub(r'([가-힣]+)음고 말함$', r'\1음', text)
    text = re.sub(r'([가-힣]+)고 말함$', r'\1', text)
    text = re.sub(r'매도가 있었음.*$', '매도가 있었음', text)
    text = re.sub(r'커졌음.*$', '커졌음', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
	
def build_message(story: dict) -> str:
    title = story.get('title', '')
    desc = story.get('desc', '')
    article_text = fetch_article_text(story.get('url', ''))

    summary_ko = rewrite_summary_with_gemini(
        title=title,
        article_text=article_text,
        fallback_text=desc
    )

    if not summary_ko:
        raw_source = f"{title}. {desc}"
        raw_summary = summarize_text(
            raw_source,
            title=title,
            max_sentences=SUMMARY_SENTENCES
	    )
        summary_ko = translate_text_to_korean(raw_summary)
        summary_ko = cleanup_text(summary_ko)
        summary_ko = fix_translation_terms(summary_ko)
        summary_ko = fix_truncated_phrases(summary_ko)
        summary_ko = normalize_style(summary_ko)
        summary_ko = cleanup_text(summary_ko)

    entities = extract_entities(story, max_tags=8)
    entities = [
        e for e in entities
        if e in INLINE_TAG_WHITELIST or entity_korean_name(e) in INLINE_TAG_WHITELIST
    ]

    summary_ko, dynamic_tags = inject_entity_hashtags(summary_ko, entities)
    summary_ko = fix_broken_inline_hashtags(summary_ko)
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
        'blackrock': '#BlackRock',
        'fed': '#Fed',
        'federal reserve': '#Fed',
        'treasury': '#Treasury',
        'rwa': '#RWA',
        'mining': '#Mining',
        'california': '#California',
        'morgan stanley': '#MorganStanley',
        'kraken': '#Kraken',
        'Fannie Mae': '#FannieMae',
        'Peter Shiff': '#PeterShiff',
		'bitcoin cash': '#BCH',
        '비트코인캐시': '#BCH',
        'bch': '#BCH',

        'u.s. department of labor': '#노동부',
        'us department of labor': '#노동부',
        'department of labor': '#노동부',
        '노동부': '#노동부',

		'mim coin':'#밈코인',
		'밈코인':'#밈코인',

        '401(k)': '#401k',
        '401 k': '#401k',
        '401k': '#401k',
		'tron': '#트론',
		'trx': '#TRX',
		'australia': '#호주',
		'australian': '#호주',
		'franklin templeton': '#프랭클린템플턴',
		'tony pecore': '#토니피코어',
		'crypto': '#암호화폐',
		'finance': '#금융',
		'financial': '#금융',
		'미국': '#미국',
		'us': '#미국',
		'wisdomtree': '#위즈덤트리',
        'clarity act': '#클래리티법',
        '클래리티법': '#클래리티법',
    }
    if has_precious_metal_context(title_text, 'gold') and '#Gold' not in dynamic_tags:
        extra_footer_tags.append('#Gold')

    if has_precious_metal_context(title_text, 'silver') and '#Silver' not in dynamic_tags:
        extra_footer_tags.append('#Silver')

	
    for key, tag in footer_map.items():
        if contains_exact_term(title_text, key) and tag not in dynamic_tags:
            extra_footer_tags.append(tag)

    dynamic_tags.extend(extra_footer_tags)

    summary_ko = finalize_summary_ending(summary_ko)

    summary = summary_ko if summary_ko else story.get('title', '')
    summary = format_summary_for_telegram(summary, max_sentences=3, max_chars=120)
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

    for s in filtered:
        title = s.get('title', '')
        norm_title = normalize_for_duplicate(title)
        signature = build_story_signature(s)
        url = s.get('url', '').strip()

        if signature and len(signature.split('|')) >= 3 and signature in seen_topic_keys:
            log(f"[토픽중복 제외] {title}")
            log(f"  └ 시그니처: {signature}")
            continue

        if url and url in seen_urls:
            log(f"[URL중복 제외] {title}")
            continue

        if is_duplicate(title, posted, url):
            log(f"[제목/URL중복 제외] {title}")
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

        if signature:
            seen_topic_keys.add(signature)

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
            signature = build_story_signature(story)
            update_posted(story['title'], posted, story.get('url', ''), signature)
            state['posted'] = posted
            save_state(STATE_FILE, state)
            log(f"Posted: {story['title']}")
        else:
            log(f"Failed: {story['title']}")

        time.sleep(0.3)


if __name__ == '__main__':
    main()
