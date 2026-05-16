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
    '예측시장','차량공유','카풀','거래소','감독',
    '원화','한국예탁결제원','삼성SDS','STO','솔라나','블랙스톤','미시간','페이워드','에타나','오하이오','거래량','시바리움','BTQ','카이아',
    '아이엠뱅크','Hut8','FalconX','비트스탬프','시장구조법안','샌들린','데이비드슈워츠'
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
'비탈릭부텔린', '사토시나카모토', '저스틴썬', '제드맥케일럽', '찰스호스킨슨', '카르다노', '휴고필리온',
'스트래티지', '도널드트럼프', '테더', '플레어', 'FLR', '에테나', '에테나', '메타플래닛', '도리뉴스',
'부탄', 'GMC', '규제', '규제된', '아이엠뱅크', '원화', 'BTQ', '카이아', '한국예탁결제원', '삼성SDS', 'STO',
'솔라나', 'wXRP', '싱가포르', '걸프은행', '스탠다드차타드', '디지털자산기본법', '총선',
'시바리움', 'SWIFT', '백악관', '카타르', '마스터카드',
'IPO', 'CTO', 'XRP', 'XLM', 'BTC', 'ETH', 'SHIB', 'USDC', 'USDT', 'XAUT', 'SOL', 'DOGE',
'토큰화', '수탁', '시드문구', '소송', '규제', '해석',
'DeFi', 'NFT', 'Web3', 'BitMine', '톰리', 'Thomasgeth', 'TimeTraveler', 'JohnSquire',
'유니스왑', 'HaydenAdams', '파월', 'America', '네비다주', 'JPMorgan', '라이드', '바이비트', 'Ledger',
'서클', '머니그램', 'Apple', '페이팔', '스트라이프', '제미니', '칼시', '제드시온', '에버노스',
'XRPLedger', '세계금협회', '디지털금', '비트코인퀀텀', 'BIP360', 'OpenAI', 'Anthropic',
'슈퍼마이크로', 'AI', 'LNG', '바잔', '캘리포니아', '지니어스법안', '지니어스', '법안', 'ICE',
'클래리티', '블랙록', '문페이', '히든로드', '게임스탑', '앤드리슨호로위츠', 'ARC', '구글', '인도', '웰스파고', '피터쉬프', '패니매','ICE', 'EEZ', '현물', '서울', '부산',
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
'업비트', 'USDT', '원화마켓', 'KRW', '아이엠뱅크', '원화', 'BTQ', '카이아', '한국예탁결제원', '삼성SDS', 'STO',
    '솔라나', 'wXRP', '블랙스톤', '미시간', '페이워드', '에타나', '오하이오', '데이비드슈워츠', 'Hut8', 'FalconX', '비트스탬프', '거래량', '시바리움',
    '테라울프', 'TeraWulf', '스위스', '스위스중앙은행', '스위스국립은행',
    'iM Bank', 'iMBank', 'KRW', 'Won', 'BTQ', 'Kaia', 'Korea Securities Depository', 'Samsung SDS', 'STO',
    'Solana', 'wXRP', 'Blackstone', 'Michigan', 'Payward', 'Etana', 'Ohio', 'David Schwartz', 'Hut 8', 'Hut8', 'FalconX', 'Bitstamp', 'Volume', 'Transaction Volume',
    'Revolut', '레볼루트', 'GoMining', '고마이닝', 'ECB', '유럽중앙은행', '요아힘나겔',
    'ASIC', '호주금융감독기관', 'XRPL재단', 'XRP Ledger Foundation',
    '샌들린', 'Sandlin', '노동부', '앤트로픽', 'SpaceX', '스페이스X',
    '데니스안겔', '르네헤이센', '후세인잔가나',
    '샤프링크', '갤럭시디지털', '서클', '페이팔', '페이팔USD', '문페이', '돈랩스', '톤', '톤코인',
    '텔레그램', '테더', '트론', 'USDT', '파올로아르도이노', '시장구조법안', '뱅크오브아메리카', '샌들린', '엑스',
    '아이엠뱅크', 'iM뱅크', '원화', 'BTQ', '카이아', '한국예탁결제원', '삼성SDS', '삼성 SDS', 'STO',
    '솔라나', 'wXRP', '블랙스톤', '미시간', '페이워드', '에타나', '오하이오', '데이비드슈워츠', 'Hut8', '헛8', 'FalconX', '팔콘엑스', '비트스탬프', '거래량',


	
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
    'fan story', 'prize pool', 'campaign reward', 'social media campaign',
    'grant program', 'ai grant program', 'human participation network', 'biomatrix',
    'old cycle', '직면한 적이 없는 지점', '추진력을 잃으면서', '연속 행진',
    'story protocol', 'azuki', 'busan web3 ip', 'busan-based web3 ip', 'campaign starts',
    'digital twin', '디지털트윈', 'understanding ton', 'comprehensive overview', 'messari research',
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
'fan story', 'prize pool', 'campaign', 'social media campaign',
'virtual investor conference', 'investor conference', 'conference online', 'conference update',
'fan story uex through your eyes', 'share your bitget fan story',
'ui bug', 'ux bug', 'display bug', 'app glitch', 'price display glitch', 'almost zero',
'core team', 'operating team', 'new operating team', 'software version', 'version 3.1.3', 'version update',
'award', 'won a prize', 'won prize', 'contest', 'hackathon prize', 'pitches at consensus',
'net outflow', 'net inflow', '순유출', '순유입', 'etf flow', 'etf flows',
'old cycle', 'cycle is dead', '시장 분석가', 'analyst says', 'analyst shah', 'top 15', '시가총액 상위 15위권 밖',
'rlusd', 'standard custody', 'standard custody & trust', 'custody & trust company',
'digital twin', '디지털트윈', 'virtual investor',
	
	
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
    '미국', 'CFTC', 'Elizabeth Warren', '엘리자베스워런',
    '정부', '비트코인', 'BTC', 'ETH', 'XRP',
    '연준', 'SEC', 'ETF', '재무부', '상원', '하원',
    '아이언라이트', '보어히스', '에릭보어히스',
    '마이클세일러', '세일러', '로버트기요사키', '폴앳킨스',
    '데이비드슈워츠', '마이크노보그라츠', '샘알트만', '일론머스크',
    '셰이프시프트', '갈링하우스', '모니카롱', '비탈릭부텔린',
    '사토시나카모토', '저스틴썬', '제드맥케일럽', '찰스호스킨슨', '카르다노', '휴고필리온',
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
    '앤드리슨호로위츠', 'ARC',
    '구글', '인도', '웰스파고', '피터쉬프', '패니매',
    'EEZ', '버핏',
    '스트라이브', '터틀', '스트라이브자산운용', 'STRC', 'SATA', '니움', '비자',
    '오픈크레딧', '스마트계약', '프라이빗크레딧', '기관자금',
'샤프링크', '갤럭시디지털', '서클', '페이팔', '페이팔USD', '문페이', '돈랩스',
'톤', '톤코인', '텔레그램', '테더', '트론', 'USDT', '시장구조법안', '뱅크오브아메리카', '샌들린', '엑스',
	'Bitcoin', 'Ethereum', 'Ripple','United States', 'US', 'Government',
'Federal Reserve', 'Fed', 'Treasury', 'Senate', 'House', 'White House',

