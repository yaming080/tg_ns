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

from openai import OpenAI


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
INITIAL_RUN = os.environ.get("INITIAL_RUN", "false").strip().lower() == "true"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini").strip() or "gpt-5.4-mini"
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

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
    ('코인니스', 'https://coinness.com/rss'),
    ('크립토뉴스닷뉴스', 'https://crypto.news/feed/'),
	
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
'ETF', 'SEC', 'CFTC', 'OCC', 'Polymarket', '폴리마켓',
'업비트', '빗썸', '바이낸스', '코인베이스',
'모건스탠리', '골드만삭스', '크라켄', '로빈후드',
'일론머스크', '갈링하우스', '제롬파월', '트럼프',
'아이언라이트', '보어히스', '에릭보어히스', '마이클세일러', '세일러', '로버트기요사키', '폴앳킨스',
'데이비드슈워츠', '마이크노보그라츠', '샘알트만', '셰이프시프트', '브래드갈링하우스', '모니카롱',
'비탈릭부텔린', '사토시나카모토', '저스틴썬', '제드맥케일럽', '찰스호스킨슨',
'스트래티지', '도널드트럼프', '테더', '플레어', 'FLR', '에테나', '에테나', '메타플래닛', '도리뉴스',
'시바리움', 'SWIFT', '백악관', '카타르', '마스터카드',
'IPO', 'CTO', 'XRP', 'XLM', 'BTC', 'ETH', 'SHIB', 'USDC', 'USDT', 'XAUT', 'SOL', 'DOGE',
    'RLUSD', 'FOMC', '헤스터피어스', '시카고상품거래소', '키발리스', '라울팔', '누바', '템포', '머니그램', '미카', '도호쿠은행', 'SBIRemit', '소프트뱅크', '트웬티원캐피털', '화이트비트', '티머시매사드', '무로', '산탄데르',
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
'프랭클린템플턴', '토니피코어','위즈덤트리', '클래리티법','마이클바', 'Michael Barr',
'홍콩', 'Hong Kong', 'HKMA', '홍콩금융관리국',
'HSBC', '스탠다드차타드', 'Standard Chartered','Michael Selig', '마이클셀릭', '마이클 셀릭',
'GENIUS', 'Genius Act',
'수탁업체','Jack Dorsey', '잭도시', 'Block','Paul Grewal', '폴그루월', '그루월',
'Brad Garlinghouse', '브래드갈링하우스', 'CEO',
'Genius Group', '지니어스그룹',
'Government', '정부', 'KYC',
'FTX', 'Nishad Singh', '니샤드싱',
'KBank', '케이뱅크',
'eToro', 'Taiwan', '대만',
'Coinone', '코인원',
'Bitget', 'SafePal', '마이크로소프트', 'Microsoft','XRPL', 'DEX', '탈중앙거래소', '사토시쿠사마','Bitdeer', '비트디어','Blockstream', '블록스트림',
'IMF', '토비아스아드리안', 'Tobias Adrian', 'RWA', '지니어스법안','Charles Schwab', '찰스슈왑','Oracle', '오라클','Peter Schiff','피터쉬프','금융당국', '사모대출', '잉글랜드은행', '앤드루베일리',
'한국은행', '보험연수원', '디지털화폐', '디지털통화', '지수보험',
'일본은행', '유가', '국채', '신현송', 'CBDC',
'메타플래닛', '일본 정부', '코인원', '코인원 AML',
'ABA', '예금', '은행예금', '금융위원회',
'모니카롱', 'ODL', 'FedNow', 'Fedwire',
'금융상품거래법', '금융상품', '스테이블코인', '클래리티법안',
'브래드갈링하우스', '리플 CEO', '블랙록 CEO',
'SMQKE', '신탁은행', '마스터계정', '금융감독청',
'주택시장', '제프박', '프로캡',
'업비트', 'USDT', '원화마켓', 'KRW',



	
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
'실용 가이드', '실용가이드','liquidates entire bitcoin stash',
'bitcoin stash',
'liquidate bitcoin holdings',
'liquidates holdings',
'debt repayment',
'repay debt',
'sell bitcoin to repay debt',
'전량 매각',
'비트코인 전량 매각',
'부채 상환 위해 매각',
'보유 비트코인 매각',

'lido dao', 'ldo', 'redemption', 'proposed sale', 'token sale',
'환매', '매각 제안',

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
	    'green monthly candle',
    'red monthly streak',
    'monthly streak',
    'monthly candle',
    'fear and greed',
    'fear index',
    'bottom signal',
    'local bottom',
    'what’s next for april',
    "what's next for april",
    'what comes next',
    'holds $',
    'holds usd',
    'fails to break higher',
    'price fails to break higher',
    'barely avoids',
    'worst red monthly',
    'worst monthly streak',
    '극단적 공포',
    '공포탐욕지수',
    '바닥 신호',
    '월봉',
    '녹색 월간 양초',
    '적색 월간',
    '상승 마감','mercado coin','mercado libre',
'loyalty rewards',
'loyalty program',
'rewards program','market recovery',
'active xrp users',
'active users cross',
'threshold enabling',
'0 recorded in xrp etf investments',
'april fools joke',
'minus monthly close',
'negative monthly close',
'positive monthly close',
'monthly close',
'market recovery possible',
'retail users',
'trading assistant',
'ai trading assistant',
'mulerun',
'wcf',
'winklevoss capital fund',
'gemini ipo',
'ipo controversy',
'discounted shares','transaction fee',
'transaction fees',
'inscription',
'inscriptions',
'soft fork',
'block space',
'block size',
'throughput',
'트랜잭션 수수료',
'인스크립션',
'소프트포크', 'bollinger',
'bollinger bands',
'major move looms',
'major move',
'tightening',
'descending channel',
'golden cross',
'burn rate rockets',
'network activity',
'eastpoint',
'eastpoint seoul',
'co-hosted',
'hosted by',
'conference 2026',
'september 28',
'registration',
'networking event',
'공동 주최',
'주최',
'개최',
'행사 개최','what’s next',
"what's next",
'know this before you join them',
'tumbling',
'lower highs',
'price correction',
'risk-off approach',
'could rise to',
'could see further dips',
'rejection at the',
'resistance level',
'financial report',
'재무 요약',
'재무 보고서',
'총자산',
'런웨이',
'grant efficiency',
'운영비 효율성',

'miners continue selling',
'miner selling',
'채굴자들이 계속 판매',
'채굴자들이 계속 매도',
'sells 3778 btc',
'sells btc in q1',
'판매하며',
'매도 중임',
'매도 기사',

'liquidation imbalance',
'liquidations',
'청산 불균형',
'청산액',
'손실을 입으면서',
'시장 손실',
'long traders',
'더 많은 손실',

'cloud mining',
'클라우드 마이닝',
'passive income',
'수동 소득',
'quantitative trading',
'트레이딩 플랫폼 비교',
'ultimate passive income showdown',

'whales woke up',
'whale activity',
'whales are selling',
'고래들이 활동을 재개',
'고래들 움직임',
'고래 매도',

'what to expect next week',
'what to expect',
'next week',
'예상되는 사항',
'예상 기사',

'high yield',
'apr',
'30 apr',
'leading high-yield opportunities',
'예치 시',
'예치하면',
'이자 제공',
'고수익 기회',

'investment guide',
'top 7 ways to earn eth',
'earn eth',
'build passive income',
'staking',
'lending',
'스테이킹',
'대출 등으로',
'수익 받는 방법',
'lost',
'loss',
'losses',
'sell at a loss',
'underwater',
'worst quarter',
'worst first quarter',
'first quarter since',
'glassnode report',
'glassnode',
'traders lost',
'손실',
'손실을 확정',
'최악의 분기',
'최악의 분기 이후',
'분석 보고서',
'canton',
'캔톤',
'canton token',
'canton network',
	
	
    'long', 'short', '롱', '숏', '롱 포지션', '숏 포지션', 'liquidation', 'liquidations',
    '시장 심리', 'market sentiment',
    'moew', 'realgo', 'fast or go home', 'challenge', 'cfd',
    'allunity', 'kalqix', 'kalaix', 'mainnet launch', 'clob dex',

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
    r'deposit',
    r'withdraw',
    r'withdrawal',

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
	

	r'\blisting\b',
    r'\blistings\b',
    r'\bdelisting\b',
    r'\bdelist\b',
    r'상장',
    r'상장 폐지',
    r'폐지 결정',
    r'거래지원 종료',
	# 시장 해설 / 분석 기사 제외
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
    r'\bdata infrastructure\b',
    r'\bcanton network\b',
    r'\bus treasuries\b',
    r'\biBoxx\b',
    r'\bs&p dow jones\b',
    r'미국채',
    r'데이터 인프라',
    r'칸톤네트워크',
    r'금융 데이터',
	r'\bactive users?\b',
    r'\bmarket recovery\b',
    r'\btrading assistant\b',
    r'\bretail users?\b',
    r'\bmonthly close\b',
    r'\bapril fools\b',
    r'\bipo controversy\b',
	r'\btransaction fee\b',
    r'\bfees\b',
    r'\binscription\b',
    r'\binscriptions\b',
    r'\bsoft fork\b',
    r'\bsoftfork\b',
    r'\bblock space\b',
    r'\bblocksize\b',
    r'\bblock size\b',
    r'\bthroughput\b',
    r'트랜잭션 수수료',
    r'인스크립션',
    r'소프트포크',
    r'블록당 트랜잭션',
    r'블록 용량',
	r'\bbollinger\b',
r'\bbollinger bands\b',
r'\bmajor move\b',
r'\btightening\b',
r'\bgolden cross\b',
r'\bburn rate\b',
r'\bnetwork activity\b',

	r'\bliquidation imbalance\b',
r'\bliquidations\b',
r'\bwhales woke up\b',
r'\bwhale activity\b',
r'\bwhat to expect\b',
r'\bnext week\b',
r'\bhigh yield\b',
r'\bpassive income\b',
r'\binvestment guide\b',
r'\bearn eth\b',
r'\bstaking\b',
r'\blending\b',
r'청산 불균형',
r'청산액',
r'고래들 움직임',
r'예상되는 사항',
r'고수익 기회',
r'수익 받는 방법',
r'스테이킹',
r'대출 등으로',

r'\blost\b',
r'\bloss(es)?\b',
r'\bworst quarter\b',
r'\bunderwater\b',
r'\bsell at a loss\b',
r'손실',
r'최악의 분기',
r'\bcanton\b',
r'캔톤',
	
	
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

def is_chart_or_price_article(text: str) -> bool:
    low = (text or "").lower()

    chart_patterns = [
        r'\bprice\b',
        r'가격',
        r'월봉',
        r'monthly candle',
        r'monthly chart',
        r'\bchart\b',
        r'\bcandlestick\b',
        r'\bsupport\b',
        r'\bresistance\b',
        r'\bbreakout\b',
        r'\btarget price\b',
        r'\bforecast\b',
        r'\bprice prediction\b',
        r'\btechnical analysis\b',
        r'기술적 분석',
        r'차트 분석',
        r'지지선',
        r'저항선',
        r'목표가',
        r'반등',
        r'선을\s*유지',
        r'선\s*유지',
        r'깨짐',
        r'뚫음',
        r'뚫림',
        r'유지함',
        r'유지 중',
        r'돌파',
        r'추세',
        r'공포탐욕',
        r'extreme fear',
        r'fear and greed',
        r'bottom signal',
        r'fails to break higher',
        r'price fails to break higher',
        r'green monthly candle',
        r'red monthly streak',
		r'lower highs',
r'price correction',
r'resistance range',
r'resistance level',
r'what s next',
r'what’s next',
r'tumbling',
r'continue to dip',
r'oscillate between',
		
    ]

    return any(re.search(p, low, re.I) for p in chart_patterns)


def is_xrp_narrative_article(text: str) -> bool:
    low = (text or "").lower()

    xrp_terms = [
        'xrp', 'ripple', 'xrpl', 'xrp ledger', 'xrpledger',
        '리플', '엑스알피'
    ]

    narrative_terms = [
        'bank charter', 'occ', 'approval', 'custody', 'payment',
        'institutional', 'adoption', 'integration', 'volume',
        'liquidity', 'settlement', 'infrastructure',
        '은행 인가', '승인', '수탁', '결제', '기관', '도입', '통합', '인프라'
    ]

    has_xrp = any(contains_exact_term(low, t) for t in xrp_terms)
    has_narrative = any(contains_exact_term(low, t) for t in narrative_terms)

    return has_xrp and has_narrative


