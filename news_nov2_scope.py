"""November 2 team feedback: candidate scope, never publication approval."""
from datetime import datetime, timezone
import re

# Freeze at the start of this change, not at process startup. No backlog replay.
ENABLED_AT = datetime(2026, 11, 2, 9, 40, tzinfo=timezone.utc)


def scope(story):
    if not isinstance(story, dict):
        return ''
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'price prediction|price target|technical analysis|sponsored|giveaway|referral|'
           r'presale|rumou?r|weekly recap|roundup|how to|목표가|차트.?분석|협찬|'
           r'프리세일|추천인|주간.?정리|루머|사용법|피해.?집계'):
        return ''
    crypto = r'crypto|digital.asset|blockchain|stablecoin|암호화폐|가상자산|디지털.?자산|블록체인|스테이블코인|코인'
    if (has(crypto) and has(r'tax|과세|공제')
            and has(r'bill|legislat|parliament|lawmaker|법안|국회|의원')
            and has(r'introduc|file|propos|pass|amend|발의|제출|통과|개정')):
        return '디지털자산 과세 법안의 새 발의·개정'
    actor = r'Trump|Elon Musk|White House|트럼프|(?:일론\s*)?머스크|백악관'
    election = r'midterm|election|Senate|Congress|중간선거|사전투표|상원|의회'
    if (has(actor) and has(election)
            and has(r'veto|endorse|support|urges?|says?|warns?|거부권|지지|요청|독재|[“"]')):
        return '실명 주요 인사의 선거·의회 권한 관련 새 발언'
    if (has(r'SWIFT|스위프트')
            and has(r'Tom\s+Alaerts|톰\s*알라에르츠|(?:former|전직).{0,20}(?:expert|전문가)|표준.{0,15}전문가')
            and has(r'interview|conversation|explains?|says?|ISO.?20022|인터뷰|대담|발언|설명')):
        return '금융 메시지 표준 실무자의 새 인터뷰'
    if (has(r'\bBTCPay\b|비티씨페이|비트코인\s*결제\s*(?:서버|처리업체)')
            and has(r'wallet|server|지갑|서버')
            and has(r'warn|shutdown|shut down|urges?|alerts?|경고|긴급|폐쇄|중단|촉구')
            and not has(r'annual|quarterly|totals?|losses rise|누적|연간|피해액.{0,12}증가')):
        return '제3자 결제 서버의 구체적 긴급 보안 공지'
    if (has(r'금융위|금융위원회|FSC|regulator')
            and has(r'exchange|거래소') and has(r'cold.?wallet|cold.?storage|콜드월렛')
            and has(r'convene|meeting|소집|회의|논의')):
        return '금융당국의 거래소 보관·보안 대응 회의'
    if (has(r'\bAWS\b|Amazon Web Services|아마존웹서비스|아마존\s*웹\s*서비스')
            and has(crypto) and has(r'exchange|거래소')
            and has(r'blueprint|architecture|design|설계안|아키텍처')
            and has(r'unveil|publish|release|공개|발표')):
        return '클라우드 사업자의 디지털자산 거래소 설계안 공개'
    if (has(r'China|Chinese|중국|공산당') and has(crypto)
            and has(r'corruption|brib|부패|뇌물')
            and has(r'resolution|calls? for|vows?|crackdown|결의안|결정문|촉구|명시|단속')):
        return '당국의 암호화폐 연계 부패 단속 조치'
    if (has(r'India|인도|RBI|FIU.?IND') and has(crypto)
            and has(r'cards?|카드') and has(r'probe|investigat|scrutini|review|조사|검토')):
        return '당국의 역외 암호화폐 카드 규정 준수 조사'
    if (has(r'\bCZ\b|Changpeng Zhao|창펑자오') and has(r'Binance|바이낸스')
            and has(r'users?|customers?|이용자|사용자|고객')
            and has(r'stay|stayed|remain|retention|머물|잔류|이탈')
            and has(r'says?|said|밝|발언|[“"]')):
        return '거래소 책임자의 이용자 신뢰·잔류 관련 새 발언'
    return ''


GUIDANCE = '''
2026-11-02 팀원 피드백에 따른 제한적 편집 예외(자동 게시 승인 아님):
코인 과세 유예·공제 법안의 새 발의는 특정 코인 이름 없이도 심사한다. 발의와 통과·시행을 구별하고 기간·공제액·대상을 원문대로 보존한다.
트럼프·머스크 등 실명 인사의 선거·의회 권한 관련 새 발언을 심사한다. '상대 당이 승리하면' 같은 조건을 보존한다. 독재 등 정치적 평가는 그 인물의 주장으로 귀속하며 봇의 사실 판단이나 지지 호소로 쓰지 않는다. 이전 발언 재탕·여론조사 숫자만 바뀐 기사는 제외한다.
SWIFT 표준 실무자의 새로운 실명 인터뷰는 금융 통합에 관한 설명·의견으로 심사한다. ISO 20022는 메시지 표준이며 특정 코인의 인증·은행 채택·가격 상승 보장이 아니다. 원문이 XRP의 실제 채택을 확인하지 않으면 XRP 호재·승인으로 확대하거나 강조 태그를 덧붙이지 않는다.
BTCPay 같은 제3자 결제 서버의 구체적인 긴급 중단 공지와 당국의 거래소 콜드월렛 회의는 이용자 보호·감독 조치로 심사한다. 이것을 비트코인 프로토콜 자체 결함과 혼동하지 않는다. 영향받는 운영자·지갑 종류·버전과 조사 중이라는 제한을 원문대로 보존한다. 모든 지갑이 위험하다고 일반화하거나 원문에 없는 대응 방법을 만들지 않는다. 하드웨어 지갑 자체 결함 제외와 포트폴리오 코인·발행사·네트워크 악재 제외는 유지한다.
AWS 등 사업자가 공개한 암호화폐 거래소 설계안은 기술 인프라 소식으로 심사하되 설계안을 실제 거래소 출시나 보안 보장으로 바꾸지 않는다.
중국의 암호화폐 연계 부패 단속 결의와 인도의 역외 암호화폐 카드 조사는 국가의 새 감독 조치로 심사한다. 조사·촉구를 위법 확정이나 새 전면 금지로 바꾸지 않는다.
CZ의 거래소 이용자 잔류·신뢰 관련 새 발언은 발언자에게 귀속한다. 2.1% 자금 순유출과 98% 이용자 잔류 주장을 같은 통계로 계산하거나 객관적으로 입증된 수치라고 쓰지 않는다. 단순 수급 수치 갱신·같은 발언 반복은 제외한다.
모든 유형에서 원문 확보·새 정보·중복·포트폴리오 제외·이미지 검사를 유지한다. 원문이 불충분하면 보류하며, 팀원 게시문은 중복 비교 근거일 뿐 새 기사의 사실 확인을 대체하지 않는다.
'''


def guidance(title):
    return GUIDANCE if scope({'title': title}) else ''
