"""Bounded institutional statements and policy events from Nov 12 feedback."""
import re
from datetime import datetime, timezone

ENABLED_AT = datetime(2026, 11, 12, 12, 45, tzinfo=timezone.utc)


def scope(story):
    if not isinstance(story, dict):
        return ''
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'price prediction|price target|technical analysis|sponsored|giveaway|referral|presale|'
           r'rumou?r|weekly recap|목표가|차트.?분석|협찬|에어드롭|추천인|루머|주간.?정리'):
        return ''
    if (has(r'Ripple|리플') and has(r'on.?chain|tokeni[sz]|온체인|토큰화')
            and has(r'assets?|trillion|자산|조\s*달러')
            and has(r'says?|forecast|expects?|predict|2030|전망|발언|["“]')):
        return '리플 실명 관계자의 자산 온체인 전환 전망'
    if (has(r'Nomura|노무라|Laser\s*Digital|레이저\s*디지털')
            and has(r'crypto|digital.asset|Laser\s*Digital|레이저\s*디지털|암호화폐|가상자산')
            and has(r'sale|sell|divest|매각')
            and has(r'weigh|explor|consider|review|plan|검토|추진|계획')):
        return '금융그룹의 디지털자산 자회사 매각 검토'
    if (has(r'Texas|텍사스|지방정부|local government|cities|counties')
            and has(r'Bitcoin|crypto|비트코인|가상자산|암호화폐')
            and has(r'bill|법안') and has(r'invest|투자|보유')
            and has(r'allow|permit|introduc|file|발의|제출|허용')):
        return '지방정부 디지털자산 투자 허용 입법'
    if (has(r'Ripple|리플') and has(r'delet|remov|withdraw|삭제|철회|정정')
            and has(r'announcement|post|blog|Qivalis|게시물|블로그|발표|스테이블코인')):
        return '리플 공식 발표 게시물 삭제·정정 확인'
    if (has(r'South Korea|Korean|한국|금융위원회|금융위|\bFSC\b')
            and has(r'crypto|digital.asset|가상자산|암호화폐')
            and has(r'withdraw|출금') and has(r'freez|suspend|halt|동결|중단|정지')
            and has(r'permit|allow|no.action|허용|규정|제도|비조치')):
        return '해킹 의심 시 거래소 예방적 출금 중단 제도'
    if (has(r'디지털자산|가상자산|digital.asset') and has(r'기본법|basic act')
            and has(r'국회|의원|금융위|National Assembly|lawmaker')
            and has(r'입법|제출|추진|합의|규율|legislat|submit|advanc')):
        return '국회·금융당국의 디지털자산 기본법 추진 발언'
    if (has(r'Miami.?Dade|마이애미.?데이드|county|municipal|카운티|지자체')
            and has(r'Bitcoin|\bBTC\b|비트코인')
            and has(r'property.tax|tax.payment|재산세|세금')
            and has(r'accept|pay|start|begin|수용|납부|시작|도입')):
        return '지방정부의 비트코인 세금 납부 지원'
    if (has(r'CPMI|지급\s*및\s*시장인프라|신현송|Hyun\s*Song\s*Shin')
            and has(r'chair|의장|지급결제|payment')
            and has(r'appoint|elect|names?|선임|임명|룰\s*메이커')):
        return '국제 지급결제 기준 기구의 의장 선임'
    return ''


def guidance(title):
    if not scope({'title': title}):
        return ''
    return '''
11월 12일 팀원 편집 보완: 이 유형은 특정 코인명이 없어도 원문 검토 대상으로 삼는다. 원문 충분성·독립된 새 사실·사건 중복·이미지 검증을 모두 통과해야 게시한다.
리플 실명 관계자의 자산 온체인 전환 전망은 새 발언으로 검토한다. 발표 날짜·발언자 실명·직책을 원문으로 확인하고 수치·기한을 발언자의 전망으로 귀속한다. 자산 전체의 전망을 XRP 시가총액·가격·현재 유입 실적으로 바꾸지 않는다. 세미나 참석 자체나 익명 코인 목표가 전망은 제외한다.
노무라 등 금융그룹의 디지털자산 자회사 매각 검토는 기업 사업 재편 보도다. 취재 매체를 밝히고 검토·협상·확정 계약·완료를 구분한다. 매각 미확정이라는 조건을 삭제하거나 단순 불확실 표현만을 이유로 제외하지 않는다. 손실 배경은 자회사와 포트폴리오 프로토콜 자체 악재를 구분한다.
사용자가 지정한 리플의 공식 게시물 삭제·정정 보도는 포트폴리오 악재 일반 제외의 좁은 편집 예외다. 원 게시물과 삭제 사실의 근거를 확인하고 확인 수준을 보도에 귀속한다. Qivalis의 37개 은행 전체가 리플과 새 제휴한 것이 아니다. 기존 BBVA·DZ BANK 고객 관계를 신규 Qivalis 참여·인프라 공급·XRP 채택으로 바꾸지 않는다. 삭제 이유나 사기·취약점을 추측하지 않는다. 실제 프로토콜 취약점·해킹·지급불능 등 기존 악재 제외는 유지한다.
해킹 의심 시 예방적 입출금 중단 허용은 거래소 고객 보호 제도다. 확인된 해킹 발생과 구분하고, 비조치의견서 예정·발급·법 개정 완료를 혼동하지 않는다. 허용 조건과 대상이 핵심이며 모든 출금의 무기한 동결로 확대하지 않는다.
국회·금융당국의 디지털자산 기본법 추진 발언은 발언자의 새 입법 일정·조건·책임 규율 등 구체적 제안이 확인되면 심사한다. 단순 조속 추진 재확인·동일 정부안의 배경 보충은 중복이다. 국회 제출·의결·시행 완료로 바꾸지 않는다. 같은 법안이라는 이유만으로 독립된 새 단계나 구체적 새 제안을 자동 중복 처리하지 않는다.
지방정부 투자 허용 법안은 발의와 통과를 구별하고 한도·시행 조건을 보존한다. 동일 HB 815의 타 매체 보도는 중복이다. 비트코인 세금 납부는 납부자의 BTC 사용과 세무기관의 달러 수령을 구분하고 자동 환전·대상 지역·세목을 보존한다. 정부의 BTC 보유·매수로 바꾸지 않는다. X는 직접 수집하지 않는다.
CPMI 의장 선임은 국제 지급결제 기준 기구의 인사다. 임기·선임 주체·직책을 확인한다. 디지털통화 기준 논의 가능성만으로 XRP 채택·제휴·가격 상승을 추론하거나 본문에 XRP 태그·상승 이모지를 추가하지 않는다. 원문에 없는 토큰 연관성을 만들지 않는다.
협찬·비포트폴리오 체인 자체 사업 홍보와 이미 게시된 사건은 계속 제외한다. 본문 태그는 실제 등장하는 인물·기관·제도에 붙인다.
'''