def is_pure_macro_article(text: str) -> bool:
    low = (text or "").lower()

    macro_terms = [
        'stablecoin', 'regulation', 'bill', 'law', 'policy', 'senate', 'house',
        'fed', 'treasury', 'bank', 'custody', 'occ', 'cftc', 'sec',
        '감시', '감독', '규제', '법안', '정책', '상원', '하원',
        '연준', '재무부', '은행', '수탁', '스테이블코인', 'OCC', 'SEC', 'CFTC'
    ]

    return any(contains_exact_term(low, t) for t in macro_terms)


FINAL_HASHTAGS = ['BTC','비트코인','dooridoori','도리도리','doorinati','도리나티']

INLINE_TAG_WHITELIST = {
    '미국', 'CFTC', 'Polymarket', '폴리마켓', 'Elizabeth Warren', '엘리자베스워런',
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
    'RLUSD', 'FOMC', '헤스터피어스', '시카고상품거래소', '키발리스', '라울팔', '누바', '템포', '머니그램', '미카', '도호쿠은행', 'SBIRemit', '소프트뱅크', '트웬티원캐피털', '화이트비트', '티머시매사드', '무로', '산탄데르',
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
    'RLUSD', 'FOMC', '헤스터피어스', '시카고상품거래소', '키발리스', '라울팔', '누바', '템포', '머니그램', '미카', '도호쿠은행', 'SBIRemit', '소프트뱅크', '트웬티원캐피털', '화이트비트', '티머시매사드', '무로', '산탄데르',

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
'프랭클린템플턴', '토니피코어','WisdomTree', '위즈덤트리', 'CLARITY Act', '클래리티법','Jack Dorsey', '잭도시', 'Block',
'Michael Selig', '마이클셀릭', '마이클 셀릭','마이크로소프트', 'Microsoft','XRPL', 'DEX', '탈중앙거래소', 'DeFi', 'Vet', '사토시쿠사마',
'XRPL', 'DEX', 'Decentralized Exchange', 'Satoshi Kusama',

	'Bitdeer', '비트디어','Blockstream', '블록스트림','IMF', '토비아스아드리안', 'Tobias Adrian', 'RWA', '지니어스법안','Charles Schwab', '찰스슈왑',
'Oracle', '오라클','피터쉬프', 'Peter Schiff','금융당국', '사모대출', '잉글랜드은행', '앤드루베일리',
'한국은행', '보험연수원', '디지털화폐', '디지털통화', '지수보험',
'일본은행', '유가', '국채', '신현송', 'CBDC',
'메타플래닛', '일본 정부', '코인원', '코인원 AML',
'ABA', '예금', '은행예금', '금융위원회',
'모니카롱', 'ODL', 'FedNow', 'Fedwire',
'금융상품거래법', '금융상품', '스테이블코인', '클래리티법안',
'브래드갈링하우스', '리플 CEO', '블랙록 CEO',
'SMQKE', '신탁은행', '마스터계정', '금융감독청',
'주택시장', '제프박', '프로캡',
'업비트', 'USDT', '원화마켓', 'KRW',

	
	
}



MANUAL_TRANSLATIONS = {
    'Polymarket': '폴리마켓',
    '폴리마켓': '폴리마켓',

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
    'FOMC': 'FOMC',
    '헤스터 피어스': '헤스터피어스',
    'Hester Peirce': '헤스터피어스',
    'CME': '시카고상품거래소',
    'CME Group': '시카고상품거래소',
    'Chicago Mercantile Exchange': '시카고상품거래소',
    'Qivalis': '키발리스',
    '키발리스': '키발리스',
    'Raoul Pal': '라울팔',
    '라울 팔': '라울팔',
    '라울팔': '라울팔',
    'NUVA': '누바',
    'Tempo': '템포',
    'MoneyGram': '머니그램',
    'RLUSD': 'RLUSD',
    'MiCA': '미카',
    'MICA': '미카',
    'AllUnity': '올유니티',
    'Kalqix': '칼릭스',
    'KalaiX': '칼릭스',
    'Tohoku Bank': '도호쿠은행',
    'SBI Remit': 'SBIRemit',
    'SoftBank': '소프트뱅크',
    'Twenty One Capital': '트웬티원캐피털',
    'XXI': 'XXI',
    'WhiteBIT': '화이트비트',
    'Timothy Massad': '티머시매사드',
    'Morgan Stanley': '모건스탠리',
    'Truth Social': '트루스소셜',
    'Santiment': '샌티먼트',
    'Muro': '무로',
    'Santander': '산탄데르',


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

	'Jack Dorsey': '잭도시',
    '잭 도시': '잭도시',
    '잭도시': '잭도시',
    'Block': 'Block',

    'Robinhood': '로빈후드',
    '로빈후드': '로빈후드',

    'Tether': '테더',
    '테더': '테더',

    'Ripple': 'XRP',
    '리플': 'XRP',

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
	    'Michael Barr': '마이클바',
    '마이클 바': '마이클바',
    '마이클바': '마이클바',

    'GENIUS': 'GENIUS',
    'Genius Act': '지니어스법',
    '지니어스법': '지니어스법',

    'Australia': '호주',
    'Australian': '호주',
    '호주': '호주',

    'Custodian': '수탁업체',
    'Custodians': '수탁업체',
    '수탁업체': '수탁업체',

    'Hong Kong': '홍콩',
    '홍콩': '홍콩',

    'HKMA': '홍콩금융관리국',
    'Hong Kong Monetary Authority': '홍콩금융관리국',
    '홍콩금융관리국': '홍콩금융관리국',

    'HSBC': 'HSBC',
    'Standard Chartered': '스탠다드차타드',
    '스탠다드차타드': '스탠다드차타드',

	'Michael Selig': '마이클셀릭',
    '마이클 셀릭': '마이클셀릭',
    '마이클셀릭': '마이클셀릭',
	'Paul Grewal': '폴그루월',
'폴 그루월': '폴그루월',
'폴그루월': '폴그루월',
'Grewal': '그루월',
'그루월': '그루월',

'Brad Garlinghouse': '브래드갈링하우스',
'브래드 갈링하우스': '브래드갈링하우스',
'브래드갈링하우스': '브래드갈링하우스',
'CEO': 'CEO',

'Genius Group': '지니어스그룹',
'지니어스그룹': '지니어스그룹',

'Government': '정부',
'정부': '정부',
'KYC': 'KYC',

'FTX': 'FTX',
'Nishad Singh': '니샤드싱',
'니샤드 싱': '니샤드싱',
'니샤드싱': '니샤드싱',

'KBank': '케이뱅크',
'케이뱅크': '케이뱅크',

'eToro': 'eToro',
'Taiwan': '대만',
'대만': '대만',

'Coinone': '코인원',
'코인원': '코인원',

'Bitget': '비트겟',
'비트겟': '비트겟',
'SafePal': '세이프팔',
'세이프팔': '세이프',

'Microsoft': '마이크로소프트',
'마이크로소프트': '마이크로소프트',
	
'David Schwartz': '데이비드슈워츠',
'데이비드슈워츠': '데이비드슈워츠',
	
'Ripple': 'XRP',
'리플': 'XRP',
	'XRPL': 'XRPL',
'DEX': 'DEX',
'Decentralized Exchange': '탈중앙거래소',
'탈중앙거래소': '탈중앙거래소',
'Satoshi Kusama': '사토시쿠사마',
    'XRP Ledger': 'XRPLedger',
    'xrp ledger': 'XRPLedger',
    'RLUSD': 'RLUSD',
    'FOMC': 'FOMC',
    'Hester Peirce': '헤스터피어스',
    'CME Group': '시카고상품거래소(CME)',
    'Chicago Mercantile Exchange': '시카고상품거래소(CME)',
    'Qivalis': '키발리스',
    'Raoul Pal': '라울팔',
    'NUVA': '누바',
    'Tempo': '템포',
    'MoneyGram': '머니그램',
    'MiCA': '미카',
    'MICA': '미카',
    'AllUnity': '올유니티',
    'Kalqix': '칼릭스',
    'KalaiX': '칼릭스',
    'Truth Social': '트루스소셜',
    'Tohoku Bank': '도호쿠은행',
    'SBI Remit': 'SBIRemit',
    'SoftBank': '소프트뱅크',
    'Twenty One Capital': '트웬티원캐피털',
    'Timothy Massad': '티머시매사드',
    'Santiment': '샌티먼트',
    'Santander': '산탄데르',

'사토시 쿠사마': '사토시쿠사마',
'사토시쿠사마': '사토시쿠사마',
'Vet': 'Vet',
'VET': 'Vet',
	'Bitdeer': '비트디어',
'비트디어': '비트디어',

	'Blockstream': '블록스트림',
'블록스트림': '블록스트림',

	'IMF': 'IMF',
'Tobias Adrian': '토비아스아드리안',
'토비아스 아드리안': '토비아스아드리안',
'토비아스아드리안': '토비아스아드리안',
'RWA': 'RWA',
'지니어스법안': '지니어스법안',
	'Charles Schwab': '찰스슈왑',
'찰스 슈왑': '찰스슈왑',
'찰스슈왑': '찰스슈왑',
'Oracle': '오라클',
'오라클': '오라클',

	'Peter Schiff': '피터쉬프',
'피터 쉬프': '피터쉬프',
'피터쉬프': '피터쉬프',
	'Financial Supervisory Service': '금융당국',
'금융당국': '금융당국',

'Private Credit': '사모대출',
'private credit': '사모대출',
'사모대출': '사모대출',

'Bank of England': '잉글랜드은행',
'잉글랜드은행': '잉글랜드은행',

'Andrew Bailey': '앤드루베일리',
'앤드루 베일리': '앤드루베일리',
'앤드루베일리': '앤드루베일리',

'Bank of Korea': '한국은행',
'한국은행': '한국은행',

'Korea Insurance Development Institute': '보험연수원',
'보험연수원': '보험연수원',

'Digital Currency': '디지털통화',
'디지털통화': '디지털통화',
'Digital Assets': '디지털자산',
'디지털자산': '디지털자산',
'Digital Finance': '디지털화폐',
'디지털화폐': '디지털화폐',

'Bank of Japan': '일본은행',
'일본은행': '일본은행',

'Hyun Song Shin': '신현송',
'신현송': '신현송',

'CBDC': 'CBDC',

'ABA': 'ABA',

'Monica Long': '모니카롱',
'모니카롱': '모니카롱',

'ODL': 'ODL',
'FedNow': 'FedNow',
'Fedwire': 'Fedwire',

'SMQKE': 'SMQKE',
'Master Account': '마스터계정',
'마스터계정': '마스터계정',
'Trust Bank': '신탁은행',
'신탁은행': '신탁은행',

'Jeff Park': '제프박',
'제프 박': '제프박',
'제프박': '제프박',

'ProCap': '프로캡',
'프로캡': '프로캡',

'Upbit': '업비트',
'업비트': '업비트',

'Coinone': '코인원',
'코인원': '코인원',
}


COUNTRY_TAG_MAP = {
    'US': ['미국', 'United States', 'US', 'U.S.', 'America'],
    'Korea': ['한국', '대한민국', 'South Korea', 'Korea'],
    'Japan': ['일본', 'Japan'],
    'China': ['중국', 'China'],
    'Taiwan': ['대만', 'Taiwan'],
    'HongKong': ['홍콩', 'Hong Kong'],
    'Australia': ['호주', 'Australia', 'Australian'],
    'Singapore': ['싱가포르', 'Singapore'],
    'Canada': ['캐나다', 'Canada'],
    'UK': ['영국', 'United Kingdom', 'UK', 'Britain'],
    'Germany': ['독일', 'Germany'],
    'France': ['프랑스', 'France'],
    'Brazil': ['브라질', 'Brazil'],
    'India': ['인도', 'India'],
    'UAE': ['아랍에미리트', 'UAE', 'United Arab Emirates'],
    'SaudiArabia': ['사우디아라비아', 'Saudi Arabia'],
    'Qatar': ['카타르', 'Qatar'],
    'Israel': ['이스라엘', 'Israel'],
    'Iran': ['이란', 'Iran'],
    'Turkey': ['튀르키예', '터키', 'Turkey', 'Türkiye'],
    'Russia': ['러시아', 'Russia'],
    'Ukraine': ['우크라이나', 'Ukraine'],
    'SouthAfrica': ['남아프리카공화국', '남아공', 'South Africa'],
    'Nigeria': ['나이지리아', 'Nigeria'],
    'Kazakhstan': ['카자흐스탄', 'Kazakhstan'],
	
}
COUNTRY_FINAL_TAGS = set()
COUNTRY_INLINE_ALIASES = set()
COUNTRY_TRANSLATIONS = {}