'Ironlight', 'Vorhees', 'Erik Vorhees',
'Michael Saylor', 'Saylor', 'Robert Kiyosaki', 'Paul Atkins',
'David Schwartz', 'Mike Novogratz', 'Sam Altman', 'Elon Musk',
'ShapeShift', 'Brad Garlinghouse', 'Garlinghouse', 'Monica Long', 'Vitalik Buterin',
'Satoshi Nakamoto', 'Justin Sun', 'Jed McCaleb', 'Charles Hoskinson', 'Cardano', 'Hugo Philion',
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
'Andreessen Horowitz', 'a16z', 'ARC', '앤드리슨호로위츠',
'SharpLink', 'Sharplink', 'Galaxy Digital', 'GalaxyDigital', 'Circle', 'PayPal', 'PayPalUSD',
'TON', 'Toncoin', 'Telegram', 'Tether', 'Paolo Ardoino', 'Dawn Labs', 'Bank of America', 'BofA',
'Clarity Act', 'Market Structure Bill', 'Sandlin', 'X',
'Google', 'India', 'Wells Fargo', 'Peter Schiff', 'Fannie Mae',
'EEZ', 'Buffett',
'Strive', 'Tuttle', 'Strive Asset Management', 'STRC', 'SATA', 'Nium',
'Open Credit', 'Smart Contract', 'Smart Contracts', 'Private Credit', 'Private Credits', 'Institutional Capital',
'TeraWulf', '테라울프', 'Switzerland', 'Swiss', 'Swiss National Bank', '스위스', '스위스중앙은행',
'Revolut', '레볼루트', 'GoMining', '고마이닝', 'ECB', 'European Central Bank', 'Joachim Nagel', '요아힘나겔',
'ASIC', '호주금융감독기관', 'XRPL Foundation', 'XRP Ledger Foundation', 'XRPL재단',
'Sandlin', '샌들린', 'SpaceX', '스페이스X',
'Denis Angell', 'René Heijsen', 'Hussein Zanganah', '데니스안겔', '르네헤이센', '후세인잔가나',
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
    'CharlesHoskinson': '찰스호스킨슨',
    '찰스호스킨슨': '찰스호스킨슨',
    'Cardano': '카르다노',
    '카르다노': '카르다노',
    'Hugo Philion': '휴고필리온',
    'HugoPhilion': '휴고필리온',
    '휴고 필리온': '휴고필리온',
    '휴고필리온': '휴고필리온',

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

    'Bhutan': '부탄',
    '부탄': '부탄',
    'Gelephu Mindfulness City': 'GMC',
    'GMC': 'GMC',
    'regulated': '규제된',
    'Regulated': '규제된',
    'Unfolded': '언폴디드',

    'iMBank': '아이엠뱅크',
    'iM Bank': '아이엠뱅크',
    '아이엠뱅크': '아이엠뱅크',
    'KRW': '원화',
    'Kaia': '카이아',
    '카이아': '카이아',
    'Korea Securities Depository': '한국예탁결제원',
    'Samsung SDS': '삼성SDS',
    'SamsungSDS': '삼성SDS',
    'STO': 'STO',
    'Solana': '솔라나',
    'wXRP': 'wXRP',
    'Wrapped XRP': 'wXRP',

    'Singapore': '싱가포르',
    '싱가포르': '싱가포르',
    'Gulf Bank': '걸프은행',
    '걸프은행': '걸프은행',
    'Standard Chartered': '스탠다드차타드',
    '스탠다드차타드': '스탠다드차타드',
    'Digital Asset Basic Act': '디지털자산기본법',
    '디지털자산기본법': '디지털자산기본법',
    'General Election': '총선',
    '총선': '총선',

    'Andreessen Horowitz': '앤드리슨호로위츠',
    'a16z': '앤드리슨호로위츠',
    '앤드리슨호로위츠': '앤드리슨호로위츠',
    'ARC': 'ARC',

    'MoonPay': '문페이',
    '문페이': '문페이',
    'SharpLink': '샤프링크',
    'Sharplink': '샤프링크',
    '샤프링크': '샤프링크',
    'Galaxy Digital': '갤럭시디지털',
    'GalaxyDigital': '갤럭시디지털',
    '갤럭시디지털': '갤럭시디지털',
    'Circle': '서클',
    '서클': '서클',
    'PayPal USD': '페이팔USD',
    'PayPalUSD': '페이팔USD',
    '페이팔USD': '페이팔USD',
    'Dawn Labs': '돈랩스',
    'DawnLabs': '돈랩스',
    '돈랩스': '돈랩스',
    'TON': '톤',
    'Toncoin': '톤코인',
    '톤': '톤',
    '톤코인': '톤코인',
    'Telegram': '텔레그램',
    '텔레그램': '텔레그램',
    'Paolo Ardoino': '파올로아르도이노',
    'PaoloArdoino': '파올로아르도이노',
    '파올로 아르도이노': '파올로아르도이노',
    '파올로아르도이노': '파올로아르도이노',
    'Bank of America': '뱅크오브아메리카',
    'BofA': '뱅크오브아메리카',
    '뱅크오브아메리카': '뱅크오브아메리카',
    'Clarity Act': '시장구조법안',
    'CLARITY Act': '시장구조법안',
    '시장구조법안': '시장구조법안',
    'Sandlin': '샌들린',
    '샌들린': '샌들린',
    'X': '엑스',
    '엑스': '엑스',
    'iM Bank': '아이엠뱅크',
    'iMBank': '아이엠뱅크',
    'iM뱅크': '아이엠뱅크',
    '아이엠뱅크': '아이엠뱅크',
    'KRW': '원화',
    'Won': '원화',
    '원화': '원화',
    'BTQ': 'BTQ',
    'Kaia': '카이아',
    '카이아': '카이아',
    'Korea Securities Depository': '한국예탁결제원',
    '한국예탁결제원': '한국예탁결제원',
    'Samsung SDS': '삼성SDS',
    '삼성 SDS': '삼성SDS',
    '삼성SDS': '삼성SDS',
    'STO': 'STO',
    'Solana': '솔라나',
    '솔라나': '솔라나',
    'wXRP': 'wXRP',
    'Blackstone': '블랙스톤',
    '블랙스톤': '블랙스톤',
    'Michigan': '미시간',
    '미시간': '미시간',
    'Payward': '페이워드',
    '페이워드': '페이워드',
    'Etana': '에타나',
    '에타나': '에타나',
    'Ohio': '오하이오',
    '오하이오': '오하이오',
    'Hut 8': 'Hut8',
    'Hut8': 'Hut8',
    '헛8': 'Hut8',
    'FalconX': 'FalconX',
    '팔콘엑스': 'FalconX',
    'Bitstamp': '비트스탬프',
    '비트스탬프': '비트스탬프',
    '거래량': '거래량',

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
	'밈코인':'밈코인',

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
	
'Ripple': '리플',
'리플': '리플',
	'XRPL': 'XRPL',
'DEX': 'DEX',
'Decentralized Exchange': '탈중앙거래소',
'탈중앙거래소': '탈중앙거래소',
'Satoshi Kusama': '사토시쿠사마',
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

