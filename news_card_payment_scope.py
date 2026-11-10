"""Named card issuers' concrete stablecoin payment proposals, not launch claims."""
import re
from datetime import datetime, timezone

ENABLED_AT = datetime(2026, 11, 10, 8, 20, tzinfo=timezone.utc)


def scope(story):
    if not isinstance(story, dict):
        return ''
    title=str(story.get('title','') or '')
    has=lambda pattern:bool(re.search(pattern,title,re.I))
    if has(r'price prediction|price target|technical analysis|sponsored|giveaway|referral|presale|'
           r'루머|목표가|차트.?분석|협찬|추천인|에어드롭|주간.?정리'):
        return ''
    issuer=r'신한카드|KB\s*국민카드|하나카드|우리카드|롯데카드|삼성카드|현대카드|Shinhan\s+Card'
    return ('카드사의 스테이블코인 결제망 활용 제안' if
            has(issuer) and has(r'stablecoin|스테이블코인') and has(r'payment|settlement|결제|정산')
            and has(r'existing\s+card\s+(?:networks?|rails?)|기존\s*(?:신용)?\s*카드망|하이브리드|멀티레일')
            and has(r'propos|suggest|says?|could\s+use|활용|제안|검토|밝|["“]') else '')


def guidance(title):
    if not scope({'title':title}):
        return ''
    return '''
카드사의 구체적인 스테이블코인 결제망 활용 제안은 금융기관의 지급결제 설계 발언으로 검토한다. 발언자 실명·소속·직책, 발표 날짜와 구체적 기능을 원문에서 확인한다. 세미나 참석 자체나 막연한 산업 전망만 있으면 제외한다.
'기존 카드망을 활용할 수도 있다', '바람직하다'는 제안이다. 이를 서비스 출시·실증 완료·현재 결제 지원·확정 계획으로 바꾸지 않는다. 원문의 조건부 기능 설명은 '그렇게 구현할 경우 가능하다는 설명'으로 귀속한다. 기존 가맹점 수는 이미 스테이블코인을 받는 가맹점 수가 아니며 실제 사용자·채택 실적으로 쓰지 않는다.
새로운 구체적 결제 구상과 기존 발언의 재인용을 구분하고 같은 사건의 중복을 검사한다. 해당 제안만으로 특정 코인 채택·가격 상승·투자 호재를 추론하지 않는다. 협찬·추천인 광고, 비포트폴리오 체인 자체의 사업 홍보, 원문 부족은 계속 제외한다.
'''