for final_tag, aliases in COUNTRY_TAG_MAP.items():
    ko = aliases[0]

    COUNTRY_FINAL_TAGS.add(f'#{final_tag}')
    COUNTRY_INLINE_ALIASES.update(aliases)

    for alias in aliases:
        COUNTRY_TRANSLATIONS[alias] = ko

for alias in COUNTRY_INLINE_ALIASES:
    if alias not in KOREAN_TAG_KEYWORDS:
        KOREAN_TAG_KEYWORDS.append(alias)

INLINE_TAG_WHITELIST.update(COUNTRY_INLINE_ALIASES)
MANUAL_TRANSLATIONS.update(COUNTRY_TRANSLATIONS)

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
MAX_ITEMS_PER_FEED = 6
SUMMARY_SENTENCES = 3
OPENAI_INPUT_COST_PER_1M = 0.75
OPENAI_OUTPUT_COST_PER_1M = 4.50
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


def log_openai_cost(title: str, prompt: str, output: str) -> None:
    if not SHOW_COST_LOG:
        return

    input_tokens = estimate_tokens_from_text(prompt)
    output_tokens = estimate_tokens_from_text(output)

    input_cost = (input_tokens / 1_000_000) * OPENAI_INPUT_COST_PER_1M
    output_cost = (output_tokens / 1_000_000) * OPENAI_OUTPUT_COST_PER_1M
    total_cost = input_cost + output_cost

    log(
        f"[OpenAI 비용] {title[:60]} | "
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

def update_posted(title: str, posted: dict, url: str = "", signature: str = "", canonical_key: str = ""):
    posted[story_hash(title)] = {
        'title': title,
        'url': normalize_url(url),
        'signature': signature,
        'canonical_key': canonical_key,
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

            # 이미지 보강
            article_desc, article_img = ('', '')

            need_meta_fetch = (
                (not image_url)
                or (not str(image_url).startswith('http'))
                or ('coinedition.com' in link)
            )

            if need_meta_fetch:
                article_desc, article_img = fetch_article_meta(link)

            if article_img and str(article_img).startswith('http'):
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

def is_corporate_treasury_sale_article(text: str) -> bool:
    low = (text or "").lower()

    sale_terms = [
        'liquidates entire bitcoin stash',
        'bitcoin stash',
        'debt repayment',
        'repay debt',
        'sell bitcoin holdings',
        'liquidates holdings',
        '전량 매각',
        '비트코인 전량 매각',
        '부채 상환',
    ]

    company_terms = [
        'genius group', 'empery digital', 'treasury company',
        '지니어스그룹', '기업 재무', '재무 기업'
    ]

    return any(t in low for t in sale_terms) and any(t in low for t in company_terms)


def is_wallet_balance_metric_article(text: str) -> bool:
    low = (text or "").lower()

    wallet_terms = [
        'spendable wallets',
        'wallet balance',
        'held in wallets',
        'average holdings',
        'bag smashes',
        '보관 중임',
        '보유량',
        '평균 보유량',
        '지갑에 보관',
        '가용 지갑',
    ]

    xrp_terms = ['xrp', 'ripple', '리플']
    allow_terms = ['whale', '고래', 'santiment', '샌티먼트']
    if any(t in low for t in allow_terms):
        return False

    return any(t in low for t in wallet_terms) and any(t in low for t in xrp_terms)


def is_conference_opinion_article(text: str) -> bool:
    low = (text or "").lower()

    event_terms = [
        'conference', 'summit', 'forum', 'event', 'panel', 'speaker',
        'speaks on', 'spoke at', 'hosted by', 'co-hosted', 'presented by',
        'scheduled for', 'will be held', 'to be held', 'registration',
        '컨퍼런스', '서밋', '포럼', '행사', '이벤트', '패널', '연사',
        '개최', '개최됨', '열림', '주최', '공동 주최', '참가', '참여', '논의'
    ]

    promo_terms = [
        'eastpoint', 'hashed', 'bloomingbit', 'korea economic daily',
        'ticket', 'registration', 'attend', 'networking',
        'seoul 2026', 'september 28'
    ]

    hard_news_terms = [
        'approval', 'approved', 'license', 'licensed', 'bill', 'law',
        'launch', 'launched', 'lawsuit', 'settlement', 'etf',
        '승인', '인가', '법안', '출시', '소송', '합의'
    ]

    has_event = any(t in low for t in event_terms)
    has_promo = any(t in low for t in promo_terms)
    has_hard_news = any(t in low for t in hard_news_terms)

    return (has_event and not has_hard_news) or (has_promo and has_event) or ('challenge' in low) or ('campaign' in low)

def is_security_incident_article(text: str) -> bool:
    low = (text or "").lower()

    incident_terms = [
        'exploit', 'security incident', 'durable nonce',
        'unauthorized trade', 'unauthorized transfer',
        '익스플로잇', '보안 사고', '무단 거래 승인'
    ]

    return any(t in low for t in incident_terms)

def is_payment_adoption_article(text: str) -> bool:
    low = (text or "").lower()

    org_terms = [
        'bitget', 'etoro', 'kbank', '케이뱅크', '업비트',
        'bitlicense', 'card', 'payment', 'spending',
        'cross border', 'crossborder', '해외송금', '결제', '카드', '라이선스'
    ]

    positive_terms = [
        'launch', 'launched', 'wins', 'secured', 'obtained', 'expands',
        '출시', '획득', '확대', '도입', '활용'
    ]

    return any(t in low for t in org_terms) and any(t in low for t in positive_terms)


def is_exchange_mna_article(text: str) -> bool:
    low = (text or "").lower()

    exchange_terms = [
        'coinone', 'korbit', 'exchange stake', 'stake acquisition',
        '지분 인수', '인수 검토', '거래소 지분', '코인원', '코빗'
    ]

    finance_terms = [
        'korea investment', 'mirae asset', '한국투자증권', '미래에셋'
    ]

    return any(t in low for t in exchange_terms) and any(t in low for t in finance_terms)



ENTITY_TRANSLATION_MAP = dict(MANUAL_TRANSLATIONS)

STRICT_ALLOWED_ASSETS = [
    'bitcoin', 'btc', 'ethereum', 'eth', 'xrp', 'ripple', 'xlm', 'stellar',
    'ada', 'cardano', 'trx', 'tron', 'bnb', 'bch', 'bitcoin cash',
    'shib', 'shiba inu', 'etc', 'flr', 'athena', 'ena', 'usdc', 'usdt',
    '비트코인', '이더리움', '리플', '스텔라', '에이다', '트론',
    '바이낸스코인', '비트코인캐시', '시바이누', '플레어', '에테나',
]

STRICT_CRYPTO_CONTEXT = [
    '암호화폐', '가상자산', '디지털자산', '블록체인',
    'crypto', 'cryptocurrency', 'digital asset', 'digital assets', 'blockchain',
    'etf', 'stablecoin', 'custody', 'tokenization', 'wallet', 'exchange',
    '수탁', '토큰화', '지갑', '거래소', '스테이블코인',
]

STRICT_POLICY_CONTEXT = [
    'sec', 'cftc', 'occ', 'fed', 'treasury', 'senate', 'house', 'committee',
    'regulation', 'regulated', 'bill', 'law', 'act', 'policy', 'approval',
    '승인', '규제', '법안', '정책', '상원', '하원', '위원회', '연준', '재무부',
]

TAG_PARTICLES = [
    '으로', '에서', '에게', '까지', '부터',
    '은', '는', '이', '가', '을', '를', '의', '와', '과', '로', '도', '만',
]

def _contains_any_term(text: str, terms: list[str]) -> bool:
    if not text or not terms:
        return False
    low = normalize_for_duplicate(str(text))
    for term in terms:
        if not term:
            continue
        t = normalize_for_duplicate(str(term))
        if not t:
            continue
        if contains_exact_term(low, t):
            return True
    return False

def _entity_korean_name_strict(entity: str, context_text: str = "") -> str:
    if not entity:
        return ""
    ent = str(entity).strip()
    if not ent:
        return ""

    if ent in {"Gold", "금"} and not has_precious_metal_context(context_text, "gold"):
        return ""
    if ent in {"Silver", "은"} and not has_precious_metal_context(context_text, "silver"):
        return ""

    if ent in ENTITY_TRANSLATION_MAP:
        mapped = ENTITY_TRANSLATION_MAP[ent]
    else:
        mapped = entity_korean_name(ent)

    mapped = str(mapped).strip().replace(" ", "")
    if mapped == "금" and not has_precious_metal_context(context_text, "gold"):
        return ""
    if mapped == "은" and not has_precious_metal_context(context_text, "silver"):
        return ""
    return mapped

def _is_inline_tag_candidate(tag_name: str, text: str = "") -> bool:
    if not tag_name:
        return False
    if tag_name in ALWAYS_INLINE_TAGS or tag_name in INLINE_TAG_WHITELIST:
        return True
    return len(tag_name) >= 2 and tag_name in (text or "")


def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
    raw_text = (story.get('title', '') + ' ' + story.get('desc', '')).strip()
    raw_lower = raw_text.lower()
    url = (story.get('url', '') or '').lower()

    portfolio_context_terms = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'xrp', 'ripple', 'xlm', 'stellar',
        'ada', 'cardano', 'trx', 'tron', 'bnb', 'bch', 'bitcoin cash',
        'shib', 'shiba inu', 'etc', 'flr', 'athena', 'ena', 'usdc', 'usdt',
        '비트코인', '이더리움', '리플', '스텔라', '에이다', '트론',
        '바이낸스코인', '비트코인캐시', '시바이누', '플레어', '에테나'
    ]

    ai_company_terms = [
        'openai', 'anthropic', 'google', 'block', 'ai',
        'middle management', 'organization design', '업무 환경', '조직', 'ai'
    ]

    if 'tokenpost.kr/news/tech/' in url:
        return False

    hard_irrelevant_terms = ['moew', 'realgo', 'fast or go home', 'allunity', 'kalqix', 'kalaix', 'challenge', 'mainnet launch', 'clob dex', 'agent', 'airdrop', 'launch campaign', 'wallet campaign']
    if any(t in raw_lower for t in hard_irrelevant_terms):
            print(f"[홍보/비관련 제외] {story.get('title', '')}")
            return False

       # 1. 기본 네거티브 차단
    for neg in NEGATIVE_KEYWORDS:
        if neg.lower() in raw_lower:
            print(f"[NEGATIVE 제외] {story.get('title', '')} / {neg}")
            return False

    if contains_bad_signal(raw_text):
        print(f"[부정시그널 제외] {story.get('title', '')}")
        return False

    if is_corporate_treasury_sale_article(raw_text):
        print(f"[기업재무매각 제외] {story.get('title', '')}")
        return False

    if is_wallet_balance_metric_article(raw_text):
        print(f"[지갑보유량 제외] {story.get('title', '')}")
        return False

    if is_conference_opinion_article(raw_text):
        print(f"[행사발언 제외] {story.get('title', '')}")
        return False

    if is_security_incident_article(raw_text):
        print(f"[보안사고 제외] {story.get('title', '')}")
        return False

    # 2. 차트/가격형 기사 차단
    if is_chart_or_price_article(raw_text):
        print(f"[차트/가격형 제외] {story.get('title', '')}")
        return False

    # 3. 포트폴리오 외 코인 차단
    allowed_coin_found = any(contains_exact_term(raw_text, c) for c in coins)
    if not allowed_coin_found and contains_non_portfolio_asset(raw_text):
        print(f"[포폴외코인 제외] {story.get('title', '')}")
        return False

    # 4. 일반 주식 문맥 차단
    if contains_stock_context(raw_text) and not allowed_coin_found:
        print(f"[주식기사 제외] {story.get('title', '')}")
        return False

    # 5. 나머지 BAD_TOPIC 차단
    if contains_bad_topic(raw_text):
        print(f"[주제제외] {story.get('title', '')}")
        return False

    # 6. 허용 코인 직접 등장 기사
    if allowed_coin_found:
        print(f"[허용코인 통과] {story.get('title', '')}")
        return True

    # 7. 순수 거시/정책 기사 허용
    if is_pure_macro_article(raw_text):
        print(f"[거시/정책 통과] {story.get('title', '')}")
        return True

    # 8. XRP 서사형 기사 허용
    if is_xrp_narrative_article(raw_text):
        print(f"[XRP서사 통과] {story.get('title', '')}")
        return True

    # 9. AI/기업 기사 허용
    if any(contains_exact_term(raw_text, t) for t in ai_company_terms):
        print(f"[AI/기업기사 통과] {story.get('title', '')}")
        return True

    if is_payment_adoption_article(raw_text):
        print(f"[결제/채택 통과] {story.get('title', '')}")
        return True

    if is_exchange_mna_article(raw_text):
        print(f"[거래소M&A 통과] {story.get('title', '')}")
        return True

    print(f"[필터미통과] {story.get('title', '')}")
    return False

def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
    if not canonical_key:
        return False

    current = {x.strip() for x in canonical_key.split('|') if x.strip()}

    for old_key in seen_keys:
        old = {x.strip() for x in old_key.split('|') if x.strip()}
        shared = current & old

        if len(shared) >= 4:
            log(f"[정규토픽중복 제외] shared={shared}")
            return True

        if len(current) >= 4 and len(old) >= 4 and len(shared) >= min(len(current), len(old)) - 1:
            log(f"[정규토픽유사 제외] shared={shared}")
            return True

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

def extract_entities_from_summary(summary: str, max_tags: int = 8) -> list[str]:
    text = summary or ""
    entities = []

    for key in sorted(MANUAL_TRANSLATIONS.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(key) + r'\b', text, re.I):
            entities.append(key)

    for kw in KOREAN_TAG_KEYWORDS:
        if kw in {'금', '은'}:
            continue
        if re.search(r'\b' + re.escape(kw) + r'\b', text, re.I):
            entities.append(kw)

    for coin in PORTFOLIO_COINS:
        if re.search(r'\b' + re.escape(coin) + r'\b', text, re.I):
            entities.append(coin)

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
        'XRP': 'XRP',
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
    text = text.replace('#마이클#세일러', '#마이클세일러')
    text = text.replace('#브래드#갈링하우스', '#브래드갈링하우스')
    text = text.replace('#토비아스#아드리안', '#토비아스아드리안')
    text = text.replace('#R L U S D', '#RLUSD')
    text = text.replace('RL#미국D', '#RLUSD')
    text = text.replace('#엑스알피', '#XRP')
    text = text.replace('#리플 ', '#XRP ')
    text = text.replace('#리플\n', '#XRP\n')
    text = text.replace('#F O M C', '#FOMC')
    text = text.replace('#헤스터 피어스', '#헤스터피어스')
    text = text.replace('#리플', '#XRP')
    text = text.replace('#X R P', '#XRP')
    text = text.replace('#F O M C', '#FOMC')
    text = text.replace('#시카고상품거래소', '#시카고상품거래소(CME)')
    text = text.replace('#Qivalis', '#키발리스')
    text = text.replace('#Nuva', '#누바')
    text = text.replace('#Tempo', '#템포')
    text = text.replace('#MoneyGram', '#머니그램')
    text = text.replace('#Muro', '#무로')
    text = text.replace('#Santander', '#산탄데르')

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
	'클레러티법': '클래리티법',
    '클레리티법': '클래리티법',
    '클레러티': '클래리티',
    '클레리티': '클래리티',
		'Shiba Inu': '시바이누',
'shiba inu': '시바이누',
'시바견': '시바이누',
		'시토시': '사토시',
'사토시 쿠사마': '사토시쿠사마',
'Satoshi Kusama': '사토시쿠사마',
    'XRP Ledger': 'XRPLedger',
    'xrp ledger': 'XRPLedger',
    'RLUSD': 'RLUSD',
    'FOMC': 'FOMC',
    'Hester Peirce': '헤스터피어스',
    'CME Group': '시카고상품거래소(CME)',
    'Chicago Mercantile Exchange': '시카고상품거래소(CME)',
    'Qivalis': '키발리스',
    'Raoul Pal': '라울팔',
    'NUVA': '누바',
    'Tempo': '템포',
    'MoneyGram': '머니그램',
    'MiCA': '미카',
    'MICA': '미카',
    'AllUnity': '올유니티',
    'Kalqix': '칼릭스',
    'KalaiX': '칼릭스',
    'Truth Social': '트루스소셜',
    'Tohoku Bank': '도호쿠은행',
    'SBI Remit': 'SBIRemit',
    'SoftBank': '소프트뱅크',
    'Twenty One Capital': '트웬티원캐피털',
    'Timothy Massad': '티머시매사드',
    'Santiment': '샌티먼트',
    'Santander': '산탄데르',

    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r'\[\.\.\.\]|\.\.\.|…', ' ', text)
    text = re.sub(r'\s*:\s*\[\s*\]', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()

    return text

def filter_final_tags(tags: list[str]) -> list[str]:
    allowed_exact = {
        '#BTC','#ETH','#XRP','#XLM','#ADA','#TRX','#BNB','#BCH','#SHIB','#ETC','#FLR','#ATHENA','#ETNA','#USDC','#USDT',
        '#Ripple','#Ethereum','#Bitcoin','#Stablecoin','#DeFi','#NFT','#Web3',
        '#ETF','#SEC','#CFTC','#OCC','#IPO','#CTO','#AI',
        '#JPMorgan','#MorganStanley','#GoldmanSachs','#BlackRock','#Coinbase','#Binance','#Upbit','#Bithumb',
        '#OpenAI','#Anthropic','#Google','#Apple','#PayPal','#Stripe','#Microsoft',
        '#DavidSchwartz','#BradGarlinghouse','#MonicaLong','#MichaelSaylor','#JeromePowell',
        '#TomLee','#JackDorsey','#PaulGrewal','#MichaelBarr','#MichaelSelig',
        '#Tether','#Circle','#MoneyGram','#Mastercard','#Visa',
        '#Metaplanet','#Strategy','#Robinhood','#Kraken','#WellsFargo',
        '#FranklinTempleton','#TonyPecore','#WisdomTree',
        '#GeniusGroup','#GENIUS','#CLARITY','#CLARITYAct',
        '#KBank','#Coinone','#Bitget','#SafePal','#eToro','#HKMA','#HSBC','#StandardChartered',
        '#US','#Korea','#Japan','#China','#Taiwan','#HongKong','#Australia','#Brazil','#India','#Iran','#Israel','#Qatar',
        '#XRPLedger','#BitMine','#BCH','#TRON','#TRX','#XAUT','#SHIB','#XRP','#XLM','#XRPL', '#DEX', '#DeFi','#Bitdeer','#Blockstream',
        '#FOMC','#RLUSD','#시카고상품거래소','#키발리스','#라울팔','#누바','#템포','#머니그램','#미카','#도호쿠은행','#SBIRemit','#소프트뱅크','#트웬티원캐피털','#화이트비트','#티머시매사드','#무로','#산탄데르',
		'#IMF', '#TobiasAdrian', '#RWA', '#GENIUSAct','#Oracle','#Coinone', '#Korea', '#Japan', '#BankOfJapan', '#BankOfKorea',
'#IMF', '#ABA', '#RWA', '#CBDC',
'#MonicaLong', '#ODL', '#FedNow', '#Fedwire',
'#AndrewBailey', '#HyunSongShin',
'#Metaplanet', '#Upbit',
'#BradGarlinghouse', '#CLARITY', '#CLARITYAct',
'#PeterSchiff', '#Gold', '#Silver',
'#CharlesSchwab', '#Oracle',
'#JeffPark', '#ProCap',
    }

    allowed_exact |= COUNTRY_FINAL_TAGS

    blocked_contains = [
        'Highlights','Surprise','Underpriced','Needs','Run','Hitting','Fall',
        'Mean','Errors','Peak','Insufficient','Deals','Game','Escrow','Top',
        'Early','About','What','Will','Passes','Says','This','Hard',
        'Level','Trigger','Million','Long','Squeeze','Could'
    ]

    cleaned = []
    for tag in tags:
        tag = tag.replace('.', '')

        # footer에는 한글 해시태그 금지
        if re.search(r'#[가-힣]+', tag):
            continue

        if any(b.lower() in tag.lower() for b in blocked_contains):
            continue

        if tag in allowed_exact:
            cleaned.append(tag)

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

def get_best_source_text(story: dict) -> str:
    article_text = fetch_article_text(story.get('url', ''))
    desc = (story.get('desc') or '').strip()
    title = (story.get('title') or '').strip()

    if article_text and len(article_text) >= 180:
        return article_text
    if desc and len(desc) >= 80:
        return desc
    return title


def rewrite_summary_with_gemini(title: str, article_text: str, fallback_text: str = "") -> str:
    source_text = (article_text or "").strip()
    if not source_text:
        source_text = (fallback_text or "").strip()
    if not source_text:
        source_text = title.strip()

    if not openai_client:
        return ""

    try:
        prompt = f"""
너는 텔레그램 암호화폐 뉴스 채널 편집자다.

아래 기사 내용을 보고 한국어로 자연스럽게 2~3문장으로 다시 써라.

규칙:
- 텔레그램 업로드용 짧은 문장으로 작성
- 첫 문장부터 핵심 키워드를 강하게 시작(느낌표 물음표는 사용금지)
- 해시태그는 마지막 footer에서만 사용됨
- 사람 이름, 기관명, 코인명도 일반 텍스트로 자연스럽게 작성
- 해시태그 사용하면 띄어쓰기 필수
- 한국어 띄어쓰기를 자연스럽게 유지
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
- 롱/숏/청산/시장심리/챌린지/광고성 캠페인/에어드롭/메인넷 출시 홍보처럼 보이면 빈 문자열만 반환할 것
- 인물명, 기관명, 국가명, 법안명은 기사에 있으면 요약문 본문에 가능한 한 직접 1회 포함할 것
- 예: Michael Barr, GENIUS Act, Australia, Hong Kong, HKMA, HSBC, Standard Chartered

제목:
{title}

본문:
{source_text}
""".strip()

        response = openai_client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
        )

        text = (response.output_text or "").strip()
        text = cleanup_text(text)
        text = fix_translation_terms(text)
        text = fix_truncated_phrases(text)
        text = normalize_style(text)
        text = cleanup_text(text)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()

        log_openai_cost(title, prompt, text)
        return text

    except Exception as e:
        log(f"OpenAI 요약 실패: {e}")
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
    text = text.replace('ripple', 'xrp')
    text = text.replace('cme group', 'cme')
    text = text.replace('chicago mercantile exchange', 'cme')
    text = text.replace('hester peirce', '헤스터피어스')
    text = text.replace('qivalis', '키발리스')
    text = text.replace('nuva', '누바')
    text = text.replace('tempo', '템포')
    text = text.replace('moneygram', '머니그램')
    text = text.replace('raoul pal', '라울팔')
    text = text.replace('muro', '무로')
    text = text.replace('santander', '산탄데르')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def build_canonical_topic_key(story: dict) -> str:
    text = normalize_for_duplicate(f"{story.get('title', '')} {story.get('desc', '')}")
    parts = []

    # 지역 / 국가
    geo_map = {
        '미국': ['united states', 'us', 'u s', 'america', '미국'],
        '호주': ['australia', 'australian', '호주'],
        '홍콩': ['hong kong', '홍콩'],
        '이란': ['iran', '이란'],
        '일본': ['japan', '일본'],
        '한국': ['korea', 'south korea', '한국'],
        '중국': ['china', '중국'],
        '유럽': ['eu', 'europe', 'european union', '유럽'],
        '영국': ['uk', 'united kingdom', 'britain', '영국'],
        '독일': ['germany', '독일'],
        '이탈리아': ['italy', '이탈리아'],
    }

    for key, terms in geo_map.items():
        if any(contains_exact_term(text, t) for t in terms):
            parts.append(f'geo_{key}')

    # 자산 / 핵심 주제
    topic_map = {
        '비트코인': ['bitcoin', 'btc', '비트코인'],
        '이더리움': ['ethereum', 'eth', '이더리움'],
        '리플': ['xrp', 'ripple', 'xrpl', 'xrp ledger', '리플'],
        '스테이블코인': ['stablecoin', '스테이블코인'],
        'etf': ['etf'],
        '라이선스': ['license', 'licensing', 'licensed', '라이선스'],
        '법안': ['bill', 'law', 'act', '법안'],
        '규제': ['regulation', 'regulatory', 'regulated', '규제'],
        '연준': ['fed', 'federal reserve', '연준'],
        '청문회': ['hearing', '청문회'],
        '지명': ['nominate', 'nominated', 'appointment', '지명'],
        '휴전': ['ceasefire', '휴전'],
        '철수': ['withdraw', 'withdrawal', '철수'],
        'ai': ['ai', 'artificial intelligence'],
		'예측시장': ['prediction market', 'prediction markets', '예측시장'],
        '클래리티법': ['clarity act', 'clarity', '클래리티법', '클래리티'],
        '감독': ['oversight', 'oversight authority', '감독'],
		'지니어스법': ['genius act', 'genius', '지니어스 법안', '지니어스법', '지니어스'],
'재무부': ['treasury', 'department of the treasury', '재무부'],
'의견수렴': ['public comment', 'seek comment', 'request for comment', '의견 수렴', '의견을 구함'],
'주정부규제': ['state level', 'state regulation', 'state oversight', '주 차원', '주정부 감독', '주정부 규제'],
'발행사': ['issuer', 'issuers', '발행사', '발행업체'],'내부자거래': ['insider trading', '내부자 거래'],
'규칙안': ['rules', 'rulemaking', '규칙안', '규칙'],
'기관진출': ['institutional entry', 'institutional access', '시장 진출', '기관 진출'],
		'시장구조법안': ['market structure bill', 'market structure', '시장 구조 법안', '시장구조법안'],
'스테이블코인수익': ['stablecoin yield', 'yield compromise', '스테이블코인 수익', '수익률 수정안'],
		        '스트래티지매수': ['strategy', 'strc', '스트래티지', '비트코인 매입', '비트코인 매수'],
        'cbdc예금토큰': ['cbdc', 'deposit token', '예금 토큰', '예금토큰'],
        '오픈ai이동': ['openai', 'emea', '정책 총괄', 'policy lead'],
        '암호화폐감독': ['crypto oversight', 'crypto supervision', '암호화폐 감독', '감독권'],
        '회로차단기': ['circuit breaker', '회로 차단기', '서킷 브레이커'],
        '가짜지갑사기': ['fake wallet', 'seed phrase', '가짜 지갑', '시드 구문'],
		        '부산은행토스': ['부산은행', 'bnk', '토스', 'toss'],
        '비트마인가': ['bitmine', '톰리', 'tom lee', 'ethereum'],
        'cftc전의장': ['cftc', 'christopher giancarlo', '크리스지안카를로'],
        '가수지갑사기': ['glove', 'g love', 'fake wallet', 'seed phrase', '가짜 지갑'],
        '크라켄유출거부': ['kraken', 'data leak', 'ransom', '유출', '몸값'],
		
    }

    for key, terms in topic_map.items():
        if any(contains_exact_term(text, t) for t in terms):
            parts.append(f'topic_{key}')

    # 기관 / 인물
    entity_map = {
        'hkma': ['hkma', 'hong kong monetary authority', '홍콩금융관리국'],
        'asic': ['asic'],
        'sec': ['sec'],
        'cftc': ['cftc'],
        'occ': ['occ'],
        '트럼프': ['donald trump', 'trump', '트럼프'],
        '케빈워시': ['kevin warsh', '케빈워시'],
        '마이클바': ['michael barr', '마이클바'],
        '잭도시': ['jack dorsey', '잭도시'],
        'hsbc': ['hsbc'],
        '스탠다드차타드': ['standard chartered', '스탠다드차타드'],
        'block': ['block'],
        '마이클셀릭': ['michael selig', '마이클셀릭', '마이클 셀릭'],
		'재무부': ['treasury', 'department of the treasury', '재무부'],
'지니어스그룹': ['genius group', '지니어스그룹'],
'empery': ['empery digital', 'empery'],'jpmorgan': ['jpmorgan', 'jp morgan', '제이피모건'],
'goldmansachs': ['goldman sachs', '골드만삭스'],
'paradigm': ['paradigm'],
'제이미다이먼': ['jamie dimon', '제이미다이먼', '제이미 다이먼'],
		        'strategy': ['strategy', 'strc', '스트래티지', 'michael saylor', '마이클세일러'],
        'bok': ['bank of korea', '한국은행', '신현송', 'hyun song shin'],
        'coinbase': ['coinbase', '코인베이스', 'tom duff gordon', '톰더프고든'],
        'openai': ['openai'],
        'ecb': ['ecb'],
        'esma': ['esma'],
        'bithumb': ['bithumb', '빗썸'],
        'kraken': ['kraken', '크라켄'],
		        'bnk': ['bnk', '부산은행'],
        'toss': ['toss', '토스'],
        'bitmine': ['bitmine', '비트마인', 'tom lee', '톰리'],
        'giancarlo': ['christopher giancarlo', '크리스지안카를로', 'cftc'],
        'glove': ['g love', 'glove', '싱어송라이터', '가수'],
    }

    for key, terms in entity_map.items():
        if any(contains_exact_term(text, t) for t in terms):
            parts.append(f'entity_{key}')

    # 액션
    action_map = {
        '통과': ['pass', 'passed', 'passes', 'approved', 'approval', '통과', '승인'],
        '지연': ['delay', 'delayed', 'missed target', 'behind schedule', '지연'],
        '출시': ['launch', 'launched', '출시'],
        '발언': ['said', 'says', 'statement', '밝힘', '전함', '발언'],
        '감축': ['job cuts', 'layoff', 'layoffs', '감축', '해고'],
		'강조': ['emphasized','warn', 'warning', 'emphasize', 'stressed', '강조', '경고'],
        '준비': ['prepared', 'ready', '준비'],
		        '이동': ['move', 'moved', 'joins', 'joined', 'appointed', '이동', '합류'],
        '매수': ['buy', 'bought', 'acquire', 'acquired', '매수', '매입'],
        '지지': ['support', 'supports', '지지'],
        '촉구': ['urge', 'urges', 'calls for', '촉구'],
    }

    for key, terms in action_map.items():
        if any(contains_exact_term(text, t) for t in terms):
            parts.append(f'action_{key}')

    # 너무 짧으면 중복키로 쓰지 않음
    parts = sorted(set(parts))
    if len(parts) < 3:
        return ""

    return " | ".join(parts)