'TeraWulf': '테라울프',
'테라울프': '테라울프',
'Switzerland': '스위스',
'Swiss': '스위스',
'스위스': '스위스',
'Swiss National Bank': '스위스중앙은행',
'Swiss central bank': '스위스중앙은행',
'스위스중앙은행': '스위스중앙은행',
'스위스국립은행': '스위스중앙은행',
'Revolut': '레볼루트',
'레볼루트': '레볼루트',
'GoMining': '고마이닝',
'고마이닝': '고마이닝',
'ECB': 'ECB',
'European Central Bank': 'ECB',
'Joachim Nagel': '요아힘나겔',
'요아힘 나겔': '요아힘나겔',
'요아힘나겔': '요아힘나겔',
'ASIC': 'ASIC',
'Australian Securities and Investments Commission': 'ASIC',
'XRPL Foundation': 'XRPL재단',
'XRP Ledger Foundation': 'XRPL재단',
'XRPL재단': 'XRPL재단',
'Sandlin': '샌들린',
'샌들린': '샌들린',
'SpaceX': '스페이스X',
'스페이스X': '스페이스X',
'Denis Angell': '데니스안겔',
'데니스 안겔': '데니스안겔',
'데니스안겔': '데니스안겔',
'René Heijsen': '르네헤이센',
'Rene Heijsen': '르네헤이센',
'르네 헤이센': '르네헤이센',
'르네헤이센': '르네헤이센',
'Hussein Zanganah': '후세인잔가나',
'후세인 잔가나': '후세인잔가나',
'후세인잔가나': '후세인잔가나',
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

    return (has_event and not has_hard_news) or (has_promo and has_event)

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
        'openai', 'anthropic', 'xai', 'grok', 'spacex', 'microsoft'
    ]

    if 'tokenpost.kr/news/tech/' in url:
        return False
    if any(x in raw_lower for x in ['story protocol', 'azuki', 'fan story', 'prize pool', 'human participation network', 'biomatrix']):
        print(f"[비관련기사 제외] {story.get('title', '')}")
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

    # 캠페인/행사/버전/UI 버그/인사개편성 기사 추가 차단
    promo_terms = ['campaign', 'prize pool', 'fan story', 'conference', 'event', 'virtual investor', 'award', 'hackathon', 'software version', 'version 3.1.3', 'ui bug', 'ux bug', 'display glitch', 'core team', 'operating team']
    if any(t in raw_lower for t in promo_terms):
        print(f"[프로모/행사/업데이트 제외] {story.get('title', '')}")
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

    # 9. AI/기업 기사 허용 (generic AI 문맥은 제외)
    if any(contains_exact_term(raw_text, t) for t in ai_company_terms) and ('crypto' in raw_lower or '암호화폐' in raw_text or 'btc' in raw_lower or 'bitcoin' in raw_lower or 'xrp' in raw_lower or 'ripple' in raw_lower):
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

        if len(shared) >= 3:
            log(f"[정규토픽중복 제외] shared={shared}")
            return True

        if len(current) >= 2 and len(old) >= 2 and len(shared) >= min(len(current), len(old)) - 1:
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
        if re.search(r'' + re.escape(key) + r'', text, re.I) or key in text:
            entities.append(key)

    for kw in KOREAN_TAG_KEYWORDS:
        if kw in {'금', '은'}:
            continue
        if re.search(r'[가-힣]', kw):
            if kw in text:
                entities.append(kw)
        else:
            if re.search(r'' + re.escape(kw) + r'', text, re.I):
                entities.append(kw)

    for coin in PORTFOLIO_COINS:
        if re.search(r'' + re.escape(coin) + r'', text, re.I):
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

    particles = ['으로는','에서는','에게는','까지는','라고는','이라고','에서','에게','까지','으로','보다','처럼','라고','이며','이라','에는','에는','에','이','가','은','는','을','를','의','와','과','도','만','로']
    for p in particles:
        text = re.sub(rf'(#[가-힣A-Za-z0-9]+){p}(?=[\s,\.\!\?]|$)', rf'\1 {p}', text)

    # 정말 깨진 해시태그만 수동 복구
    text = text.replace('#미 국', '#미국')
    text = text.replace('#비트 코 인', '#비트코인')
    text = text.replace('#이더 리 움', '#이더리움')
    text = text.replace('#시 바 이 누', '#시바이누')
    text = text.replace('#신 시 아 루 미 스', '#신시아루미스')
    text = text.replace('#마이클#세일러', '#마이클세일러')
    text = text.replace('#브래드#갈링하우스', '#브래드갈링하우스')
    text = text.replace('#토비아스#아드리안', '#토비아스아드리안')
    text = text.replace('#아이 엠 뱅 크', '#아이엠뱅크')
    text = text.replace('#한 국 예 탁 결 제 원', '#한국예탁결제원')
    text = text.replace('#삼 성 S D S', '#삼성SDS')
    text = text.replace('#원 화', '#원화')
    text = text.replace('#솔 라 나', '#솔라나')
    text = text.replace('#블 랙 스 톤', '#블랙스톤')
    text = text.replace('#미 시 간', '#미시간')
    text = text.replace('#페 이 워 드', '#페이워드')
    text = text.replace('#에 타 나', '#에타나')
    text = text.replace('#오 하 이 오', '#오하이오')
    text = text.replace('#데 이 비 드 슈 워 츠', '#데이비드슈워츠')
    text = text.replace('#비 트 스 탬 프', '#비트스탬프')
    text = text.replace('#거 래 량', '#거래량')
    text = text.replace('#요아힘#나겔', '#요아힘나겔')
    text = text.replace('#찰스#호스킨슨', '#찰스호스킨슨')
    text = text.replace('#휴고#필리온', '#휴고필리온')
    text = text.replace('#사토시#나카모토', '#사토시나카모토')
    text = text.replace('#테라#울프', '#테라울프')
    text = text.replace('#스위스#중앙은행', '#스위스중앙은행')
    text = text.replace('#부 탄', '#부탄')
    text = text.replace('#규 제', '#규제')
    text = text.replace('#아이 엠 뱅 크', '#아이엠뱅크')
    text = text.replace('#카 이 아', '#카이아')
    text = text.replace('#싱 가 포 르', '#싱가포르')
    text = text.replace('#걸 프 은 행', '#걸프은행')
    text = text.replace('#스 탠 다 드 차 타 드', '#스탠다드차타드')
    text = text.replace('#디 지 털 자 산 기 본 법', '#디지털자산기본법')
    text = text.replace('#총 선', '#총선')
    text = text.replace('#삼성 S D S', '#삼성SDS')
    text = text.replace('#비트코인에', '#비트코인 에')
    text = text.replace('#이더리움에', '#이더리움 에')
    text = text.replace('#연준의', '#연준 의')
    text = text.replace('#규제된', '#규제 된')

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
        '[]',
        '전문 계정',
        '리서치 계정',
        '가상자산 전문 계정',
        '언폴디드',
        'Unfolded'
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
    text = re.sub(r'\b\d{1,2}일\s+가상자산\s+전문\s+계정\s+언폴디드\s*\(Unfolded\)\s*는?', '', text, flags=re.I)
    text = re.sub(r'\b가상자산\s+전문\s+계정\s+언폴디드\s*\(Unfolded\)\s*는?', '', text, flags=re.I)
    text = re.sub(r'\b언폴디드\s*\(Unfolded\)\s*는?', '', text, flags=re.I)
    text = re.sub(r'\bUnfolded\s*는?', '', text, flags=re.I)
    text = re.sub(r'\b전문\s+계정\b', '', text, flags=re.I)

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
		'#IMF', '#TobiasAdrian', '#RWA', '#GENIUSAct','#Oracle','#Coinone', '#Korea', '#Japan', '#BankOfJapan', '#BankOfKorea',
