"""False exclusions found by comparing live logs with approved team examples."""
import re
from datetime import datetime, timezone

ENABLED_AT = datetime(2026, 11, 26, 16, 55, tzinfo=timezone.utc)


def scope(story):
    if not isinstance(story, dict):
        return ''
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'rumou?r|price target|price prediction|giveaway|presale|referral|목표가|루머|추천인'):
        return ''
    categories = (
        ((r'TRON|트론', r'Backpack|백팩', r'wallet|월렛|지갑', r'integrat|통합|연동'), '팀원 허용 지갑 통합 발표'),
        ((r'Ethena|에테나', r'Stellar|스텔라', r'USDe|sUSDe', r'live|launch|출시|도입'), '스테이블코인 새 체인 출시'),
        ((r'UBS', r'Chainlink|체인링크', r'tokeniz|tokenis|토큰화', r'notes|구조화|증권', r'automat|자동화'), '은행 토큰화 구조화 증권 자동화'),
        ((r'H100', r'buyback|buy.back|자사주', r'Bitcoin|비트코인|BTC'), '실명 기업 자사주 매입 의결 계획'),
        ((r'Two Prime|TwoPrime|투프라임', r'loan|lend|대출', r'collateral|담보', r'add|expand|추가|확대'), '기관 대출 담보 조건 확대'),
        ((r'Durov|두로프', r'Telegram|텔레그램', r'wallet|지갑', r'report|announc|발표|공개', r'new|신규|새|활성화'), '텔레그램 CEO 새 지갑 보급 발표'),
        ((r'Russia|Moscow|러시아|모스크바', r'XRP', r'news|exchange|소식|거래소', r'analyst|분석가|발표|launch'), '러시아 거래 제도 관련 원문 확인'),
        ((r'Maxine Waters|맥신.?워터스|Elizabeth Warren|엘리자베스.?워런|하원|상원|Congress|Senat', r'crypto|digital.asset|암호화폐|가상자산|디지털자산', r'probe|investigat|bill|regulat|조사|수사|법안|규제', r'vow|plan|introduc|propos|추진|계획|발의|촉구'), '입법부 디지털자산 감독·입법 방침'),
    )
    for patterns, label in categories:
        if all(has(p) for p in patterns):
            return label
    return ''


def approved_release(story):
    # The user explicitly supplied this sponsored publisher article as an
    # acceptable announcement. This is not permission for arbitrary adverts.
    return scope(story) == '팀원 허용 지갑 통합 발표'


def guidance(title):
    label = scope({'title': title})
    if not label:
        return ''
    notes = {
        '팀원 허용 지갑 통합 발표': '트론·백팩 월렛의 실제 통합·지원 기능은 팀원 허용 사례다. 매체의 협찬/보도자료 표시만으로 제외하지 않는다. 트론 측 발표로 귀속하고 독립 검증 사실이나 투자 권유로 바꾸지 않는다. 추천인·할인코드·경품 유도는 여전히 제외한다.',
        '스테이블코인 새 체인 출시': '에테나 USDe·sUSDe의 스텔라 출시를 심사한다. USDe는 현금 1:1 보유 방식의 일반 스테이블코인과 다르므로 원문에 맞게 합성 달러로 표현한다. 기존 출시의 물량 증가만 재탕하지 않는다.',
        '은행 토큰화 구조화 증권 자동화': 'UBS의 구조화 증권 발행·사후관리 자동화 시험은 은행 금융 인프라 소식이다. 체인링크가 기술 제공자로 등장한다는 이유로 LINK 코인 자체 홍보로 판단하지 않는다. 시험과 실제 상용 전환은 구별한다.',
        '실명 기업 자사주 매입 의결 계획': 'H100의 주주 의결·매입 승인 계획은 주가 등락 기사가 아니다. 의결일·매입 상한과 자금 출처가 원문에 있을 때 요약하고 계획을 매입 완료로 바꾸지 않는다.',
        '기관 대출 담보 조건 확대': '투프라임 기관 대출의 새 담보·만기·수탁 조건은 상품 조건 변화로 심사한다. 단순 수익률 광고는 제외한다. 적격 기관 대상·최장 만기 등 필수 제한을 유지한다.',
        '텔레그램 CEO 새 지갑 보급 발표': '두로프가 공개한 신규 지갑 보급 발표는 허용 사례다. 최초 제품 보급 발표의 근거·기간을 확인하며, 단순 매일 증가 집계는 재게시하지 않는다. 자동 생성 주소 수를 실제 활성 이용자 수로 쓰지 않는다.',
        '러시아 거래 제도 관련 원문 확인': '원문에 모스크바 거래소의 구체적인 서비스 개시·승인·자산 범위가 있어야 한다. 분석가의 XRP 기대만 있으면 제외한다. 이미 게시한 같은 개장 소식이면 중복이며 XRP 선물을 현물 상장 확정으로 바꾸지 않는다.',
        '입법부 디지털자산 감독·입법 방침': '실명 입법자의 새 공식 감독·입법 방침은 코인명 부재나 부수적인 주가 언급 때문에 제외하지 않는다. 계획과 조사 착수·가결은 구별하고 의혹은 주장 주체에 귀속한다.',
    }
    return '\n팀원 허용 유형 보완: ' + notes[label] + '\n원문·중복·관련 이미지 검증은 그대로 적용한다.\n'


STYLE_GUIDANCE = '''
채널의 승인 문체는 '발표함·촉구함·추진 중임·상태임·예정임'처럼 끝나는 간결한 뉴스 문장이다. 주체·행동·의미가 완결되면 이러한 종결형만으로 understandable=false 또는 faithful=false를 주지 않는다. '합니다/했다'로 바꾸라는 요구도 하지 않는다.
용어 설명은 핵심 의미를 이해하는 데 필요한 경우에만 요구한다. 토큰화 증권·분산원장·ETF·수탁 등의 용어가 문맥상 이해되면 사전식 정의 부재만으로 제외하지 않는다. 낯선 기술의 설명이 필요하면 쉬운 표현으로 한 번 고치고 핵심 조건은 보존한다.
사용자가 제공한 팀원 기사들은 허용 유형의 기준이다. 규제·입법·은행 서비스·기술 도입·실명 인사의 새 발표를 일반적인 전망/부정적 기사 금지로 확대해 막지 않는다. 사실·조건 검증 및 이미 게시된 사건 중복 검증과 편집 주제의 허용 여부는 구별한다.
'''


def style_rejection(entry, kind):
    if kind not in {'source_summary', 'negative_request'} or not isinstance(entry, dict):
        return False
    result = entry.get('result', {})
    reason = str(result.get('reason', ''))
    if not reason and isinstance(result.get('text'), str):
        import json
        try:
            decision = json.loads(result['text'])
            if isinstance(decision, dict) and decision.get('publish') is False:
                reason = str(decision.get('reason', ''))
        except (ValueError, TypeError):
            pass
    return bool(re.search(r'완결.{0,20}문장|문장.{0,35}(?:함|임|종결)|(?:용어|의미).{0,35}설명.{0,15}(?:없|않|부족)|설명.{0,20}이해하기 어렵', reason))