def build_story_signature(story: dict) -> str:
    raw = f"{story.get('title', '')} {story.get('desc', '')}"
    text = normalize_for_duplicate(raw)

    tags = set()

    # 자산
    asset_map = {
        'btc': 'asset_btc',
        'bitcoin': 'asset_btc',
        'eth': 'asset_eth',
        'ethereum': 'asset_eth',
        'xrp': 'asset_xrp',
        'ripple': 'asset_xrp',
        'xrpl': 'asset_xrpl',
        'xrp ledger': 'asset_xrpl',
        'usdc': 'asset_usdc',
        'usdt': 'asset_usdt',
        'bch': 'asset_bch',
        'bitcoin cash': 'asset_bch',
        'shib': 'asset_shib',
        'shiba inu': 'asset_shib',

    }

    for key, value in asset_map.items():
        if key in text:
            tags.add(value)

    # 기관/회사
    org_map = {
        'occ': 'org_occ',
        'fed': 'org_fed',
        'federal reserve': 'org_fed',
        'treasury': 'org_treasury',
        'sec': 'org_sec',
        'cftc': 'org_cftc',
        'ripple': 'org_ripple',
        'bitget': 'org_bitget',
        'google': 'org_google',
        'openai': 'org_openai',
        'anthropic': 'org_anthropic',
        'block': 'org_block',
        'coinbase': 'org_coinbase',
		'treasury': 'org_treasury',
        'genius group': 'org_geniusgroup',
        'empery digital': 'org_empery',
        'fomc': 'org_fomc',
        'cme': 'org_cme',
        'qivalis': 'org_qivalis',
        'tempo': 'org_tempo',
        'moneygram': 'org_moneygram',
        'allunity': 'org_allunity',
        'kalqix': 'org_kalqix',
        'truth social': 'org_truthsocial',
        'tohoku bank': 'org_tohokubank',
        'sbi remit': 'org_sbiremit',
        'softbank': 'org_softbank',
        'whitebit': 'org_whitebit',
        'morgan stanley': 'org_morganstanley',
        'santiment': 'org_santiment',
        'santander': 'org_santander',
        'nuva': 'org_nuva',
		        'strategy': 'org_strategy',
        'strc': 'org_strategy',
        'michael saylor': 'org_strategy',
        '스트래티지': 'org_strategy',
        '마이클세일러': 'org_strategy',

        'bank of korea': 'org_bok',
        '한국은행': 'org_bok',
        '신현송': 'person_hyunsongshin',
        'hyun song shin': 'person_hyunsongshin',

        'coinbase': 'org_coinbase',
        'openai': 'org_openai',
        'tom duff gordon': 'person_tomduffgordon',
        '톰더프고든': 'person_tomduffgordon',

        'ecb': 'org_ecb',
        'esma': 'org_esma',

        'bithumb': 'org_bithumb',
        '빗썸': 'org_bithumb',

        'kraken': 'org_kraken',
        '애플': 'org_apple',
        'apple': 'org_apple',
		'bnk': 'org_bnk',
        '부산은행': 'org_bnk',
        'toss': 'org_toss',
        '토스': 'org_toss',
        'bitmine': 'org_bitmine',
        '비트마인': 'org_bitmine',
        'christopher giancarlo': 'person_giancarlo',
        '크리스지안카를로': 'person_giancarlo',
        'g love': 'person_glove',
        'glove': 'person_glove',
    }

    for key, value in org_map.items():
        if key in text:
            tags.add(value)

    # 액션
    action_map = {
        'approval': 'act_approval',
        'approve': 'act_approval',
        'bank charter': 'act_bank_charter',
        'custody': 'act_custody',
        'integration': 'act_integration',
        'integrated': 'act_integration',
        'payment': 'act_payment',
        'payments': 'act_payment',
        'staking': 'act_staking',
        'unlock': 'act_unlock',
        'unlocked': 'act_unlock',
        'surveillance': 'act_surveillance',
        '감시': 'act_surveillance',
        'regulation': 'act_regulation',
        'bill': 'act_bill',
        'law': 'act_law',
        'risk': 'act_risk',
        'adoption': 'act_adoption',
        'institutional': 'act_institutional',
 		'comment': 'act_comment',
        'issuer': 'act_issuer',
        'repay': 'act_repay',
        'sale': 'act_sale',
        'sold': 'act_sale',
        '매각': 'act_sale',
        '상환': 'act_repay',
        '의견 수렴': 'act_comment',
		        'move': 'act_move',
        'joins': 'act_move',
        'joined': 'act_move',
        'appointed': 'act_move',
        'hire': 'act_move',
        'hired': 'act_move',
        '이동': 'act_move',
        '합류': 'act_move',

        'supports': 'act_support',
        'support': 'act_support',
        '지지': 'act_support',

        'calls for': 'act_policy',
        'urges': 'act_policy',
        '촉구': 'act_policy',

        'bought': 'act_buy',
        'buy': 'act_buy',
        '매입': 'act_buy',
        '매수': 'act_buy',
		'stolen': 'act_theft',
        'theft': 'act_theft',
        '도난': 'act_theft',
        'leak': 'act_leak',
        'leaked': 'act_leak',
        '유출': 'act_leak',
        'refuse': 'act_refuse',
        'refused': 'act_refuse',
        '거부': 'act_refuse',
    }

    for key, value in action_map.items():
        if key in text:
            tags.add(value)



    return ' | '.join(sorted(tags))


