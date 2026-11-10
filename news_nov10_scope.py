"""Concrete events missed in Nov 9-10 feedback; candidate intake, not approval."""
import re
from datetime import datetime, timezone

ENABLED_AT = datetime(2026, 11, 10, 6, 50, tzinfo=timezone.utc)


def scope(story):
    if not isinstance(story, dict):
        return ''
    title = str(story.get('title', '') or '')
    has = lambda pattern: bool(re.search(pattern, title, re.I))
    if has(r'price prediction|price target|technical analysis|sponsored|giveaway|referral|presale|'
           r'rumou?r|roundup|weekly recap|목표가|차트.?분석|협찬|에어드롭|추천인|루머|뉴스.?브리핑|주간.?정리'):
        return ''
    if (has(r'\bHTX\b|후오비') and has(r'tokeni[sz]|토큰화')
            and has(r'stocks?|equities|주식') and has(r'launch|start|offer|roll.?out|출시|시작|개시|도입')):
        return '거래소의 토큰화 주식 서비스 개시'
    if (has(r'Coinbase|코인베이스') and has(r'\bOCC\b|통화감독청|national\s+trust|전국\s*신탁|연방\s*신탁')
            and has(r'charter|trust|인가|신탁') and has(r'approv|secur|wins?|takes effect|획득|승인|효력|발효')):
        return '거래소의 신탁은행 인가 단계 진행'
    if (has(r'Robinhood|로빈후드') and has(r'\bUK\b|United Kingdom|British|영국')
            and has(r'IPO|공모주') and has(r'opens?|brings?|launch|introduc|expand|도입|확대|개시|출시')):
        return '금융 플랫폼의 국가별 공모주 접근 서비스 도입'
    if (has(r'\bStrategy\b|MicroStrategy|스트[래레]티지|마이크로스트[래레]티지|Bitmine|비트마인')
            and has(r'Bitcoin|Ethereum|\bBTC\b|\bETH\b|비트코인|이더리움')
            and has(r'\b(?:buys?|bought|purchases?|purchased|acquires?|acquired)\b|매수|매입|매입한')
            and has(r'\d')
            and not has(r'\b(?:may|might|could|plans?|hints?|predicts?)\b.{0,30}\b(?:buy|purchase|acquire)\b|매입\s*(?:암시|계획|가능)|매수\s*(?:암시|계획|가능)')):
        return '실명 기업의 수량·금액이 있는 실제 BTC·ETH 매입'
    if (has(r'\bPNC\b|PNC은행') and has(r'USDC|stablecoin|스테이블코인')
            and has(r'payment|deposit|결제|입금')
            and has(r'test|pilot|launch|bring|takes?|expand|partner|convert|지원|시범|추진|협력|전환')):
        return '은행의 스테이블코인 결제·예금 전환 서비스'
    if (has(r'\bBullish\b|불리시') and has(r'Stacey Cunningham|Cunningham|스테이시\s*커닝햄|커닝햄')
            and has(r'president|chief|사장') and has(r'appoint|names?|hires?|선임|임명|영입')):
        return '암호화폐 거래소의 실명 경영진 선임'
    if (has(r'police|경찰|(?:^|\s)警') and has(r'seized|confiscat|압수')
            and has(r'crypto|digital.asset|암호화폐|가상자산')
            and has(r'Upbit|업비트') and has(r'custody|커스터디|보관')):
        return '수사기관 압수 디지털자산의 전문 수탁 전환'
    if (has(r'Trump|트럼프') and has(r'Iran|이란') and has(r'war|전쟁|종전|군사행동')
            and has(r'progress|진전') and has(r'says?|states?|밝|발언|["“]')):
        return '당사국 정상의 종전 협상 진행에 관한 새 발언'
    if (has(r'Elizabeth Warren|Warren|엘리자베스\s*워런|워런')
            and has(r'Senate Banking|상원\s*은행') and has(r'chair|위원장')
            and has(r'crypto|digital.asset|암호화폐|가상자산')
            and has(r'appoint|poised|takes?|assum|plans?|vows?|취임|예정|선임|추진')):
        return '상원 은행위원장 취임 일정과 디지털자산 감독 방향'
    return ''


def guidance(title):
    if not scope({'title': title}):
        return ''
    return '''
11월 10일 팀원 편집 보완: 아래 유형은 특정 코인명이 제목에 없더라도 새 사건의 후보로 심사한다. 원문 충분성·허용 범위·이미지·기존 게시 사건 중복 검증을 모두 통과해야 한다.
HTX의 토큰화 주식 거래, 로빈후드의 영국 IPO 접근 서비스는 거래·청약 서비스 도입이다. 고객의 주식 배정 보장·실물 주식 직접 소유·모든 국가 이용 가능으로 확대하지 않는다. 시범 운영과 정식 출시를 구분한다.
코인베이스 OCC 인가는 신청·조건부 승인·최종 승인·효력 발생을 구분하고 전국 신탁은행을 예금·대출이 가능한 일반 상업은행으로 바꾸지 않는다. PNC USDC 결제는 지원 고객·시범 여부와 달러 전환 조건을 보존한다.
스트래티지·비트마인의 실제 BTC·ETH 매입은 제목에 predicts·전망이 함께 있어도 매입 사실을 검토한다. 실제 거래와 개인 전망을 분리하고 매수 암시를 실행으로 쓰지 않는다. 매입 수량·금액·기간은 원문으로 확인하며 다른 매체 수치가 충돌하면 임의로 합치지 않는다. 기존 거래의 누적 보유량 수정·반올림 차이·재인용은 중복이며, 새 보고기간의 독립된 거래임이 입증된 경우에만 새 사건으로 판단한다.
불리시의 경영진 선임과 경찰 압수 가상자산의 업비트 커스터디 위탁은 인사·기관 수탁 사건이다. 배경의 NYSE 경력을 거래소 간 제휴로 바꾸지 않는다.
트럼프의 이란 종전 진전 발언은 당사자 평가이며 종전·협상 타결 확정이 아니다. 워런의 은행위원장 취임 예정과 규제 방향은 취임 완료·입법 통과와 구분한다. 지난 인사 전망을 같은 사실로 재보도한 경우 중복 제외한다.
협찬·홍보, 비포트폴리오 코인 사업, 포트폴리오 자체 악재 제외는 유지한다. 이 보완은 X 직접 수집을 추가하지 않으며 과거 미발행 기사 일괄 발송을 허용하지 않는다.
'''
