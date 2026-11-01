"""Candidate intake only; never approve summaries, duplicates or publication."""
from datetime import datetime, timezone
import re

# Do not replay previously rejected stories when the intake gate is widened.
ENABLED_AT = datetime(2026, 11, 1, 15, 11, tzinfo=timezone.utc)


def industry_intake_scope(story):
    if not isinstance(story, dict):
        return ''
    title = str(story.get('title', '') or '')
    has = lambda pattern: bool(re.search(pattern, title, re.I))
    if has(r'price prediction|price target|technical analysis|sponsored|giveaway|referral|'
           r'week in review|weekly recap|roundup|how to|could|might|rumou?r|'
           r'목표가|가격.?전망|차트.?분석|협찬|경품|추천인|주간.?정리|사용법|루머|가능성'):
        return ''
    crypto = r'crypto|digital.asset|stablecoin|tokeniz|암호화폐|가상자산|디지털.?자산|스테이블코인|토큰화'
    authority = r'government|ministry|regulator|commission|central bank|FCA|SEC|CFTC|FBI|'
    authority += r'China|Chinese|정부|당국|위원회|중앙은행|공산당|국무원|검찰|경찰'
    enforcement = r'brib|corruption|launder|enforcement|crackdown|단속|부패|뇌물|자금.?세탁'
    action = r'announc|publish|issu(?:e|es|ed)|adopt|approv|introduc|calls? for|'
    action += r'발표|공개|도입|시행|채택|명시|강화|승인'
    if has(crypto) and has(authority) and has(enforcement) and has(action):
        return '디지털자산 단속·감독의 새 공식 조치 후보'

    exchange = r'\b(?:Binance|Coinbase|Kraken|HTX|OKX|Bybit|Bitfinex|Upbit|Bithumb)\b|'
    exchange += r'바이낸스|코인베이스|크라켄|후오비|업비트|빗썸|암호화폐\s*거래소|가상자산\s*거래소|crypto\s+exchange'
    if has(exchange):
        service = r'withdrawals?|deposits?|출금|입금|입출금'
        restoration = r'reopen\w*|resum\w*|restor\w*|재개|복구'
        if has(service) and has(restoration):
            return '거래소 입출금 서비스의 실제 재개 후보'
        authority_action = r'FCA|SEC|CFTC|regulat|authorit|licen[cs]|settlement|당국|규제|인가|라이선스|합의'
        market_action = r'\bexits?\b|withdraws? from|ceases?|halt\w*|approv|obtain|grant|'
        market_action += r'철수|종료|중단|승인|획득'
        if has(authority_action) and has(market_action):
            return '거래소 규제 합의·시장 접근 변경 후보'

    institution = r'\bbanks?\b|asset manager|insurer|은행|자산운용|보험사|증권사'
    service = r'custody|settlement|payment|tokeniz|수탁|정산|결제|토큰화'
    concrete = r'launch|partner|agreement|pilot|trial|introduc|출시|제휴|협약|실증|시범|도입'
    if has(institution) and has(crypto) and has(service) and has(concrete):
        return '금융기관 디지털자산 서비스·실증 후보'
    return ''