def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = normalize_for_duplicate(story.get('title', ''))
    signature = build_story_signature(story)

    # 제목 유사도는 조금 완화
    for old_title in seen_titles:
        ratio = SequenceMatcher(None, title, old_title).ratio()
        if ratio >= 0.88:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    # 시그니처가 너무 짧으면 중복판단 안 함
    if len(signature.split('|')) < 3:
        return False

    # 액션(act_)이 같은 경우에만 강하게 중복 판정
    current_actions = {x for x in signature.split('|') if x.strip().startswith('act_')}

    for old_sig in seen_signatures:
        old_actions = {x for x in old_sig.split('|') if x.strip().startswith('act_')}

        if not current_actions or not old_actions:
            continue

        if current_actions and old_actions and current_actions.isdisjoint(old_actions):
            continue

        ratio = SequenceMatcher(None, signature, old_sig).ratio()
        if ratio >= 0.92:
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

    text = re.sub(r'문제가 아니\.$', '문제가 아님', text)
    text = re.sub(r'아니\.$', '아님', text)
    text = re.sub(r'될 것\.$', '될 것임', text)
    text = re.sub(r'계획이\.$', '계획임', text)
    text = re.sub(r'보인다\.$', '보임', text)
    text = re.sub(r'전망이다\.$', '전망임', text)

    text = re.sub(r'매도가 있었음.*$', '매도가 있었음', text)
    text = re.sub(r'커졌음.*$', '커졌음', text)

    text = re.sub(r'했음고', '했고', text)
    text = re.sub(r'했음는', '했다는', text)
    text = text.replace('있음고', '있다고')
    text = text.replace('변화할 것임.', '변화할 것임')
    text = re.sub(r'#([A-Za-z0-9가-힣]+)\s+\n', r'#\1\n', text)

    text = re.sub(r'\s+', ' ', text).strip()
    return text
	


