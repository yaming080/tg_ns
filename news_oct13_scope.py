"""New intake examples; source, duplicate, portfolio and image gates still apply."""
from datetime import datetime, timezone
import re

ENABLED_AT = datetime(2026, 10, 13, 8, 30, tzinfo=timezone.utc)


def scope(story):
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'presale|airdrop|giveaway|referral|sponsored|rumou?r|price prediction|price target|technical analysis|RSI|MACD|프리세일|에어드롭|협찬|소문|목표가|차트.?분석|뉴스.?브리핑'):
        return ''
    crypto = r'crypto|digital.asset|암호화폐|가상자산|디지털.?자산'
    if (has(r'Binance|Coinbase|Kraken|바이낸스|코인베이스|크라켄')
            and has(r'stocks?|equities|주식|증권|투자상품')
            and has(r'launch|offer|explor|consider|plan|출시|검토|추진|거래.{0,12}지원')):
        return '거래소의 주식·증권 상품 사업 계획'
    if (has(r'\bUSDT\b|\bUSDC\b|stablecoins?|스테이블코인')
            and has(r'payment|settlement|송금|결제|정산')
            and has(r'service|network|서비스|네트워크')
            and has(r'unveil|launch|introduc|공개|출시|도입|발표')):
        return '스테이블코인 결제망의 새 서비스 발표'
    if (has(r'bank|은행|스베르방크|스베르뱅크|스베르뱅') and has(crypto)
            and has(r'exchange|trading|거래|교환')
            and has(r'approv|licen[cs]|register|승인|허가|등록')):
        return '은행의 암호화폐 거래 인가·등록'
    if (has(crypto) and has(r'election|candidate|선거|후보')
            and has(r'donat|spend|funding|contribut|기부|지원|투입|후원')
            and has(r'\d.{0,20}(?:million|billion|dollar|달러)|\$\s*\d')):
        return '암호화폐 업계의 구체적 선거자금 공개'
    if (has(r'Singapore Gulf Bank|싱가포르\s*걸프\s*은행') and has(r'(?<![A-Za-z])BNY(?![A-Za-z])|뉴욕멜론')
            and has(r'USD|dollar|달러') and has(r'payment|transfer|결제|송금')
            and has(r'partner|expand|tap|join|제휴|확대|도입|참여')):
        return '디지털자산 연계 은행의 달러 결제 인프라 제휴'
    if (has(r'CFTC|SEC|상품선물거래위원회|증권거래위원회')
            and has(r'Caroline Pham|캐롤라인\s*(?:팸|팜)|위원장|chair')
            and has(r'regulat|규제|감독|기존\s*법률')
            and has(r'says?|said|발언|밝|충분|can')):
        return '전현직 감독당국 책임자의 새 규제 발언'
    return ''


GUIDANCE = '''
2026-10-13 운영자 보완(선별 예외이며 자동 게시 승인이 아님):
거래소의 주식·증권 투자상품 출시 검토, 은행의 암호화폐 거래 인가·등록, 스테이블코인 결제망 새 서비스 발표, 암호화폐 업계의 구체적인 선거자금 집행 공개를 지정 코인 없이도 심사한다. 검토는 출시 확정이 아니며 승인·등록 대상 업무를 구분한다. 기부금 집행 보도를 선거운동 권유로 바꾸지 않는다.
싱가포르 걸프은행과 BNY의 24시간 달러 결제 제휴도 심사한다. 원문이 확인한 적격 고객·계좌·참여 은행 조건을 유지하며 달러 송금을 온체인·USDT 송금으로 바꾸지 않는다. 과거 크라켄 제휴를 새 계약으로 쓰지 않는다.
A7처럼 제재 대상 결제망의 서비스 발표도 사실 보도 대상이다. 제재 대상이라는 조건은 반드시 보존하고 합법성·안전성·사용 권유를 덧붙이지 않는다. 제재 회피 방법을 설명하지 않는다.
암호화폐 기업의 합병 완료·상장 예정과 실제 첫 거래 개시는 서로 다른 단계다. 에버노스 같은 지정 자산 보유 기업의 실제 상장 첫 거래와 새 임원 영입·운용전략이 원문으로 확인되면 심사한다. 첫 거래 당시 5% 같은 주가 수치는 부차 사실로 가능하지만 단순 일일 등락·목표가·반복 보유량 기사는 계속 제외한다. 이미 게시한 상장 첫날 사건은 다른 매체라도 재게시하지 않는다.
금융기관 토큰화 상품의 구체적인 목표 일정과 일정 변경도 심사한다. 모건스탠리의 2027년 1분기 지원 목표를 출시 확정으로 쓰지 말고, 시장 규모 전망은 에이미 올든버그의 의견으로 귀속한다. 연구소 출범·지갑 개발 배경을 새 발표로 혼동하지 않는다. 본문에서 확인되지 않는 일정은 제목만으로 추가하지 않는다.
캐롤라인 팸 전 CFTC 위원장 대행처럼 전직 인사의 발언은 현재 직책과 구별한다. 규제 가능하다는 의견을 새 규제 시행·법안 통과로 바꾸지 않는다. 본문은 핵심 발언과 중요한 조건을 짧게 쓰고 인명·기관명은 한국어 표기와 본문 태그를 사용한다. CFTC·SEC·USDT·V2·REVO 식별자는 유지할 수 있다.
중복, 포트폴리오 자체 악재, 비포트폴리오 플랫폼 중심 기사, 광고·원문 부족·부적합 이미지 차단은 유지한다.
'''
