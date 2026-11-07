"""Bounded candidate intake from the Nov 8 team examples, not approval."""
import re
from datetime import datetime, timezone

ENABLED_AT = datetime(2026, 11, 7, 15, 42, tzinfo=timezone.utc)


def scope(story):
    if not isinstance(story, dict):
        return ''
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'price prediction|price target|technical analysis|sponsored|giveaway|referral|presale|'
           r'rumou?r|roundup|weekly recap|목표가|차트.?분석|협찬|에어드롭|추천인|루머|뉴스.?브리핑|주간.?정리'):
        return ''
    if (has(r'\bUS\b|U\.?S\.?\b|United States|미국|美')
            and has(r'midterm|election|중간선거|선거')
            and has(r'winners?|elected|당선자|당선인')
            and has(r'pro.crypto|crypto.friendly|친.{0,8}(?:암호화폐|가상자산|코인)|親.{0,8}(?:가상자산|암호화폐)')
            and has(r'classif|share|percent|\d+(?:\.\d+)?\s*%|분류|비중|비율')):
        return '미국 선거 당선자의 디지털자산 정책 성향 집계'
    institution = r'Ripple|BlackRock|Standard Chartered|DFSA|리플|블랙록|스탠다드차타드|두바이\s*금융서비스청'
    if (has(institution) and has(r'tokeni[sz]|토큰화') and has(r'report|white\s*paper|보고서|백서')
            and has(r'joins?|contribut|publish|releas|launch|참여|기여|발간|공개|발표')):
        return '기관·감독당국의 토큰화 보고서 발간·기여'
    if (has(r'Fidelity|피델리티') and has(r'Jurrien\s+Timmer|주리[엔안]\s*팀[머멜]|쥬리[엔안]\s*팀[머멜]')
            and has(r'Bitcoin|\bBTC\b|비트코인') and has(r'\bgold\b|금\s*(?:보다|과|대비|선호)|보다\s*금')
            and has(r'prefer|favou?r|explain|says?|선호|설명|평가|발언')):
        return '실명 금융기관 전문가의 비트코인·금 비교 견해'
    return ''


GUIDANCE = '''
11월 8일 팀원 편집 보완: 미국 선거 당선자의 친암호화폐 성향 집계는 정책 환경 보도다. 분류 기관·집계 시각·대상·분모와 비교 연도를 원문에서 확인하고, 개표 확정 범위를 보존한다. 분류 수치가 특정 법안 지지·통과 확정이나 시장 상승을 뜻하지 않는다. 여론조사와 실제 당선자 집계를 혼동하지 않는다.
리플·블랙록·스탠다드차타드·DFSA 등 실명 기관의 새 토큰화 백서 발간·기여도 구체적 사건으로 심사한다. 보고서 발표·참여와 실제 제휴·서비스 출시·XRP레저 채택은 별개다. 인프라 연결 가능성을 현재 도입·담보 사용 확정으로 바꾸지 않는다. 보고서 발간일과 후속 보도일을 구분하고 같은 보고서 재탕이나 기존 패널 참석만 있으면 제외한다.
피델리티 주리엔 팀머의 비트코인·금 비교에 관한 새 발언은 실명 기관 전문가 의견으로 심사한다. 상대적 가격 방어력과 주식시장 동조화 등 판단 근거와 한계를 보존하고, 개인 견해를 피델리티의 공식 매수·자산 배분 결정이나 보장 수익으로 바꾸지 않는다. 단순 시세 중계·익명 전망·차트 목표가 홍보는 계속 제외한다.
세 유형 모두 원문 충분성·실제 새 사실·동일 사건 중복·이미지 검증을 통과해야 한다. 과거 기사 재발송, 포트폴리오 자체 악재, 비포트폴리오 사업 홍보를 허용하는 예외가 아니다.
'''


def guidance(title):
    return GUIDANCE if scope({'title': title}) else ''