def _normalize_footer_tags(tags: list[str]) -> list[str]:
    mapping = {
        '#Japan': '#일본', '#Bhutan': '#부탄', '#Germany': '#독일', '#US': '#미국', '#USA': '#미국',
        '#Ripple': '#XRP', '#RL#미국D': '#RLUSD', '#F O M C': '#FOMC', '#HesterPeirce': '#헤스터피어스',
        '#CME': '#시카고상품거래소(CME)', '#Qivalis': '#키발리스', '#RaoulPal': '#라울팔',
        '#Nuva': '#누바', '#Tempo': '#템포', '#MoneyGram': '#머니그램', '#Muro': '#무로', '#Santander': '#산탄데르'
    }
    out=[]
    seen=set()
    for tag in tags:
        tag = mapping.get(tag, tag)
        if tag == '#리플':
            tag = '#XRP'
        if tag and tag not in seen:
            out.append(tag)
            seen.add(tag)
    return out

def build_message(story: dict) -> str:
    title = story.get('title', '')
    desc = story.get('desc', '')
    article_text = get_best_source_text(story)

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

    # 기사 원문/제목 + 요약문 둘 다 기준으로 엔티티 추출
    story_entities = extract_entities(story, max_tags=12)
    summary_entities = extract_entities_from_summary(summary_ko, max_tags=12)

    merged_entities = []
    seen_entities = set()
    for e in story_entities + summary_entities:
        key = e.lower()
        if key not in seen_entities:
            merged_entities.append(e)
            seen_entities.add(key)

    entities = [
        e for e in merged_entities
        if e in INLINE_TAG_WHITELIST or entity_korean_name(e) in INLINE_TAG_WHITELIST
    ]

    summary_ko, dynamic_tags = inject_entity_hashtags(summary_ko, entities)
    summary_ko = fix_broken_inline_hashtags(summary_ko)
    summary_ko = remove_duplicate_inline_hashtags(summary_ko)
    summary_ko = finalize_summary_ending(summary_ko)

    summary = summary_ko if summary_ko else story.get('title', '')
    summary = format_summary_for_telegram(summary, max_sentences=3, max_chars=115)
    summary = summary.replace('자동뉴스', '').strip()
    summary = summary.replace('다음 기사는', '').strip()
    summary = summary.replace('뉴스레터', '').strip()
    summary = summary.replace('가상자산', '암호화폐')
    summary = summary.replace('리플 얼라이언스', 'XRP 얼라이언스')
    summary = summary.replace('리플 고래', 'XRP 고래')
    summary = summary.replace('리플 선물', 'XRP 선물')
    summary = summary.replace('Santiment', '샌티먼트')
    summary = summary.replace('Hester Peirce', '헤스터피어스')
    summary = summary.replace('FOMC 회의록', '#FOMC 회의록')
    summary = summary.replace('연준은', '#연준 은')
    summary = summary.replace('연준 의장', '#연준 의장')
    summary = summary.replace('CME ', '시카고상품거래소(CME) ')
    summary = summary.replace('Qivalis', '키발리스')
    summary = summary.replace('Raoul Pal', '라울팔')
    summary = summary.replace('NUVA', '누바')
    summary = summary.replace('Tempo', '템포')
    summary = summary.replace('MoneyGram', '머니그램')
    summary = summary.replace('MiCA', '미카')
    summary = summary.replace('Truth Social', '트루스소셜')
    summary = summary.replace('Tohoku Bank', '도호쿠은행')
    summary = summary.replace('SoftBank', '소프트뱅크')
    summary = summary.replace('Twenty One Capital', '트웬티원캐피털')
    summary = summary.replace('WhiteBIT', '화이트비트')
    summary = summary.replace('Timothy Massad', '티머시매사드')

    dynamic_tags = filter_final_tags(dynamic_tags)
    footer_tags = dynamic_tags + [f'#{t}' for t in FINAL_HASHTAGS]

    inline_tags = set(re.findall(r'#[A-Za-z0-9가-힣]+', summary))
    footer_tags = [t for t in footer_tags if t not in inline_tags]

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

    seen_canonical_keys = {
        item.get('canonical_key', '')
        for item in posted.values()
        if item.get('canonical_key')
    }

    for s in filtered:
        title = s.get('title', '')
        norm_title = normalize_for_duplicate(title)
        signature = build_story_signature(s)
        canonical_key = build_canonical_topic_key(s)
        url = s.get('url', '').strip()

        current_actions = {x for x in signature.split('|') if x.strip().startswith('act_')}

        if (
            signature
            and len(signature.split('|')) >= 3
            and signature in seen_topic_keys
        ):
            log(f"[토픽중복 제외] {title}")
            log(f"  └ 시그니처: {signature}")
            continue

        if is_canonical_duplicate(canonical_key, seen_canonical_keys):
            log(f"[정규토픽중복 제외] {title}")
            log(f"  └ canonical_key: {canonical_key}")
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

        if signature and len(signature.split('|')) >= 3:
            seen_topic_keys.add(signature)

        if canonical_key:
            seen_canonical_keys.add(canonical_key)

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
            canonical_key = build_canonical_topic_key(story)
            update_posted(
                story['title'],
                posted,
                story.get('url', ''),
                signature,
                canonical_key
            )
            state['posted'] = posted
            save_state(STATE_FILE, state)
            log(f"Posted: {story['title']}")
        else:
            log(f"Failed: {story['title']}")

        time.sleep(0.3)



# ---------------------------------------------------------------------------
# PATCH: 2026-05-20 duplicate / readability / tag refinement
# ---------------------------------------------------------------------------

_OLD_matches_keywords = matches_keywords
_OLD_build_story_signature = build_story_signature
_OLD_build_canonical_topic_key = build_canonical_topic_key
_OLD_is_canonical_duplicate = is_canonical_duplicate
_OLD_is_semantically_duplicate = is_semantically_duplicate
_OLD_format_summary_for_telegram = format_summary_for_telegram

INLINE_TAG_WHITELIST.update({
    '엘리자베스워런', 'OCC', '신탁은행', '엑스알피얼라이언스', '디센트',
    '아이렌', '엔비디아', '트럼프', '연준', '마스터계정',
    '한화투자증권', '두나무', '금융', '위메이드', 'NICE정보통신',
    'RWA', '토큰화', '스테이블코인', '독일', '유니온인베스트먼트',
    'CNBC', '케빈워시', 'BC카드', '결제', '인프라', '아베', 'WETH', 'rsETH',
    '일본', '부탄', '시장구조법안'
})

MANUAL_TRANSLATIONS.update({
    'Elizabeth Warren': '엘리자베스워런',
    'Warren': '엘리자베스워런',
    'OCC': 'OCC',
    'trust bank': '신탁은행',
    "D'CENT": '디센트',
    'D’CENT': '디센트',
    'DCENT': '디센트',
    'XRP Alliance': '엑스알피얼라이언스',
    'IREN': '아이렌',
    'Iris Energy': '아이렌',
    'NVIDIA': '엔비디아',
    'Federal Reserve': '연준',
    'Fed': '연준',
    'master account': '마스터계정',
    'Hanwha Investment Securities': '한화투자증권',
    'Hanwha Investment': '한화투자증권',
    'Dunamu': '두나무',
    'Wemade': '위메이드',
    'NICE Information & Telecommunication': 'NICE정보통신',
    'NICE Information&Telecommunication': 'NICE정보통신',
    'Union Investment': '유니온인베스트먼트',
    'Kevin Warsh': '케빈워시',
    'BC Card': 'BC카드',
    'Aave': '아베',
    'CLARITY Act': '시장구조법안',
    'CLARITY': '시장구조법안',
})

_EXTRA_NEGATIVE_PATTERNS = [
    r'\bcrypto longs?\b', r'\blongs? lose\b', r'\bshorts?\b',
    r'\bliquidation(?:s)?\b', r'\bliquidated\b',
    r'롱\s*베팅', r'숏\s*베팅', r'선물\s*시장', r'청산', r'대규모\s*청산',
    r'시장\s*심리', r'심리\s*악화', r'심리\s*위축',
    r'하락함', r'상승함', r'급락', r'급등', r'하락세', r'약세', r'반등',
    r'선\s*유지', r'77,?000\s*달러\s*선', r'가격이\s*[^\n]{0,12}(유지|깨짐|뚫|돌파)', r'현물\s*etf\s*유출',
]

_EVENT_RULES = {
    'ent_warren': [r'elizabeth warren', r'\bwarren\b', r'엘리자베스\s*워런', r'엘리자베스워런'],
    'ent_occ': [r'\bocc\b', r'통화감독청'],
    'obj_trustbank': [r'trust bank', r'신탁\s*은행'],
    'act_probe': [r'investigat', r'조사', r'문제\s*삼', r'문제제기', r'착수'],
    'ent_dcent': [r"d[’']?cent", r'디센트'],
    'ent_xrp_alliance': [r'xrp alliance', r'엑스알피얼라이언스'],
    'obj_rewards': [r'earnxrp', r'mxrpy', r'수익금고', r'리워드', r'금고'],
    'act_connect': [r'connect', r'연결', r'제공'],
    'ent_iren': [r'\biren\b', r'iris energy', r'아이렌'],
    'ent_nvidia': [r'nvidia', r'엔비디아'],
    'obj_ai_cloud': [r'ai cloud', r'인프라 클라우드', r'hpc', r'고성능 컴퓨팅'],
    'act_convert': [r'전환', r'본격화', r'가속화', r'확보'],
    'ent_trump': [r'\btrump\b', r'트럼프'],
    'ent_fed': [r'federal reserve', r'\bfed\b', r'연준'],
    'obj_master_account': [r'master account', r'마스터\s*계정'],
    'act_review': [r'검토', r'명령', r'접근\s*권한'],
    'ent_hanwha': [r'한화투자증권', r'hanwha investment'],
    'ent_dunamu': [r'\bdunamu\b', r'두나무'],
    'act_invest': [r'투자', r'지분', r'매수'],
    'amt_6000eok': [r'6000억', r'9\.84%'],
    'ent_wemade': [r'위메이드', r'\bwemade\b'],
    'ent_nice': [r'nice정보통신', r'nice information'],
    'obj_mou': [r'\bmou\b', r'협약', r'체결'],
    'obj_payment': [r'결제\s*인프라', r'웹3\s*결제', r'결제'],
    'ent_union': [r'union investment', r'유니온인베스트먼트'],
    'geo_germany': [r'germany', r'독일'],
    'obj_stablecoin_safety': [r'스테이블코인', r'usdc', r'usdt'],
    'act_warn': [r'안전하지\s*않', r'보지\s*않', r'경고', r'설명'],
    'ent_cnbc': [r'\bcnbc\b'],
    'obj_innovation50': [r'혁신\s*기업\s*50', r'innovation 50'],
    'ent_kevinwarsh': [r'kevin warsh', r'케빈\s*워시', r'케빈워시'],
    'obj_asset_sale': [r'자산을?\s*매각', r'매각함', r'매각'],
    'ent_bccard': [r'bc카드', r'\bbc card\b'],
    'obj_patent': [r'특허', r'인프라\s*확장'],
    'ent_aave': [r'\baave\b', r'아베'],
    'obj_weth': [r'\bweth\b', r'rseth', r'담보인정비율', r'복구'],
    'geo_japan': [r'japan', r'일본'],
    'geo_bhutan': [r'bhutan', r'부탄'],
    'bill_clarity': [r'clarity act', r'시장구조법안', r'클래리티'],
    'ent_qivalis': [r'qivalis', r'키발리스'],
    'ent_raoulpal': [r'raoul pal', r'라울팔', r'라울\s*팔'],
    'ent_nuva': [r'\bnuva\b', r'누바'],
    'ent_tempo': [r'\btempo\b', r'템포'],
    'ent_moneygram': [r'moneygram', r'머니그램'],
    'ent_muro': [r'\bmuro\b', r'무로'],
    'ent_santander': [r'santander', r'산탄데르'],
    'ent_fomc': [r'\bfomc\b', r'FOMC'],
    'ent_hester': [r'hester peirce', r'헤스터\s*피어스', r'헤스터피어스'],
    'ent_cme': [r'\bcme\b', r'cme group', r'chicago mercantile exchange', r'시카고상품거래소'],
    'obj_line_hold': [r'77,?000', r'선\s*유지', r'선을?\s*걸고?\s*유지', r'깨짐', r'뚫', r'돌파', r'지지선', r'저항선'],
}