'#IMF', '#ABA', '#RWA', '#CBDC',
'#MonicaLong', '#ODL', '#FedNow', '#Fedwire',
'#AndrewBailey', '#HyunSongShin',
'#Metaplanet', '#Upbit',
'#BradGarlinghouse', '#CLARITY', '#CLARITYAct',
'#PeterSchiff', '#Gold', '#Silver',
'#CharlesSchwab', '#Oracle',
'#JeffPark', '#ProCap', '#TeraWulf', '#Switzerland', '#SwissNationalBank', '#Revolut', '#GoMining', '#ECB', '#JoachimNagel', '#ASIC', '#XRPLFoundation', '#SpaceX', '#Anthropic', '#Sandlin', '#XRPL',
'#iMBank', '#BTQ', '#Kaia', '#SamsungSDS', '#STO', '#Solana', '#wXRP', '#Blackstone', '#Michigan', '#Payward', '#Etana', '#Ohio', '#DavidSchwartz', '#Hut8', '#FalconX', '#Bitstamp', '#TransactionVolume',
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
- 캠페인, 이벤트, 콘퍼런스 일정, 경품, UI 오류, 앱 표시 오류, 소프트웨어 버전 업데이트, 인사개편 단순 공지성 기사처럼 보이면 빈 문자열만 반환할 것
- 각 문장은 짧게 작성
- 한 문장이 끝날 때마다 반드시 한 줄 띄울 것
- 전체 길이는 120자 안팎으로 유지
- 불필요한 배경 설명 금지
- 문장 끝은 텔레그램 축약형으로 정리할 것 (예: 밝혔다→밝힘, 전했다→전함, 설명했다→설명함)
- 고유명사는 가능한 한 한국어 표기를 우선 사용하고, 한국어 표기가 어색하면 원문을 유지할 것
- 특별한 경우가 아니면 불릿 사용 금지
- 너무 딱딱한 기사체보다, 빠르게 읽히는 텔레그램 뉴스 톤으로 작성
- 직역투 금지
- 기사에 없는 내용은 추측해서 추가 금지
- 매체명, first appeared on, sponsor 문구 제거
- 트위터/X 계정명, 전문 계정, 리서치 계정, 날짜 출처 언급은 제거
- 문장은 너무 길지 않게 끊기
- 출력은 요약문만 작성
- 마지막 해시태그 줄, 출처, 링크 문구는 작성하지 말 것
- 사람 이름, 국가명, 브랜드명, 코인명은 중간 띄어쓰기 없이 자연스럽게 작성
- 해시태그 내부 단어를 분리하지 말 것
- 본문에는 해시태그를 넣지 말 것
- 아래 표현은 절대 쓰지 말 것:
  하락세, 약세, 급락, 반등 실패, 상승으로 이어지지 못함, 강세 전환 신호 없음, 불확실, 이유, 전망, 크로스오버
- 가격 차트 해설 기사나 기술적 분석 기사처럼 보이면 빈 문자열만 반환할 것
- 인물명, 기관명, 국가명, 법안명은 기사에 있으면 요약문 본문에 가능한 한 직접 1회 포함할 것
- 예: Michael Barr, GENIUS Act, Australia, Hong Kong, HKMA, HSBC, Standard Chartered

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
        if ratio >= 0.80:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    # 시그니처가 너무 짧으면 중복판단 안 함
    if len(signature.split('|')) < 2:
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
        if ratio >= 0.86:
            log(f"[시그니처 유사도 중복] {signature} <> {old_sig} / {ratio:.2f}")
            return True

    return False


def format_summary_for_telegram(text: str, max_sentences: int = 3, max_chars: int = 180) -> str:
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

    text = re.sub(r'\s+', ' ', text).strip()
    return text
	
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
    summary = format_summary_for_telegram(summary, max_sentences=3, max_chars=180)
    summary = summary.replace('자동뉴스', '').strip()
    summary = summary.replace('다음 기사는', '').strip()
    summary = summary.replace('뉴스레터', '').strip()

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


# ---------------------------------------------------------------------------
# Crypto Telegram hardening layer
# ---------------------------------------------------------------------------
# 위쪽의 기존 함수와 데이터는 그대로 두고, 아래에서 핵심 함수만 재정의한다.
# Python은 나중에 정의된 함수를 사용하므로 main() 이전에 두면 기존 호출부를
# 크게 흔들지 않고 필터/요약/태그/중복 정책만 교체할 수 있다.

TAG_PARTICLES = [
    '으로는', '에서는', '에게는', '까지는', '이라고', '라고는',
    '에서', '에게', '까지', '으로', '보다', '처럼', '라고',
    '이며', '이라', '에는', '에', '이', '가', '은', '는',
    '을', '를', '의', '와', '과', '도', '만', '로',
]

STRICT_ALLOWED_ASSETS = [
    'bitcoin', 'btc', '비트코인',
    'ethereum', 'eth', '이더리움',
    'xrp', 'ripple', 'xrpl', 'xrp ledger', '리플',
    'xlm', 'stellar', '스텔라',
    'ada', 'cardano', '에이다',
    'trx', 'tron', '트론',
    'bnb', 'bch', 'bitcoin cash', '비트코인캐시',
    'shib', 'shiba inu', '시바이누',
    'etc', 'flr', 'flare', '플레어',
    'athena', 'ena', 'ethena', '에테나',
    'usdc', 'usdt', 'stablecoin', '스테이블코인',
]

STRICT_CRYPTO_CONTEXT = [
    'crypto', 'cryptocurrency', 'digital asset', 'virtual asset',
    'blockchain', 'token', 'tokenization', 'custody', 'wallet',
    'exchange', 'defi', 'rwa', 'staking', 'etf', 'spot etf',
    'sec', 'cftc', 'occ', 'stablecoin', 'market structure bill',
    'clarity act', 'genius act', '암호화폐', '가상자산', '디지털자산',
    '블록체인', '토큰', '토큰화', '수탁', '지갑', '거래소',
    '디파이', '스테이블코인', '현물 ETF', '시장구조법안',
    '클래리티법안', '지니어스법안',
]

STRICT_POLICY_CONTEXT = [
    'regulation', 'regulatory', 'regulated', 'bill', 'law', 'act',
    'policy', 'approval', 'hearing', 'senate', 'house', 'committee',
    'license', 'legislation', 'lawsuit', '규제', '법안', '입법',
    '정책', '승인', '청문회', '상원', '하원', '위원회', '라이선스', '소송',
]

STRICT_BLOCK_PATTERNS = [
    r'\bprice prediction\b', r'\bprice analysis\b', r'\btechnical analysis\b',
    r'\bforecast\b', r'\bchart\b', r'\bsupport\b', r'\bresistance\b',
    r'\bbullish\b', r'\bbearish\b', r'\bgolden cross\b', r'\bdeath cross\b',
    r'\bcandlestick\b', r'\bbollinger\b', r'\btarget price\b',
    r'\bwhat[’\']?s next\b', r'\bwhat to expect\b', r'\btop\s+\d+\b',
    r'\bpresale\b', r'\bpre-sale\b', r'\bairdrop\b', r'\bgiveaway\b',
    r'\bsponsored\b', r'\bpress release\b', r'\bguest post\b',
    r'\bnewsletter\b', r'\bprize pool\b', r'\bcampaign\b',
    r'\bconference\b', r'\bevent\b', r'\bversion update\b',
    r'가격\s*분석', r'기술적\s*분석', r'차트\s*분석', r'지지선',
    r'저항선', r'목표가', r'데드크로스', r'골든크로스',
    r'급등', r'급락', r'청산', r'매수\s*기회', r'프리세일',
    r'에어드롭', r'스폰서', r'보도자료', r'경품', r'이벤트',
    r'콘퍼런스', r'컨퍼런스', r'버전\s*업데이트', r'앱\s*표시\s*오류',
]

TERM_NORMALIZATION_OVERRIDES = {
    'Market Structure Bill': '시장구조법안',
    'market structure bill': '시장구조법안',
    'CLARITY Act': '시장구조법안',
    'Clarity Act': '시장구조법안',
    'clarity act': '시장구조법안',
    'GENIUS Act': '지니어스법안',
    'Genius Act': '지니어스법안',
    'genius act': '지니어스법안',
    'Stablecoin': '스테이블코인',
    'stablecoin': '스테이블코인',
    'Tokenization': '토큰화',
    'tokenization': '토큰화',
    'Custody': '수탁',
    'custody': '수탁',
    'regulated': '규제',
    'Regulated': '규제',
    'digital asset': '디지털자산',
    'Digital Asset': '디지털자산',
    'digital assets': '디지털자산',
    'Digital Assets': '디지털자산',
}

