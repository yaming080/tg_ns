"""Bounded candidate categories; never bypass source, duplicate or image review."""
import re
from datetime import datetime, timezone

ENABLED_AT = datetime(2026, 11, 15, 8, 30, tzinfo=timezone.utc)


def excluded_claim(title):
    return bool(re.search(r'Simpsons|심슨', title, re.I)
                and re.search(r'XRP|리플', title, re.I)
                and re.search(r'blackout|predict|prophe|\$\s*50|정전|예언|폭등', title, re.I))


def scope(story):
    title = str(story.get('title', '') or '') if isinstance(story, dict) else ''
    has = lambda p: bool(re.search(p, title, re.I))
    if excluded_claim(title) or has(r'price prediction|price target|technical analysis|sponsored|giveaway|referral|presale|rumou?r|목표가|협찬|루머|차트.?분석'):
        return ''
    if (has(r'Coinbase|코인베이스|Brian Armstrong|브라이언\s*암스트롱')
            and has(r'AiFi|agentic finance|AI.{0,20}(?:finance|account|금융|계좌)|에이전트.{0,12}금융')
            and has(r'CEO|Armstrong|암스트롱|대표|최고경영자|build|구축')):
        return '거래소 경영진의 AI 금융 계좌 사업 발표'
    if (has(r'XRP\s*Ledger|XRPL|XRP레저|XRP\s*레저') and has(r'AI|에이전트|agent')
            and has(r'services?|merchant|서비스|가맹|제공업체')):
        return 'XRPL AI 서비스 구매·결제 지원 현황 발표'
    if (has(r'Adam Back|아담\s*백|Blockstream|블록스트림')
            and has(r'custody|cold.?stor|cold.?wallet|security|수탁|콜드|보안')
            and has(r'launch|makes case|says?|advocat|강조|보관|출시|발표')):
        return '실명 개발자의 오프라인 수탁 보안 발표'
    if (has(r'가상자산|암호화폐|crypto') and has(r'기업부설연구소|corporate research')
            and has(r'정부|과기|과학기술|government|ministry')
            and has(r'인정|개정|입법예고|recogn|amend')):
        return '가상자산 기업 연구개발 지원 제도 개정'
    if (has(r'중앙은행|central bank|national bank|\bCNB\b|국채|sovereign')
            and has(r'블록체인|토큰화|blockchain|tokeni[sz]')
            and has(r'채권|어음|bond|note') and has(r'발행|판매|출시|issue|issuance|sale|launch')):
        return '중앙은행·국가의 토큰화 채권 발행·시험'
    if (has(r'태국|Thailand|Thai') and has(r'crypto|가상자산|암호화폐')
            and has(r'fraud|pyramid|Ponzi|사기|다단계') and has(r'arrest|체포')):
        return '가상자산 투자사기 용의자 체포'
    if (has(r'Nubank|누뱅크') and has(r'banking|bank|은행')
            and has(r'licen[cs]e|approv|인가|승인')):
        return '디지털 금융 플랫폼의 은행업 인가'
    return ''


def guidance(title):
    if not scope({'title': title}):
        return ''
    return '''
11월 15일 편집 보완: 위 범주는 원문 심사 대상이며 코인명 부재·짧은 기사·명사형 종결만으로 제외하지 않는다. ~함·~음·~임도 주체와 행동이 분명하면 완결된 뉴스 문장이다. 필요한 사실을 쉬운 말로 전달하고 부차적인 Repo·MPC 약어 나열은 생략할 수 있다. 시험/정식 서비스, 추진/시행과 필수 조건은 반드시 보존한다. 원문 부족을 추측으로 채우지 않는다.
코인베이스 경영진의 AiFi 계좌 사업 우선순위와 AI 에이전트 금융 발언을 심사한다. 2030년 3조~5조달러는 인용된 거래 규모 전망이지 현재 시장 규모·코인베이스 매출·확정 성과가 아니다. 투자 권유·코인 목표가로 바꾸지 않는다.
XRPL AI Hub의 실사용 서비스 구매·결제 지원 현황을 실명 운영사 발표로 심사한다. 서비스 수·가맹업체 수는 발표의 범위를 설명할 수 있으나 같은 카탈로그 숫자만 다시 바뀐 후속은 중복이다. 운영사·결제 기능·이용 범위가 확인되어야 한다. 5,410개 서비스는 5,410개 기업이나 사용자 수가 아니며 193개 가맹업체와 구별한다. Monid의 10월 20일 합류는 과거 배경이지 오늘 새 제휴가 아니다. XRP 가격 효과를 만들지 않는다.
아담 백의 새 수탁 시스템 발표·인터뷰는 비트코인 프로토콜 취약점 보도와 구분한다. 블록스트림·탈레스의 기관용 오프라인 거래 승인 시스템과 발언자에게 귀속한 보안 의견을 심사한다. 원문에 없는 실제 해킹 발생·완전한 안전 보장을 쓰지 않는다. 일반 보관법 재소개와 같은 인터뷰의 반복은 제외한다.
가상자산 기업부설연구소 인정은 시행령 개정안 입법예고와 조건부 연구개발 지원이다. 시행 완료·모든 거래소 자동 세액공제로 바꾸지 않는다.
중앙은행의 블록체인 채권은 시험 발행과 거래·결제 실증도 심사한다. 체코 CNB Lab 시험을 일반 투자자 대상 정식 판매나 국채 전면 전환으로 쓰지 않는다. 카자흐스탄 중앙은행 어음 판매와 향후 국채 출시 목표는 다른 단계이며 X는 직접 수집하지 않는다.
태국 가상자산 투자사기 용의자 체포는 코인 네트워크 자체 악재가 아니다. 혐의·추정 피해 규모·체포일·송환 진행을 유지하고 유죄나 송환 완료로 쓰지 않는다. 기존 사건의 피해액 변화만이면 제외한다.
누뱅크의 은행업 인가는 암호화폐 서비스를 운영하는 디지털 금융사의 제도권 사업 변화로 심사한다. 인수 승인에 따른 브라질 은행업 인가를 신규 암호화폐 인가·새 코인 출시·미국 은행 인가로 바꾸지 않는다.
심슨 정전·XRP 50달러 예언 주장은 사실 뉴스로 허용하지 않는다. 원문이 반박한 주장을 확인된 예언으로 뒤집지 않는다. 모든 유형에 원문 사실검사·사건 중복·관련 이미지 검증을 계속 적용한다.
'''