def _story_text(story: dict) -> str:
    return f"{story.get('title','')} {story.get('desc','')}"

def _extract_event_markers(text: str) -> list[str]:
    low = normalize_for_duplicate(text)
    out = []
    for key, patterns in _EVENT_RULES.items():
        for pat in patterns:
            if re.search(pat, low, re.I):
                out.append(key)
                break
    if re.search(r'72만|720000|720,?000', low):
        out.append('amt_72man')
    if re.search(r'34억\s*달러|3\.4\s*billion', low):
        out.append('amt_34eok_dollar')
    if re.search(r'1억\s*9300만\s*달러|193 million', low):
        out.append('amt_193m')
    if re.search(r'630억\s*달러|63 billion', low):
        out.append('amt_63b')
    if re.search(r'4,?500억\s*개|450 billion', low):
        out.append('amt_450b_units')
    if re.search(r'25개\s*은행|37개\s*은행', low):
        out.append('obj_bank_expansion')
    return sorted(set(out))

def _normalize_signature_parts(parts):
    return sorted(set([p.strip() for p in parts if p and p.strip()]))

def build_story_signature(story: dict) -> str:
    base = _OLD_build_story_signature(story)
    parts = [p.strip() for p in base.split('|') if p.strip()]
    parts.extend(_extract_event_markers(_story_text(story)))
    return ' | '.join(_normalize_signature_parts(parts))

def build_canonical_topic_key(story: dict) -> str:
    base = _OLD_build_canonical_topic_key(story)
    parts = [p.strip() for p in base.split('|') if p.strip()]
    parts.extend(_extract_event_markers(_story_text(story)))
    return ' | '.join(_normalize_signature_parts(parts))

def _core_event_tokens(key: str) -> set:
    toks = {x.strip() for x in (key or '').split('|') if x.strip()}
    return {t for t in toks if not t.startswith('asset_') and not t.startswith('geo_')}

def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
    if not canonical_key:
        return False
    cur_all = {x.strip() for x in canonical_key.split('|') if x.strip()}
    cur_core = _core_event_tokens(canonical_key)

    for old_key in seen_keys:
        old_all = {x.strip() for x in old_key.split('|') if x.strip()}
        old_core = _core_event_tokens(old_key)
        shared_core = cur_core & old_core
        shared_all = cur_all & old_all

        if len(shared_core) >= 2:
            log(f"[정규토픽중복 제외] shared_core={shared_core}")
            return True
        if len(shared_all) >= 4 and len(shared_core) >= 1:
            log(f"[정규토픽유사 제외] shared_all={shared_all}")
            return True
    return False

def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = normalize_for_duplicate(story.get('title', ''))
    signature = build_story_signature(story)
    cur_all = {x.strip() for x in signature.split('|') if x.strip()}
    cur_core = _core_event_tokens(signature)

    for old_title in seen_titles:
        ratio = SequenceMatcher(None, title, old_title).ratio()
        if ratio >= 0.92:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    if len(cur_all) < 3:
        return False

    for old_sig in seen_signatures:
        old_all = {x.strip() for x in old_sig.split('|') if x.strip()}
        old_core = _core_event_tokens(old_sig)
        shared_core = cur_core & old_core
        shared_all = cur_all & old_all

        if not shared_core:
            continue
        if len(shared_core) >= 2:
            log(f"[의미중복 제외] shared_core={shared_core}")
            return True
        if len(shared_core) >= 1 and len(shared_all) >= 4:
            log(f"[시그니처 교집합 중복] {signature} <> {old_sig}")
            return True
        ratio = SequenceMatcher(None, signature, old_sig).ratio()
        if len(shared_core) >= 1 and ratio >= 0.93:
            log(f"[시그니처 유사도 중복] {signature} <> {old_sig} / {ratio:.2f}")
            return True

    return False

def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
    raw_text = _story_text(story)
    raw_lower = raw_text.lower()

    if any(re.search(p, raw_lower, re.I) for p in _EXTRA_NEGATIVE_PATTERNS):
        print(f"[시황심리/롱숏 제외] {story.get('title', '')}")
        return False

    return _OLD_matches_keywords(story, coins, econ_keywords, korean_keywords)

def _clean_summary_for_style(text: str) -> str:
    text = text or ""
    text = text.replace('가상자산', '암호화폐')
    text = text.replace('있음고', '있다고')
    text = text.replace('RL#미국D', '#RLUSD').replace('#R L U S D', '#RLUSD')
    text = text.replace('리플 얼라이언스', 'XRP 얼라이언스')
    text = text.replace('리플 고래', 'XRP 고래')
    text = text.replace('리플 선물', 'XRP 선물')
    text = re.sub(r'시장 심리[^.\n]*', '', text)
    text = re.sub(r'가격을 끌어올리지 못함', '', text)
    text = re.sub(r'(?<!#)리플(?=\s*고래|\s*선물|\s*현물|\s*토큰|\s*네트워크|\s*얼라이언스)', 'XRP', text)
    text = re.sub(r'(?<!#)XRP(?=\s*(고래|선물|현물|보유량|리워드|토큰))', '#XRP', text, count=1)
    text = re.sub(r'(?<!#)FOMC(?=\s)', '#FOMC', text, count=1)
    text = re.sub(r'(?<!#)헤스터피어스(?=\s)', '#헤스터피어스', text, count=1)
    text = re.sub(r'(?<!#)시카고상품거래소\(CME\)(?=\s)', '#시카고상품거래소(CME)', text, count=1)
    text = re.sub(r'(?<!#)키발리스(?=\s|[가-힣])', '#키발리스', text, count=1)
    text = re.sub(r'(?<!#)라울팔(?=\s)', '#라울팔', text, count=1)
    text = re.sub(r'(?<!#)누바(?=\s|,|\()', '#누바', text, count=1)
    text = re.sub(r'(?<!#)템포(?=\s|,|\()', '#템포', text, count=1)
    text = re.sub(r'(?<!#)무로(?=\s|,)', '#무로', text, count=1)
    text = re.sub(r'(?<!#)산탄데르(?=\s|,)', '#산탄데르', text, count=1)
    text = re.sub(r'(?<!#)RLUSD(?=\s|,|\))', '#RLUSD', text, count=1)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def format_summary_for_telegram(text: str, max_sentences: int = 3, max_chars: int = 110) -> str:
    text = _clean_summary_for_style(text)
    text = (text or "").replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n{2,}', '\n', text).strip()
    text = re.sub(r'[ \t]+', ' ', text)

    chunks = [c.strip() for c in text.split('\n') if c.strip()]
    if len(chunks) >= 2:
        picked = []
        total = 0
        for c in chunks:
            if len(picked) >= max_sentences:
                break
            if picked and total + len(c) > max_chars:
                break
            picked.append(c)
            total += len(c)
        if picked:
            return '\n\n'.join(picked).strip()

    return _OLD_format_summary_for_telegram(text, max_sentences=max_sentences, max_chars=max_chars)

def _ensure_case_tags(summary: str, story: dict, footer_tags: list[str]) -> list[str]:
    text = _story_text(story) + " " + (summary or "")
    additions = []
    pairs = [
        ('엘리자베스워런', [r'elizabeth warren', r'엘리자베스워런', r'엘리자베스 워런']),
        ('OCC', [r'\bocc\b', r'통화감독청']),
        ('신탁은행', [r'trust bank', r'신탁\s*은행']),
        ('엑스알피얼라이언스', [r'xrp alliance', r'엑스알피얼라이언스']),
        ('디센트', [r"d[’']?cent", r'디센트']),
        ('아이렌', [r'\biren\b', r'iris energy', r'아이렌']),
        ('엔비디아', [r'nvidia', r'엔비디아']),
        ('한화투자증권', [r'한화투자증권', r'hanwha investment']),
        ('두나무', [r'\bdunamu\b', r'두나무']),
        ('위메이드', [r'\bwemade\b', r'위메이드']),
        ('NICE정보통신', [r'nice information', r'nice정보통신']),
        ('유니온인베스트먼트', [r'union investment', r'유니온인베스트먼트']),
        ('독일', [r'germany', r'독일']),
        ('CNBC', [r'\bcnbc\b']),
        ('XRP', [r'\bxrp\b', r'\bripple\b', r'리플']),
        ('FOMC', [r'\bfomc\b']),
        ('헤스터피어스', [r'hester peirce', r'헤스터\s*피어스', r'헤스터피어스']),
        ('시카고상품거래소(CME)', [r'\bcme\b', r'cme group', r'chicago mercantile exchange', r'시카고상품거래소']),
        ('키발리스', [r'qivalis', r'키발리스']),
        ('라울팔', [r'raoul pal', r'라울\s*팔', r'라울팔']),
        ('누바', [r'\bnuva\b', r'누바']),
        ('템포', [r'\btempo\b', r'템포']),
        ('머니그램', [r'moneygram', r'머니그램']),
        ('무로', [r'\bmuro\b', r'무로']),
        ('산탄데르', [r'santander', r'산탄데르']),
        ('RLUSD', [r'\brlusd\b', r'RLUSD']),
        ('금융', [r'금융', r'financial']),
        ('케빈워시', [r'kevin warsh', r'케빈워시', r'케빈 워시']),
        ('연준', [r'federal reserve', r'\bfed\b', r'연준']),
        ('자산', [r'자산']),
        ('매각', [r'매각', r'sale', r'sell']),
        ('스테이블코인', [r'stablecoin', r'스테이블코인']),
        ('RWA', [r'\brwa\b']),
        ('토큰화', [r'tokeni[sz]ation', r'토큰화']),
    ]
    for tag, patterns in pairs:
        if any(re.search(p, text, re.I) for p in patterns):
            additions.append(f'#{tag}')
    for t in additions:
        if t not in footer_tags:
            footer_tags.append(t)
    return footer_tags

def build_message(story: dict) -> str:
    title = story.get('title', '')
    desc = story.get('desc', '')
    article_text = get_best_source_text(story)

    summary_ko = rewrite_summary_with_gemini(title=title, article_text=article_text, fallback_text=desc)
    if not summary_ko:
        raw_source = f"{title}. {desc}"
        raw_summary = summarize_text(raw_source, title=title, max_sentences=SUMMARY_SENTENCES)
        summary_ko = translate_text_to_korean(raw_summary)
        summary_ko = cleanup_text(summary_ko)
        summary_ko = fix_translation_terms(summary_ko)
        summary_ko = fix_truncated_phrases(summary_ko)
        summary_ko = normalize_style(summary_ko)
        summary_ko = cleanup_text(summary_ko)

    story_entities = extract_entities(story, max_tags=14)
    summary_entities = extract_entities_from_summary(summary_ko, max_tags=14)

    merged_entities = []
    seen_entities = set()
    for e in story_entities + summary_entities:
        k = e.lower()
        if k not in seen_entities:
            merged_entities.append(e)
            seen_entities.add(k)

    entities = []
    for e in merged_entities:
        ko = entity_korean_name(e)
        if e in INLINE_TAG_WHITELIST or ko in INLINE_TAG_WHITELIST:
            entities.append(e)

    summary_ko, dynamic_tags = inject_entity_hashtags(summary_ko, entities)
    summary_ko = fix_broken_inline_hashtags(summary_ko)
    summary_ko = remove_duplicate_inline_hashtags(summary_ko)
    summary_ko = finalize_summary_ending(summary_ko)
    summary_ko = _clean_summary_for_style(summary_ko)

    summary = summary_ko if summary_ko else story.get('title', '')
    summary = format_summary_for_telegram(summary, max_sentences=3, max_chars=110)
    summary = summary.replace('자동뉴스', '').replace('다음 기사는', '').replace('뉴스레터', '').strip()

    dynamic_tags = filter_final_tags(dynamic_tags)
    footer_tags = dynamic_tags + [f'#{t}' for t in FINAL_HASHTAGS]
    footer_tags = _ensure_case_tags(summary, story, footer_tags)
    footer_tags = _normalize_footer_tags(footer_tags)

    inline_tags = set(re.findall(r'#[A-Za-z0-9가-힣]+', summary))
    footer_tags = [f for f in footer_tags if f not in inline_tags]

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



