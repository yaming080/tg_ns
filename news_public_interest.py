"""Narrow public-interest intake from the operator's October 12 examples."""
from datetime import datetime, timezone
import re

# Admit newly published candidates, never release the old rejected backlog.
ENABLED_AT = datetime(2026, 10, 11, 18, 0, tzinfo=timezone.utc)


def public_interest_scope(story):
    title = str(story.get('title', '') or '')
    has = lambda pattern: bool(re.search(pattern, title, re.I))
    if has(r'presale|giveaway|sponsored|referral|price prediction|price target|technical analysis|'
           r'프리세일|에어드롭|추천인|협찬|목표가|차트\s*분석|뉴스\s*모음|피해\s*집계|annual.{0,20}(?:loss|report)'):
        return ''
    crypto = r'crypto|cryptocurrency|digital.asset|Bitcoin|BTC|암호화폐|가상자산|디지털\s*자산|비트코인'
    # A named wallet impersonation on a specific distribution surface is a
    # current consumer-protection incident, not a generic security tutorial.
    wallet = r'Ledger|레저|렛저|Trezor|트레저|MetaMask|메타마스크|Phantom|팬텀|하드웨어\s*지갑|hardware\s+wallet'
    if (has(wallet) and has(r'fake|impersonat|phishing|사칭|가짜|피싱')
            and has(r'Google|구글|search|검색|광고|ads?\b|앱\s*스토어|app\s*store')
            and has(r'appear|surface|found|discover|warn|expos|top|노출|상단|발견|확인|적발|경고')):
        return '지갑 사칭 사이트·검색 광고의 구체적 노출'
    if (has(crypto) and has(r'arrest(?:s|ed)?|detain(?:s|ed)?|indict\w*|prosecut\w*|체포|검거|구속|기소')
            and has(r'launder|fraud|scam|crime|police|authorit|검찰|경찰|당국|자금\s*세탁|사기|범죄')):
        return '암호화폐 범죄의 체포·기소 등 새 수사 단계'
    government = r'Russia|러시아|정부|에너지부|ministry|government'
    if (has(government) and has(r'min(?:ing|ers?)|채굴')
            and has(r'power|electricity|grid|전력|전기|계통')
            and has(r'new.{0,25}(?:rules?|regulat)|decree|resolution|introduc\w*.{0,30}rules|새(?:로운)?\s*규정|규정.{0,15}(?:도입|시행)|법령|정부령|개정')
            and not has(r'profitability|수익성|전기\s*요금\s*비교|price\s+forecast')):
        return '정부의 채굴 전력 연결·공급 규정 변경'
    government = r'China|Chinese|\b中\b|중국|국무원|공산당|정부|government|State Council|ministry'
    if (has(government) and has(r'blockchain|블록체인')
            and has(r'national|nationwide|국가|전국') and has(r'network|infrastructure|네트워크|인프라')
            and has(r'plan|build|calls?\s+for|announc|approv|launch|구축|추진|발표|승인|착수')):
        return '국가 블록체인 인프라의 공식 추진 계획'
    return ''


GUIDANCE = '''
2026-10-12 운영자 보완: 다음 공익·정책 기사는 지정 코인 티커가 없어도 심사한다. 위의 단순 경고·질문형 제목 제외 기준에 대한 제한적 예외이며 자동 게시 승인이 아니다.
1. 실명 지갑을 사칭한 가짜 사이트·앱이 검색 광고/상단에 실제 노출된 구체적 새 사례. 일반 예방 수칙, 과거 경고 재탕, 피해액만 늘어난 후속 집계, 하드웨어 기기 자체 취약점 경고는 계속 제외한다. 렛저(레저) 사칭 사이트와 크립토빌리스 기기 유통·고객 자산 유출 사건을 구별한다. 원문이 연관성을 확인하지 않았으면 같은 사고라고 단정하지 않는다. 악성 사이트 주소나 복구 문구 입력 방법을 본문에 재현하지 않는다.
2. 암호화폐 자금세탁·사기 수사의 실제 체포·기소·압수 등 새 단계. 범죄 발생일이 오래됐어도 새 수사 행위가 있으면 그 행위를 심사한다. 기사 작성일을 체포일로 바꾸지 말고, 혐의·수사 대상액을 유죄·확정 피해액으로 바꾸지 않는다. 일본 예시의 580,000달러는 전체 수사 대상 추정액이며 최초 체포 관련 거래액과 구별한다.
3. 정부가 채굴 시설의 전력 연결·공급 조건을 실제로 도입·개정한 법령. 제목이 질문형이어도 원문에 새 법령·당국 발표가 있으면 심사한다. 전망이나 기존 전기료 해설만 있으면 제외한다. 러시아 사례는 신규·미완료 연결 신청의 공급 우선순위 변경이며 모든 가동 채굴장의 즉시 단전이나 비트코인 체인 중단이 아니다. 이미 시행된 규정을 최신 기사라는 이유로 재탕하지 않는다.
4. 정부·공식 기관의 국가 블록체인 인프라 구축 계획 발표. 특정 코인 이름 없이도 심사하되 민간 홍보·논평과 구별한다. 추진 계획을 구축 완료·암호화폐 거래 허용으로 확대하지 않는다. 중국 사례에서 구체적 일정과 운영 방식이 미공개라면 그 불확실성을 보존한다.
이 네 유형에도 중복 사건·과거 기사·홍보·원문 불충분·부적합 이미지 차단은 그대로 적용한다. 매체·언어·제목이 달라도 같은 사건이면 새로 게시하지 않는다. 관련 기업 이름만 같고 사고 유형·당국 조치가 다르면 원문과 게시 이력으로 비교한다.
포트폴리오 자체의 취약점·해킹 등 악재 및 수이 등 비포트폴리오 플랫폼 중심 기사 제외는 유지한다. 일반 국가 채굴 규정과 제3자 사칭·범죄 수사를 BTC라는 단어만으로 비트코인 네트워크 자체 악재와 혼동하지 않는다.
'''
