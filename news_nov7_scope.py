"""Narrow outage-feedback candidates. Every candidate still needs source review."""
import re


def scope(story):
    if not isinstance(story, dict):
        return ''
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'price prediction|price target|technical analysis|sponsored|giveaway|referral|presale|'
           r'목표가|차트.?분석|협찬|에어드롭|추천인|루머|뉴스.?브리핑|weekly recap'):
        return ''
    crypto = r'crypto|digital.asset|Bitcoin|Ethereum|USDT|암호화폐|가상자산|비트코인|이더리움'
    if (has(r'central bank|중앙은행') and has(crypto) and has(r'bill|legislat|법안')
            and has(r'oppos|reject|object|반대|거부|우려')):
        return '중앙은행의 디지털자산 입법 공식 입장'
    if (has(r'Gopax|고팍스|crypto exchange|암호화폐\s*거래소|가상자산\s*거래소')
            and has(r'halt|suspend|중단') and has(r'cyber|hack|security|사이버|해킹|보안')):
        return '거래소의 사이버 위협 대응 서비스 중단'
    if (has(r'Russia|러시아') and has(crypto) and has(r'retail|개인\s*투자|비적격|일반\s*투자')
            and has(r'approv|allow|permit|허용|승인')):
        return '당국의 개인투자자 디지털자산 거래 허용'
    if (has(r'Treasury|Federal Reserve|\bFed\b|재무부|연준') and has(crypto)
            and has(r'transfer|송금') and has(r'abandon|withdraw|scrap|철회|추진\s*중단')):
        return '당국의 디지털자산 송금 규제안 철회'
    if (has(r'NYSE|뉴욕증권거래소') and has(r'transfer agents?|명의개서')
            and has(r'tokeniz|XRP|Stellar|토큰화|스텔라|리플')
            and has(r'sign|agreement|connect|계약|체결|연결')):
        return '거래소 토큰화 증권의 명의개서기관 계약 보도'
    if (has(r'J\.?P\.?\s*Morgan|JP모건|제이피모건') and has(r'Bitcoin|비트코인|\bBTC\b')
            and has(r'long.term|장기') and has(r'expected returns?|return assumptions?|기대\s*수익률')):
        return '실명 금융기관의 장기 자산 기대수익률 연구'
    if (has(r'crypto exchanges?|암호화폐\s*거래소|가상자산\s*거래소')
            and has(r'cold storage|cold wallets?|콜드\s*(?:월렛|스토리지)|저온\s*보관')
            and has(r'tout|disclos|announce|emphasi|공개|발표|강조')):
        return '거래소의 고객 자산 보관 정책 새 공개'
    if (has(r'Iran|이란') and has(r'Hormuz|호르무즈') and has(r'conditions?|조건')
            and has(r'cannot|won.t|refus|불가|개방.{0,10}거부|충족\s*전')):
        return '당사국의 해협 개방 조건 입장'
    if (has(r'Iran|이란') and has(r'nuclear|핵\s*문제')
            and has(r'willing.{0,20}discuss|논의할\s*의향|논의\s*의사')):
        return '당사국의 협상 의향에 관한 출처 있는 보도'
    return ''


def guidance(title):
    if not scope({'title': title}):
        return ''
    return '''
11월 7일 운영자 편집 보완: 아래의 새 보도는 특정 코인 이름이나 완료형 동사가 부족해도 심사한다.
중앙은행의 암호화폐 법안 반대, 당국의 개인 투자자 거래 허용·송금 추적 규제안 철회, 거래소의 실제 예방적 거래 중단·고객 자산 보관 정책 공개는 입법·감독·이용자 보호 소식이다. 공식 입장을 법안 부결·시행 완료로 바꾸지 말고 시행 예정일과 적용 대상을 보존한다. 거래소 자체 사이버 대응을 BNB·비트코인 프로토콜 자체 결함과 혼동하지 않는다.
NYSE 명의개서기관 계약은 주체·기관명·계약 범위를 원문으로 확인한다. 명의개서기관의 기존 체인 연계가 NYSE의 직접 XRP/XLM 채택·통합 완료나 특정 코인 사용 확정을 뜻하지 않는다. 배경 관계만 있는 체인의 새 채택을 만들어내지 않는다.
JP모건 등 실명 금융기관이 새 보고서에서 제시한 장기 기대수익률은 가정·기간을 포함한 기관 전망으로 귀속한다. 실제·보장 수익률이나 매수 권유로 쓰지 않는다. 익명 목표가·차트 홍보와 같은 보고서 재탕은 계속 제외한다.
거래소의 콜드월렛 비율 강조는 최신 당사자 공개 내용이 있는지 확인한다. 보관 비율을 높였다는 행동이나 자산 안전 보장으로 바꾸지 않는다. 같은 사고 피해액만 바뀐 후속 집계·일반 예방수칙 모음은 제외한다.
이란의 호르무즈 개방 조건 입장과 핵 문제 논의 의향을 다룬 출처 있는 보도는 당사자의 입장·보도된 의향으로 전달한다. '가능성'이 있다는 이유만으로 자동 제외하지 않지만 익명 전망만 있고 당사자의 새로운 입장 근거가 없으면 보류한다. 재인용된 오래된 발언은 제외하고, 합의·해협 개방·종전 완료로 확정하지 않는다.
포트폴리오 자체 악재·비포트폴리오 사업 제외, 원문 충분성, 이미지 적합성, 동일 사건 중복/보충 및 과거 기사 차단은 그대로 적용한다.
'''