GENERIC_TAG_BLOCKLIST = {
    '규제된', 'Act', 'Government', '정부', 'Crypto', 'crypto',
    '금융', '암호화폐', '현물', '매수', '거래량', 'CEO',
}


def _contains_any_term(text: str, terms: list[str]) -> bool:
    return any(contains_exact_term(text, term) for term in terms)


def _contains_any_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def _is_gold_silver_context(text: str) -> bool:
    low = (text or '').lower()
    terms = [
        'gold', 'silver', 'digital gold', 'xaut', 'world gold council',
        '금 가격', '은 가격', '디지털 금', '디지털금', '세계금협회',
    ]
    return any(contains_exact_term(low, term.lower()) for term in terms)


def _normalize_entity_name(entity: str, context: str = '') -> str:
    raw = (entity or '').strip()
    name = entity_korean_name(raw)
    name = TERM_NORMALIZATION_OVERRIDES.get(name, name)
    name = name.replace(' ', '')

    if name == '규제된':
        name = '규제'
    if name in {'Gold', '금', 'Silver', '은'} and not _is_gold_silver_context(context):
        return ''
    if name in GENERIC_TAG_BLOCKLIST:
        return ''
    return name


def normalize_inline_hashtag_spacing(text: str) -> str:
    text = text or ''
    text = re.sub(r'#+', '#', text)
    text = re.sub(r'#\s+', '#', text)
    text = text.replace('#규제된', '#규제 된')

    for particle in sorted(TAG_PARTICLES, key=len, reverse=True):
        text = re.sub(
            rf'(#[A-Za-z0-9가-힣]+){particle}(?=[\s,\.\!\?\)\]\}}]|$)',
            rf'\1 {particle}',
            text,
        )

    if not _is_gold_silver_context(text):
        text = re.sub(r'#(금|은)(?=[\s,\.\!\?]|$)', r'\1', text)

    text = re.sub(r'\s+([,\.\!\?])', r'\1', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
    title = story.get('title', '') or ''
    desc = story.get('desc', '') or ''
    url = (story.get('url', '') or '').lower()
    raw_text = f'{title} {desc}'.strip()
    raw_lower = raw_text.lower()

    if not raw_text:
        return False

    if 'tokenpost.kr/news/tech/' in url:
        log(f"[기술일반 제외] {title}")
        return False

    if _contains_any_pattern(raw_lower, STRICT_BLOCK_PATTERNS):
        log(f"[하드차단] {title}")
        return False

    for neg in NEGATIVE_KEYWORDS:
        if neg and neg.lower() in raw_lower:
            log(f"[NEGATIVE 제외] {title} / {neg}")
            return False

    if (
        contains_bad_signal(raw_text)
        or contains_bad_topic(raw_text)
        or is_chart_or_price_article(raw_text)
        or is_corporate_treasury_sale_article(raw_text)
        or is_wallet_balance_metric_article(raw_text)
        or is_conference_opinion_article(raw_text)
        or is_security_incident_article(raw_text)
    ):
        log(f"[부적합주제 제외] {title}")
        return False

    has_allowed_asset = _contains_any_term(raw_lower, STRICT_ALLOWED_ASSETS)
    has_crypto_context = _contains_any_term(raw_lower, STRICT_CRYPTO_CONTEXT)
    has_policy_context = _contains_any_term(raw_lower, STRICT_POLICY_CONTEXT)

    if contains_non_portfolio_asset(raw_text) and not has_allowed_asset:
        log(f"[포폴외코인 제외] {title}")
        return False

    if contains_stock_context(raw_text) and not (has_allowed_asset or has_crypto_context):
        log(f"[주식기사 제외] {title}")
        return False

    # 순수 거시/정치/금융 기사는 암호화폐 연결이 명확할 때만 통과시킨다.
    if not (has_allowed_asset or has_crypto_context):
        log(f"[암호화폐맥락없음 제외] {title}")
        return False

    if has_allowed_asset:
        log(f"[허용자산 통과] {title}")
        return True

    if has_crypto_context and has_policy_context:
        log(f"[가상자산정책 통과] {title}")
        return True

    if is_xrp_narrative_article(raw_text) or is_payment_adoption_article(raw_text) or is_exchange_mna_article(raw_text):
        log(f"[채택/서사 통과] {title}")
        return True

    log(f"[필터미통과] {title}")
    return False


def fix_translation_terms(text: str) -> str:
    text = text or ''
    for src, dst in sorted(TERM_NORMALIZATION_OVERRIDES.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(re.escape(src), dst, text, flags=re.I)

    for src, dst in sorted(MANUAL_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        if src in {'Gold', 'Silver', '금', '은'} and not _is_gold_silver_context(text):
            continue
        text = re.sub(re.escape(src), dst, text)

    replacements = {
        '규제된': '규제',
        '클래리티법': '시장구조법안',
        '클래리티법안': '시장구조법안',
        '지니어스법': '지니어스법안',
        '스테이블 코인': '스테이블코인',
        '디지털 자산': '디지털자산',
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return cleanup_text(text)


def inject_entity_hashtags(summary: str, entities: list[str]) -> tuple[str, list[str]]:
    text = fix_translation_terms(summary or '')
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
        context = f'{text} {ent}'

        if ent_upper in PORTFOLIO_COINS or ent_upper in CRYPTO_ACRONYMS:
            korean_name = coin_inline_map.get(ent_upper, ent_upper)
            if f'#{ent_upper}' not in final_tags:
                final_tags.append(f'#{ent_upper}')
            if korean_name and korean_name not in {'USDC', 'USDT'} and f'#{korean_name}' not in final_tags:
                final_tags.append(f'#{korean_name}')
            tag_name = korean_name
        else:
            tag_name = _normalize_entity_name(ent, context)
            if not tag_name:
                continue
            tag = f'#{tag_name}'
            if tag not in final_tags:
                final_tags.append(tag)

        tag_text = f'#{tag_name}'
        if tag_text in text:
            continue

        bases = []
        for base in [tag_name, entity_korean_name(ent), ent, ent_upper]:
            base = (base or '').strip()
            if base and base not in bases:
                bases.append(base)

        replaced = False
        for base in sorted(bases, key=len, reverse=True):
            for particle in sorted(TAG_PARTICLES, key=len, reverse=True):
                new_text, count = re.subn(re.escape(base + particle), f'{tag_text} {particle}', text, count=1)
                if count:
                    text = new_text
                    replaced = True
                    break
            if replaced:
                break

        if not replaced:
            for base in sorted(bases, key=len, reverse=True):
                new_text, count = re.subn(rf'(?<![#A-Za-z0-9가-힣]){re.escape(base)}(?![A-Za-z0-9가-힣])', tag_text, text, count=1)
                if count:
                    text = new_text
                    break

    return normalize_inline_hashtag_spacing(text), filter_final_tags(final_tags)


def fix_broken_inline_hashtags(text: str) -> str:
    text = normalize_inline_hashtag_spacing(text)
    repairs = {
        '#미 국': '#미국',
        '#비트 코 인': '#비트코인',
        '#이더 리 움': '#이더리움',
        '#부 탄': '#부탄',
        '#규 제': '#규제',
        '#시장 구조 법안': '#시장구조법안',
        '#지니어스 법안': '#지니어스법안',
        '#스테이블 코인': '#스테이블코인',
        '#디지털 자산': '#디지털자산',
    }
    for src, dst in repairs.items():
        text = text.replace(src, dst)
    return normalize_inline_hashtag_spacing(text)


def remove_duplicate_inline_hashtags(text: str) -> str:
    seen = set()

    def repl(match):
        tag = match.group(0)
        key = tag.lower()
        if key in seen:
            return tag[1:]
        seen.add(key)
        return tag

    text = re.sub(r'#[A-Za-z0-9가-힣]+', repl, text or '')
    return normalize_inline_hashtag_spacing(text)


def rewrite_summary_with_gemini(title: str, article_text: str, fallback_text: str = "") -> str:
    source_text = (article_text or fallback_text or title or '').strip()
    if not source_text or not GEMINI_API_KEY:
        return ''

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""
너는 텔레그램 암호화폐 뉴스 채널 편집자다.

아래 기사가 암호화폐, 디지털자산, 블록체인, 스테이블코인, ETF, 수탁, 거래소, 관련 규제/법안/소송과 직접 관련 없으면 빈 문자열만 반환하라.

작성 규칙:
- 한국어 2~3문장으로만 작성
- 문장마다 줄바꿈을 유지
- 짧고 또렷한 텔레그램 뉴스 스타일
- 과장, 추측, 전망성 표현 금지
- 직역투 금지
- 기사에 없는 내용 추가 금지
- 매체명, 출처성 문구, sponsor, first appeared on, 계정명 제거
- 가격 예측, 차트 분석, 기술적 분석, 프리세일, 경품, 이벤트, 콘퍼런스, 앱 오류, 버전 업데이트면 빈 문자열만 반환
- 본문에 해시태그를 직접 쓰지 말 것
- 축약형 사용: 밝힘, 전함, 설명함, 추진함, 통과함, 승인함
- 고유명사는 아래 번역어를 우선 적용
  Market Structure Bill/CLARITY Act=시장구조법안
  GENIUS Act=지니어스법안
  stablecoin=스테이블코인
  tokenization=토큰화
  custody=수탁
  regulated=규제
- 금/은은 Gold/Silver 금속 문맥에서만 금, 은으로 번역

제목:
{title}

본문:
{source_text[:12000]}
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
        text = re.sub(r'[ \t]+', ' ', text.replace('\r\n', '\n').replace('\r', '\n'))
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        log_gemini_cost(title, prompt, text)
        return text

    except Exception as e:
        log(f"Gemini 요약 실패: {e}")
        return ""


def build_canonical_topic_key(story: dict) -> str:
    text = normalize_for_duplicate(f"{story.get('title', '')} {story.get('desc', '')}")
    parts = []

    maps = {
        'asset_btc': ['bitcoin', 'btc', '비트코인'],
        'asset_eth': ['ethereum', 'eth', '이더리움'],
        'asset_xrp': ['xrp', 'ripple', 'xrpl', 'xrp ledger', '리플'],
        'asset_usdc': ['usdc'],
        'asset_usdt': ['usdt', 'tether', '테더'],
        'topic_stablecoin': ['stablecoin', '스테이블코인'],
        'topic_etf': ['etf', '현물 etf'],
        'topic_custody': ['custody', '수탁'],
        'topic_tokenization': ['tokenization', '토큰화'],
        'topic_market_structure': ['market structure bill', 'clarity act', '시장구조법안', '클래리티법안'],
        'topic_genius': ['genius act', '지니어스법안', '지니어스법'],
        'topic_regulation': ['regulation', 'regulatory', 'regulated', '규제'],
        'topic_lawsuit': ['lawsuit', '소송'],
        'org_sec': ['sec'],
        'org_cftc': ['cftc'],
        'org_occ': ['occ'],
        'org_fed': ['fed', 'federal reserve', '연준'],
        'org_treasury': ['treasury', '재무부'],
        'geo_us': ['united states', 'us', 'u s', 'america', '미국'],
        'geo_korea': ['korea', 'south korea', '한국'],
        'geo_hongkong': ['hong kong', '홍콩'],
        'geo_japan': ['japan', '일본'],
    }

    for key, terms in maps.items():
        if any(contains_exact_term(text, term) for term in terms):
            parts.append(key)

    action_map = {
        'act_approval': ['approval', 'approve', 'approved', '승인'],
        'act_pass': ['pass', 'passed', 'passes', '통과'],
        'act_launch': ['launch', 'launched', '출시'],
        'act_delay': ['delay', 'delayed', '지연'],
        'act_comment': ['comment', 'public comment', '의견 수렴'],
        'act_buy': ['buy', 'bought', 'acquire', 'acquired', '매수', '매입'],
        'act_support': ['support', 'supports', '지지'],
    }

    for key, terms in action_map.items():
        if any(contains_exact_term(text, term) for term in terms):
            parts.append(key)

    parts = sorted(set(parts))
    if len(parts) < 3:
        return ''
    return ' | '.join(parts)


def build_story_signature(story: dict) -> str:
    text = normalize_for_duplicate(f"{story.get('title', '')} {story.get('desc', '')}")
    tags = set()

    signature_map = {
        'asset_btc': ['btc', 'bitcoin', '비트코인'],
        'asset_eth': ['eth', 'ethereum', '이더리움'],
        'asset_xrp': ['xrp', 'ripple', 'xrpl', 'xrp ledger', '리플'],
        'asset_usdc': ['usdc'],
        'asset_usdt': ['usdt', 'tether', '테더'],
        'asset_bch': ['bch', 'bitcoin cash', '비트코인캐시'],
        'asset_shib': ['shib', 'shiba inu', '시바이누'],
        'topic_stablecoin': ['stablecoin', '스테이블코인'],
        'topic_etf': ['etf'],
        'topic_bill': ['bill', 'law', 'act', '법안'],
        'topic_market_structure': ['market structure bill', 'clarity act', '시장구조법안'],
        'topic_genius': ['genius act', '지니어스법안'],
        'topic_regulation': ['regulation', 'regulated', '규제'],
        'topic_custody': ['custody', '수탁'],
        'topic_tokenization': ['tokenization', '토큰화'],
        'org_sec': ['sec'],
        'org_cftc': ['cftc'],
        'org_occ': ['occ'],
        'org_fed': ['fed', 'federal reserve', '연준'],
        'org_treasury': ['treasury', '재무부'],
        'org_coinbase': ['coinbase', '코인베이스'],
        'org_ripple': ['ripple', '리플'],
        'act_approval': ['approval', 'approve', 'approved', '승인'],
        'act_pass': ['pass', 'passed', 'passes', '통과'],
        'act_launch': ['launch', 'launched', '출시'],
        'act_buy': ['buy', 'bought', 'acquire', 'acquired', '매수', '매입'],
        'act_comment': ['comment', 'public comment', '의견 수렴'],
    }

    for key, terms in signature_map.items():
        if any(contains_exact_term(text, term) for term in terms):
            tags.add(key)

    return ' | '.join(sorted(tags))


def _signature_parts(signature: str) -> set[str]:
    return {x.strip() for x in (signature or '').split('|') if x.strip()}


def _has_non_asset_signal(parts: set[str]) -> bool:
    return any(part.startswith(('topic_', 'act_', 'org_')) for part in parts)


def _is_semantic_signature_candidate(parts: set[str]) -> bool:
    if len(parts) < 2:
        return False
    if not _has_non_asset_signal(parts):
        return False
    return True


def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = normalize_for_duplicate(story.get('title', ''))
    signature = build_story_signature(story)
    canonical_key = build_canonical_topic_key(story)

    for old_title in seen_titles:
        ratio = SequenceMatcher(None, title, old_title).ratio()
        if ratio >= 0.74:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    current_sig = _signature_parts(signature)
    current_canonical = _signature_parts(canonical_key)

    if not _is_semantic_signature_candidate(current_sig) and not _is_semantic_signature_candidate(current_canonical):
        log(f"[의미중복검사 생략] 짧은/자산전용 시그니처: {signature or canonical_key}")
        return False

    for old_sig in seen_signatures:
        old = _signature_parts(old_sig)
        if not old:
            continue
        if not _is_semantic_signature_candidate(old):
            continue

        shared_sig = current_sig & old
        shared_canonical = current_canonical & old
        shared_sig_non_asset = {x for x in shared_sig if x.startswith(('topic_', 'act_', 'org_'))}
        shared_canonical_non_asset = {x for x in shared_canonical if x.startswith(('topic_', 'act_', 'org_'))}

        if len(shared_canonical) >= 3 and shared_canonical_non_asset:
            log(f"[정규토픽 중복] {canonical_key} <> {old_sig}")
            return True
        if len(shared_sig) >= 3 and shared_sig_non_asset and len(shared_sig) / max(len(current_sig), 1) >= 0.60:
            log(f"[시그니처 교집합 중복] {signature} <> {old_sig}")
            return True
        if (
            _is_semantic_signature_candidate(current_sig)
            and _is_semantic_signature_candidate(old)
            and shared_sig_non_asset
            and signature
            and SequenceMatcher(None, signature, old_sig).ratio() >= 0.80
        ):
            log(f"[시그니처 유사도 중복] {signature} <> {old_sig}")
            return True

    return False


def format_summary_for_telegram(text: str, max_sentences: int = 3, max_chars: int = 220) -> str:
    text = fix_translation_terms(text or '')
    text = normalize_inline_hashtag_spacing(text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'(에 따르면|보도에 따르면|외신은|매체는|기사는)\s*', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    endings = {
        '밝혔다': '밝힘',
        '전했다': '전함',
        '설명했다': '설명함',
        '추진했다': '추진함',
        '승인했다': '승인함',
        '통과했다': '통과함',
        '발표했다': '발표함',
    }
    for src, dst in endings.items():
        text = text.replace(src, dst)

    sentences = re.split(
        r'(?<=[.!?])\s+|(?<=음)\s+|(?<=됨)\s+|(?<=함)\s+|(?<=밝힘)\s+|(?<=전함)\s+|(?<=설명함)\s+|(?<=추진함)\s+',
        text,
    )
    sentences = [normalize_inline_hashtag_spacing(s.strip(' .')) for s in sentences if s.strip()]

    picked = []
    total = 0
    for sentence in sentences:
        if len(picked) >= max_sentences:
            break
        if picked and total + len(sentence) > max_chars:
            break
        picked.append(sentence)
        total += len(sentence)

    if not picked and text:
        picked = [text[:max_chars].rstrip()]

    return '\n\n'.join(picked).strip()


def _safe_replace_terms(text: str, replacements: dict[str, str]) -> str:
    for src, dst in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        if not src:
            continue
        if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 .&()-]*', src):
            pattern = rf'(?<![A-Za-z0-9]){re.escape(src)}(?![A-Za-z0-9])'
            text = re.sub(pattern, dst, text, flags=re.I)
        else:
            text = text.replace(src, dst)
    return text


def _fix_xrp_and_ton_artifacts(text: str) -> str:
    text = text or ''
    text = re.sub(r'엑스\s*RP', 'XRP', text, flags=re.I)
    text = re.sub(r'엑스\s*알\s*피', 'XRP', text)
    text = re.sub(r'엑스\s*RPL', 'XRPL', text, flags=re.I)
    text = re.sub(r'엑스\s*알\s*피\s*엘', 'XRPL', text)
    text = text.replace('마일스#톤', '마일스톤')
    text = text.replace('마일스 #톤', '마일스톤')
    text = text.replace('#톤코인', '톤코인')
    text = re.sub(r'(?<![A-Za-z0-9가-힣])엑스(?![A-Za-z0-9가-힣])', 'X', text)
    return text


def _looks_like_ton_context(text: str) -> bool:
    low = (text or '').lower()
    return any(contains_exact_term(low, term) for term in [
        'ton', 'toncoin', 'the open network', 'telegram', '톤코인', '텔레그램', '오픈네트워크'
    ])


def _is_inline_tag_candidate(name: str, context: str) -> bool:
    if not name or name in GENERIC_TAG_BLOCKLIST:
        return False
    if name in {'TON', '톤', '톤코인'} and not _looks_like_ton_context(context):
        return False
    if name in {'X', '엑스'}:
        return False
    allowed = {
        '비트코인', '이더리움', '리플', 'XRP', 'BTC', 'ETH', 'USDT', 'USDC',
        'ETF', 'SEC', 'CFTC', 'OCC', '시장구조법안', '지니어스법안',
        '스테이블코인', '토큰화', '수탁', '규제', '미국', '한국', '홍콩', '일본',
        '리플재단', 'XRPL재단',
    }
    return name in allowed


def fix_translation_terms(text: str) -> str:
    text = text or ''
    text = _fix_xrp_and_ton_artifacts(text)

    safe_manual = {
        src: dst
        for src, dst in MANUAL_TRANSLATIONS.items()
        if src not in {'X', '엑스', 'TON', 'Toncoin', '톤', '톤코인'}
    }
    safe_manual.update(TERM_NORMALIZATION_OVERRIDES)
    safe_manual.update({
        '401(k)': '401k',
        'U.S. Department of Labor': '미국 노동부',
        'US Department of Labor': '미국 노동부',
        'Department of Labor': '노동부',
        'Labor Department': '노동부',
        'Bitcoin Cash': '비트코인캐시',
        'Shiba Inu': '시바이누',
        'shiba inu': '시바이누',
        'XRP Ledger Foundation': 'XRPL재단',
        'XRP Foundation': 'XRP재단',
        'XRP Ledger': 'XRPL',
    })

    text = _safe_replace_terms(text, safe_manual)

    if _looks_like_ton_context(text):
        text = _safe_replace_terms(text, {'Toncoin': '톤코인', 'TON': 'TON'})

    replacements = {
        '엑스 RP': 'XRP',
        '엑스RP': 'XRP',
        '엑스알피': 'XRP',
        '엑스 RPL': 'XRPL',
        '엑스RPL': 'XRPL',
        '규제된': '규제',
        '클래리티법': '시장구조법안',
        '클래리티법안': '시장구조법안',
        '지니어스법': '지니어스법안',
        '스테이블 코인': '스테이블코인',
        '디지털 자산': '디지털자산',
        '마일스#톤': '마일스톤',
        '마일스 #톤': '마일스톤',
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    text = _fix_xrp_and_ton_artifacts(text)
    return cleanup_text(text)


def normalize_inline_hashtag_spacing(text: str) -> str:
    text = _fix_xrp_and_ton_artifacts(text or '')
    text = re.sub(r'#+', '#', text)
    text = re.sub(r'#\s+', '#', text)
    text = text.replace('#규제된', '#규제 된')

    for particle in sorted(TAG_PARTICLES, key=len, reverse=True):
        text = re.sub(
            rf'(#[A-Za-z0-9가-힣]+){particle}(?=[\s,\.\!\?\)\]\}}]|$)',
            rf'\1 {particle}',
            text,
        )

    if not _looks_like_ton_context(text):
        text = re.sub(r'#(TON|톤|톤코인)(?=[\s,\.\!\?]|$)', lambda m: m.group(1), text)
    if not _is_gold_silver_context(text):
        text = re.sub(r'#(금|은)(?=[\s,\.\!\?]|$)', r'\1', text)

    text = text.replace('마일스 #톤', '마일스톤')
    text = text.replace('마일스#톤', '마일스톤')
    text = re.sub(r'\s+([,\.\!\?])', r'\1', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def inject_entity_hashtags(summary: str, entities: list[str]) -> tuple[str, list[str]]:
    text = fix_translation_terms(summary or '')
    final_tags = []
    inline_count = 0
    max_inline_tags = 2

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

    priority_entities = []
    for ent in entities:
        ent_upper = ent.upper()
        normalized = _normalize_entity_name(ent, f'{text} {ent}')
        if ent_upper in {'BTC', 'ETH', 'XRP', 'USDT', 'USDC'} or normalized in {'비트코인', '이더리움', '리플', 'XRP'}:
            priority = 0
        elif ent_upper in {'ETF', 'SEC', 'CFTC', 'OCC'}:
            priority = 1
        elif normalized in {'시장구조법안', '지니어스법안', '스테이블코인', '수탁', '토큰화', '규제'}:
            priority = 2
        else:
            priority = 9
        priority_entities.append((priority, -len(ent), ent))

    for _, __, ent in sorted(priority_entities):
        ent_upper = ent.upper()
        context = f'{text} {ent}'

        if ent_upper in PORTFOLIO_COINS or ent_upper in CRYPTO_ACRONYMS:
            tag_name = coin_inline_map.get(ent_upper, ent_upper)
            if f'#{ent_upper}' not in final_tags:
                final_tags.append(f'#{ent_upper}')
        else:
            tag_name = _normalize_entity_name(ent, context)
            if not tag_name:
                continue
            tag = f'#{tag_name}'
            if tag not in final_tags:
                final_tags.append(tag)

        if inline_count >= max_inline_tags or not _is_inline_tag_candidate(tag_name, context):
            continue

        tag_text = f'#{tag_name}'
        if tag_text in text:
            continue

        bases = []
        for base in [tag_name, entity_korean_name(ent), ent, ent_upper]:
            base = _fix_xrp_and_ton_artifacts((base or '').strip())
            if base and base not in bases:
                bases.append(base)

        replaced = False
        for base in sorted(bases, key=len, reverse=True):
            if base in {'TON', '톤', '톤코인'} and not _looks_like_ton_context(text):
                continue
            for particle in sorted(TAG_PARTICLES, key=len, reverse=True):
                new_text, count = re.subn(re.escape(base + particle), f'{tag_text} {particle}', text, count=1)
                if count:
                    text = new_text
                    inline_count += 1
                    replaced = True
                    break
            if replaced:
                break

        if not replaced:
            for base in sorted(bases, key=len, reverse=True):
                if base in {'TON', '톤', '톤코인'} and not _looks_like_ton_context(text):
                    continue
                new_text, count = re.subn(
                    rf'(?<![#A-Za-z0-9가-힣]){re.escape(base)}(?![A-Za-z0-9가-힣])',
                    tag_text,
                    text,
                    count=1,
                )
                if count:
                    text = new_text
                    inline_count += 1
                    break

    return normalize_inline_hashtag_spacing(text), filter_final_tags(final_tags)


def fix_broken_inline_hashtags(text: str) -> str:
    text = normalize_inline_hashtag_spacing(text)
    repairs = {
        '#미 국': '#미국',
        '#비트 코 인': '#비트코인',
        '#이더 리 움': '#이더리움',
        '#부 탄': '#부탄',
        '#규 제': '#규제',
        '#시장 구조 법안': '#시장구조법안',
        '#지니어스 법안': '#지니어스법안',
        '#스테이블 코인': '#스테이블코인',
        '#디지털 자산': '#디지털자산',
        '#엑스 RP': '#XRP',
        '#엑스RP': '#XRP',
        '#엑스알피': '#XRP',
        '#톤코인': '톤코인',
    }
    for src, dst in repairs.items():
        text = text.replace(src, dst)
    return normalize_inline_hashtag_spacing(text)


def remove_duplicate_inline_hashtags(text: str) -> str:
    seen = set()

    def repl(match):
        tag = match.group(0)
        key = tag.lower()
        if key in seen:
            return tag[1:]
        seen.add(key)
        return tag

    text = re.sub(r'#[A-Za-z0-9가-힣]+', repl, text or '')
    return normalize_inline_hashtag_spacing(text)


def finalize_summary_ending(text: str) -> str:
    text = _fix_xrp_and_ton_artifacts(text or '')
    text = re.sub(r'좋은\s*덩어리$', '', text)
    text = re.sub(r'([가-힣]+)음고 말함$', r'\1음', text)
    text = re.sub(r'([가-힣]+)고 말함$', r'\1', text)

    ending_fixes = {
        '능가': '능가함',
        '증가': '증가함',
        '합류': '합류함',
        '달성': '달성함',
        '책임': '책임 범위를 명확히 하는 내용임',
        '비판': '비판함',
        '추가': '추가함',
        '확대': '확대함',
    }
    for src, dst in ending_fixes.items():
        text = re.sub(rf'{src}$', dst, text)

    text = re.sub(r'문제가 아니\.$', '문제가 아님', text)
    text = re.sub(r'아니\.$', '아님', text)
    text = re.sub(r'될 것\.$', '될 것임', text)
    text = re.sub(r'계획이\.$', '계획임', text)
    text = re.sub(r'보인다\.$', '보임', text)
    text = re.sub(r'전망이다\.$', '전망임', text)
    text = re.sub(r'했음고', '했고', text)
    text = re.sub(r'했음는', '했다는', text)
    return normalize_inline_hashtag_spacing(re.sub(r'\s+', ' ', text).strip())


def _drop_incomplete_summary_lines(text: str) -> str:
    lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
    clean = []
    incomplete_endings = (
        '가', '이', '은', '는', '을', '를', '의', '에', '에서', '로', '으로',
        '주요 자산을 능가', '책임'
    )
    for line in lines:
        fixed = finalize_summary_ending(line)
        if fixed.endswith(incomplete_endings):
            continue
        clean.append(fixed)
    return '\n\n'.join(clean)


def format_summary_for_telegram(text: str, max_sentences: int = 3, max_chars: int = 260) -> str:
    text = fix_translation_terms(text or '')
    text = normalize_inline_hashtag_spacing(text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'(에 따르면|보도에 따르면|외신은|매체는|기사는)\s*', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    endings = {
        '밝혔다': '밝힘',
        '전했다': '전함',
        '설명했다': '설명함',
        '추진했다': '추진함',
        '승인했다': '승인함',
        '통과했다': '통과함',
        '발표했다': '발표함',
        '합류했다': '합류함',
        '달성했다': '달성함',
        '비판했다': '비판함',
    }
    for src, dst in endings.items():
        text = text.replace(src, dst)

    text = _drop_incomplete_summary_lines(text)
    sentences = re.split(
        r'(?<=[.!?])\s+|(?<=음)\s+|(?<=됨)\s+|(?<=함)\s+|(?<=밝힘)\s+|(?<=전함)\s+|(?<=설명함)\s+|(?<=추진함)\s+',
        text,
    )
    sentences = [finalize_summary_ending(s.strip(' .')) for s in sentences if s.strip()]

    picked = []
    total = 0
    for sentence in sentences:
        if len(picked) >= max_sentences:
            break
        if picked and total + len(sentence) > max_chars:
            continue
        picked.append(sentence)
        total += len(sentence)

    if not picked and text:
        picked = [finalize_summary_ending(text[:max_chars].rstrip())]

    return '\n\n'.join(picked).strip()


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


if __name__ == '__main__':
    main()
