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