# ===== 2026-05-21 late patch: duplicate / XRP / SBI / price-line filtering =====

_OLD_build_story_signature_v3 = build_story_signature
_OLD_build_canonical_topic_key_v3 = build_canonical_topic_key
_OLD_is_canonical_duplicate_v3 = is_canonical_duplicate
_OLD_is_semantically_duplicate_v3 = is_semantically_duplicate
_OLD_matches_keywords_v3 = matches_keywords
_OLD_build_message_v3 = build_message

_EXTRA_NEGATIVE_PATTERNS_V3 = [
    r'\bholds? above\b', r'\bholds? below\b', r'\bholds? firm\b',
    r'\bbreaks? above\b', r'\bbreaks? below\b', r'\bbreaking above\b', r'\bbreaking below\b',
    r'\bprice (?:holds|held|holding)\b', r'\bprice action\b', r'\bmarket sentiment\b',
    r'77,?000\s*dollar', r'77,?000달러', r'달러\s*선', r'지지선', r'저항선',
    r'견고하게 유지', r'유지함', r'유지 중', r'깨짐', r'뚫음', r'돌파', r'버팀',
    r'챌린지', r'challenge', r'fan story', r'promo', r'campaign',
    r'moew', r'realgo', r'fast or go home', r'mainnet launch', r'clob dex',
    r'truth social', r'etf launch plan', r'launch plan scrapped'
]

_EVENT_MARKER_PATTERNS_V3 = {
    'evt_sbiremit_tohoku': [r'sbi\s*remit', r'sbiremit', r'sbi리밋', r'tohoku\s*bank', r'도호쿠은행'],
    'evt_occ_warren': [r'elizabeth\s+warren', r'엘리자베스\s*워런', r'occ', r'trust\s*bank', r'신탁\s*은행'],
    'evt_xrpalliance_dcent': [r'xrp\s*alliance', r'엑스알피얼라이언스', r'd[’\']?cent', r'디센트', r'mxrpy', r'earnxrp'],
    'evt_iren_nvidia': [r'\biren\b', r'iris\s*energy', r'아이렌', r'nvidia', r'엔비디아'],
    'evt_trump_fed_master': [r'trump', r'트럼프', r'fed', r'연준', r'master\s*account', r'마스터\s*계정'],
    'evt_hanwha_dunamu': [r'한화투자증권', r'hanwha\s*investment', r'dunamu', r'두나무'],
    'evt_qivalis_banks': [r'qivalis', r'키발리스', r'stablecoin', r'25\s*개\s*은행', r'37\s*개\s*은행'],
    'evt_moneygram_tempo': [r'moneygram', r'머니그램', r'tempo', r'템포', r'stripe', r'스트라이프'],
    'evt_mica_review': [r'\bmica\b', r'미카', r'defi', r'스테이블코인\s*이자'],
    'evt_rlusd': [r'\brlusd\b'],
    'evt_cme_xrp': [r'\bcme\b', r'시카고상품거래소', r'\bxrp\b', r'630억\s*달러'],
}

_FORCED_INLINE_MAP_V3 = [
    ('XRP', [r'\bxrp\b']),
    ('FOMC', [r'\bfomc\b']),
    ('헤스터피어스', [r'hester\s+peirce', r'헤스터\s*피어스', r'헤스터피어스']),
    ('시카고상품거래소(CME)', [r'\bcme\b', r'cme\s+group', r'chicago\s+mercantile\s+exchange', r'시카고상품거래소']),
    ('SBI', [r'\bsbi\b']),
    ('SBI리밋', [r'sbi\s*remit', r'sbiremit', r'sbi리밋']),
    ('리플', [r'\bripple\b', r'리플', r'ripplenet', r'리플넷']),
    ('리플넷', [r'ripplenet', r'리플넷']),
    ('도호쿠은행', [r'tohoku\s*bank', r'도호쿠은행']),
    ('키발리스', [r'qivalis', r'키발리스']),
    ('무로', [r'\bmuro\b', r'무로']),
    ('산탄데르', [r'santander', r'산탄데르']),
    ('라울팔', [r'raoul\s+pal', r'라울\s*팔', r'라울팔']),
    ('누바', [r'\bnuva\b', r'누바']),
    ('템포', [r'\btempo\b', r'템포']),
    ('머니그램', [r'moneygram', r'머니그램']),
    ('RLUSD', [r'\brlusd\b']),
]

_EXTRA_FOOTER_TAGS_V3 = [
    ('#SBI', [r'\bsbi\b']),
    ('#SBI리밋', [r'sbi\s*remit', r'sbiremit', r'sbi리밋']),
    ('#리플', [r'\bripple\b', r'리플', r'ripplenet', r'리플넷']),
    ('#XRP', [r'\bxrp\b']),
    ('#FOMC', [r'\bfomc\b']),
    ('#헤스터피어스', [r'hester\s+peirce', r'헤스터\s*피어스', r'헤스터피어스']),
    ('#시카고상품거래소', [r'\bcme\b', r'cme\s+group', r'시카고상품거래소']),
    ('#금융', [r'금융', r'financial']),
    ('#도호쿠은행', [r'tohoku\s*bank', r'도호쿠은행']),
    ('#리플넷', [r'ripplenet', r'리플넷']),
    ('#RLUSD', [r'\brlusd\b']),
]

def _story_text_v3(story: dict) -> str:
    return f"{story.get('title','')} {story.get('desc','')}"


def _extract_event_markers_v3(text: str) -> list[str]:
    low = normalize_for_duplicate(text or '')
    found = []
    for key, patterns in _EVENT_MARKER_PATTERNS_V3.items():
        if any(re.search(p, low, re.I) for p in patterns):
            found.append(key)
    return found


def _normalize_sig_parts_v3(parts: list[str]) -> list[str]:
    out = []
    seen = set()
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p not in seen:
            out.append(p)
            seen.add(p)
    return sorted(out)


def build_story_signature(story: dict) -> str:
    base = _OLD_build_story_signature_v3(story)
    parts = [p.strip() for p in base.split('|') if p.strip()]
    parts.extend(_extract_event_markers_v3(_story_text_v3(story)))
    return ' | '.join(_normalize_sig_parts_v3(parts))


def build_canonical_topic_key(story: dict) -> str:
    base = _OLD_build_canonical_topic_key_v3(story)
    parts = [p.strip() for p in base.split('|') if p.strip()]
    parts.extend(_extract_event_markers_v3(_story_text_v3(story)))
    return ' | '.join(_normalize_sig_parts_v3(parts))


def _core_event_tokens_v3(key: str) -> set:
    toks = {x.strip() for x in (key or '').split('|') if x.strip()}
    return {t for t in toks if not t.startswith('asset_') and not t.startswith('geo_')}


def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
    if not canonical_key:
        return False
    cur_all = {x.strip() for x in canonical_key.split('|') if x.strip()}
    cur_core = _core_event_tokens_v3(canonical_key)
    for old_key in seen_keys:
        old_all = {x.strip() for x in old_key.split('|') if x.strip()}
        old_core = _core_event_tokens_v3(old_key)
        shared_core = cur_core & old_core
        shared_all = cur_all & old_all
        if len(shared_core) >= 2:
            log(f"[정규토픽중복 제외] shared_core={shared_core}")
            return True
        if len(shared_core) >= 1 and len(shared_all) >= 4:
            log(f"[정규토픽유사 제외] shared_all={shared_all}")
            return True
    return False


def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = normalize_for_duplicate(story.get('title', ''))
    signature = build_story_signature(story)
    cur_all = {x.strip() for x in signature.split('|') if x.strip()}
    cur_core = _core_event_tokens_v3(signature)

    for old_title in seen_titles:
        ratio = SequenceMatcher(None, title, old_title).ratio()
        if ratio >= 0.92:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    if len(cur_all) < 3:
        return False

    for old_sig in seen_signatures:
        old_all = {x.strip() for x in old_sig.split('|') if x.strip()}
        old_core = _core_event_tokens_v3(old_sig)
        shared_core = cur_core & old_core
        shared_all = cur_all & old_all
        if len(shared_core) >= 2:
            log(f"[의미중복 제외] shared_core={shared_core}")
            return True
        if len(shared_core) >= 1 and len(shared_all) >= 4:
            log(f"[시그니처 교집합 중복] {signature} <> {old_sig}")
            return True
    return False


def _is_price_level_article_v3(text: str) -> bool:
    low = (text or '').lower()
    price_terms = [
        '77,000달러', '달러 선', '견고하게 유지', '유지함', '유지 중', '깨짐', '뚫음', '돌파',
        'price holds', 'holding above', 'holding below', 'holds above', 'holds below', 'price action',
        '지지선', '저항선', '버팀'
    ]
    market_terms = ['비트코인 가격', 'btc 현물', 'btc spot etf', 'etf 유출', '시장 심리']
    return any(t in low for t in price_terms) and any(t in low for t in market_terms)


def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
    raw_text = _story_text_v3(story)
    raw_lower = raw_text.lower()
    if any(re.search(p, raw_lower, re.I) for p in _EXTRA_NEGATIVE_PATTERNS_V3):
        print(f"[홍보/시황 제외] {story.get('title', '')}")
        return False
    if _is_price_level_article_v3(raw_text):
        print(f"[가격레벨 기사 제외] {story.get('title', '')}")
        return False
    return _OLD_matches_keywords_v3(story, coins, econ_keywords, korean_keywords)


def _clean_summary_for_style_v3(text: str) -> str:
    text = (text or '').replace('가상자산', '암호화폐').replace('있음고', '있다고')
    text = text.replace('RL#미국D', '#RLUSD').replace('#R L U S D', '#RLUSD')
    text = text.replace('RippleNet', '리플넷').replace('SBI Remit', 'SBI리밋').replace('SBIRemit', 'SBI리밋')
    text = text.replace('리플 얼라이언스', 'XRP 얼라이언스').replace('리플 고래', 'XRP 고래').replace('리플 선물', 'XRP 선물')
    text = re.sub(r'시장 심리[^.\n]*', '', text)
    text = re.sub(r'가격을 끌어올리지 못함', '', text)
    # first important inline tags
    for tag, patterns in _FORCED_INLINE_MAP_V3:
        if f'#{tag}' in text:
            continue
        for p in patterns:
            m = re.search(p, text, re.I)
            if m:
                found = text[m.start():m.end()]
                text = text[:m.start()] + '#' + found + text[m.end():]
                break
    # preserve XRP as XRP, not 리플, when ticker/context exists
    text = re.sub(r'(?<!#)리플(?=\s*(고래|선물|현물|보유량|리워드|토큰))', 'XRP', text)
    text = re.sub(r'(?<![#A-Za-z0-9가-힣])XRP(?![A-Za-z0-9가-힣])', '#XRP', text, count=1)
    text = text.replace('#헤스터피어스 후임', '#헤스터피어스 후임 인선') if '후임 인선' in text else text
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _ensure_case_tags_v3(summary: str, story: dict, footer_tags: list[str]) -> list[str]:
    text = _story_text_v3(story) + ' ' + (summary or '')
    for tag, patterns in _EXTRA_FOOTER_TAGS_V3:
        if any(re.search(p, text, re.I) for p in patterns):
            if tag not in footer_tags:
                footer_tags.append(tag)
    return footer_tags


def build_message(story: dict) -> str:
    message = _OLD_build_message_v3(story)
    parts = message.split('\n\n')
    if not parts:
        return message
    summary = parts[0]
    summary = html.unescape(summary)
    summary = _clean_summary_for_style_v3(summary)
    # regenerate footer line if present
    if len(parts) >= 4:
        footer_tags = parts[-1].split()
        footer_tags = _ensure_case_tags_v3(summary, story, footer_tags)
        footer_tags = _normalize_footer_tags(footer_tags)
        inline_tags = set(re.findall(r'#[A-Za-z0-9가-힣()]+', summary))
        dedup=[]; seen=set()
        for t in footer_tags:
            if t in inline_tags:
                continue
            if t not in seen:
                dedup.append(t); seen.add(t)
        parts[0] = html.escape(summary)
        parts[-1] = ' '.join(html.escape(t) for t in dedup)
        return '\n\n'.join(parts)
    return message

if __name__ == '__main__':
    main()
