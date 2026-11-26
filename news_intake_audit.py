"""False exclusions found by comparing live logs with approved team examples."""
import re
from datetime import datetime, timezone

ENABLED_AT = datetime(2026, 11, 26, 16, 55, tzinfo=timezone.utc)


def team_review_scope(story):
    """Earlier approved examples and Nov 27 named statements, not URL exemptions."""
    if not isinstance(story, dict):
        return ''
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'rumou?r|presale|giveaway|referral|sponsored|technical analysis|루머|추천인|협찬|취약점|해킹|vulnerabilit|hack(?:ed|ing)|stock price|shares?.{0,30}(?:surge|rall|fall|rise)|주가'):
        return ''
    categories = (
        ((r'Tether|테더', r'Bitcoin|비트코인', r'mining|채굴', r'AI|자동화', r'backing|support|지원|협력'), '채굴 기업 AI 자동화 도입 협력'),
        ((r'Binance|바이낸스|CZ', r'BNB', r'layer.?1|L1|레이어.?1', r'new|새|신규', r'back|support|지원'), '새 블록체인 기술망 지원 발표'),
        ((r'Lightning Labs|라이트닝.?랩스', r'Bitcoin|비트코인', r'payment|결제', r'mainnet|메인넷', r'launch|공개|출시'), '비트코인 결제 도구 메인넷 공개'),
        ((r'VanEck|반에크', r'Bitcoin|비트코인', r'ETF', r'launch|출시', r'stock|equity|bond|주식|채권'), '복수 자산 투자 ETF 출시'),
        ((r'Ethena Pay|에테나.?페이', r'deposit|예치', r'launch|출시', r'dollar|달러'), '결제 플랫폼 달러 예치 기능 출시'),
        ((r'Coinbase|코인베이스', r'Ripple USD|RLUSD|리플.?달러', r'add|support|추가|지원'), '거래소 달러 스테이블코인 지원 확대'),
        ((r'Galaxy|갤럭시', r'Bitcoin|BTC|비트코인', r'walks? back|retract|withdraw|revis|철회|수정', r'call|analysis|outlook|bottom|분석|진단|전망'), '실명 금융기관의 기존 분석 변경'),
        ((r'Coinbase CEO|Brian Armstrong|코인베이스.*CEO|브라이언.?암스트롱', r'Bitcoin|BTC|비트코인', r'inflation|money printing|IPO|인플레이션|화폐.?발행', r'says?|said|argu|발언|밝|주장|중요'), '실명 경영자의 비트코인 투자 논거 발언'),
        ((r'British Strategy CEO|Smarter Web|Andrew Webley|스마터.?웹|스마트.?웹|앤드루.?웨블리', r'Bitcoin|BTC|비트코인', r'sentiment|심리', r'says?|said|발언|밝|전환|바뀔'), '실명 경영자의 시장 심리 발언'),
        ((r'XRP|XRPL|리플', r'ISO.?20022', r'convert|demonstrat|변환|시연|데모'), '블록체인 결제 표준 연동 시연'),
        ((r'China|중국', r'housing|mortgage|주택|주택담보', r'loan|interest|대출|이자', r'support|measure|지원|부양'), '정부 주택금융 지원 정책'),
        ((r'Morgan Stanley|모건스탠리', r'digital.asset|디지털자산', r'lab|laboratory|연구소', r'launch|open|설립|신설'), '은행 디지털자산 연구소 신설'),
        ((r'financial institutions|금융권|금융기관', r'tokeniz|tokenis|토큰화', r'abroad|overseas|해외', r'pursue|pilot|trial|추진|진행|실험'), '금융기관 해외 토큰화 사업 추진'),
        ((r'Blockchain\.com|블록체인닷컴', r'IPO|기업공개|상장', r'pursue|plan|file|추진|신청'), '암호화폐 기업 기업공개 추진'),
        ((r'Oracle|오라클', r'SWIFT|스위프트', r'blockchain|ledger|블록체인|원장', r'integrat|통합|연동'), '은행 블록체인 원장 연동'),
        ((r'CFTC|셀리그|Selig', r'crypto|암호화폐|가상자산', r'margin|증거금', r'model|모델|입장|적용'), '금융당국 디지털자산 증거금 적용 입장'),
        ((r'Samsung.?Wallet|삼성.?월렛', r'USDC', r'transfer|remit|송금|이체', r'plan|launch|계획|도입|출시'), '결제 지갑 스테이블코인 송금 도입'),
        ((r'Evernorth|Evernoth|에버노스', r'XRP', r'strategy|전략', r'lend|기관.?대출|DeFi|디파이|진출'), '기관 디지털자산 운용 사업 전략'),
        ((r'Arc|아크', r'MoonPay|문페이', r'USDC', r'integrat|연동|통합|전송'), '스테이블코인 결제 구매 경로 연동'),
        ((r'Stellar|스텔라', r'repo|환매조건부', r'USDM1|기관|institutional', r'trad|거래|시험|실증'), '기관 토큰화 자산 담보 거래 실증'),
        ((r'Cardone|카돈', r'Bitcoin|BTC|비트코인', r'real.estate|부동산', r'deal|거래|진행'), '실명 기업의 부동산·디지털자산 사업 진행'),
        ((r'Lido|리도', r'validator|검증인', r'2048|2,048|0x02', r'launch|module|path|경로|모듈|가동|열어'), '스테이킹 검증인 모듈 가동'),
        ((r'Bitcoin|BTC|비트코인', r'fraud|사기', r'sentence|prison|징역|선고'), '암호화폐 연계 사기 사건 판결'),
        ((r'Aviva|아비바', r'XRP|XRPL|리플', r'fund|펀드', r'brings|launch|share.class|출시|지분'), '기관 펀드 토큰화 지분 도입'),
        ((r'Ripple|리플', r'bank.charter|은행.?인가|은행.?승인', r'final|최종', r'wins|approv|승인|취득'), '디지털자산 기업 은행 최종 인가'),
        ((r'Anchorage|앵커리지', r'stablecoin|스테이블코인', r'custody|수탁', r'gains|support|지원|확대'), '은행 스테이블코인 수탁 지원 확대'),
        ((r'Securitize|시큐리타이즈', r'Stellar|스텔라', r'add|support|추가|지원'), '기관 토큰화 플랫폼 지원망 확대'),
        ((r'Cardano|카르다노', r'police|경찰', r'evidence|증거', r'proposal|안|제출|weighs'), '블록체인 경찰 증거 관리 확대 제안'),
        ((r'Stellar|스텔라', r'USDC', r'remit|송금', r'settle|정산', r'plan|계획|도입'), '스테이블코인 국경 간 송금 정산 계획'),
    )
    for patterns, label in categories:
        if all(has(p) for p in patterns):
            # Previously supported titles keep their original intake boundary.
            # Only short/variant headlines missing those rules need this scope.
            from news_quality import crypto_ipo_scope_reason, institutional_scope_reason, feedback_scope_reason
            if crypto_ipo_scope_reason(story) or institutional_scope_reason(story) or feedback_scope_reason(story):
                return ''
            return label
    return ''


def scope(story):
    if not isinstance(story, dict):
        return ''
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'rumou?r|price target|price prediction|giveaway|presale|referral|목표가|루머|추천인'):
        return ''
    reviewed = team_review_scope(story)
    if reviewed:
        return reviewed
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
    detail = notes.get(label, '이 유형은 과거 팀원 피드백에서 허용한 정책·사업·실명 발표 유형이다. 짧은 제목이나 부수적인 가격·기술 용어로 제외하지 말고 원문에서 주체·행동·대상·단계를 확인한다.')
    if label in {'실명 금융기관의 기존 분석 변경', '실명 경영자의 비트코인 투자 논거 발언', '실명 경영자의 시장 심리 발언'}:
        detail = ('최신 사용자 승인: 갤럭시의 기존 분석 철회, 암스트롱의 인플레이션·IPO 관련 비트코인 견해, 스마터웹 CEO의 시장 심리 발언 같은 실명 주체의 새 발언·보고서 변경은 허용한다. '
                  '이 제한적 승인은 앞의 일반 전망·심리·부정적 견해 금지보다 우선한다. 투자 전망을 사실로 보증하지 말고 말한 사람에게 귀속한다. '
                  '기사 게재일과 발언일, 배경 매입일을 구별한다. 스마터웹의 55 BTC 매입은 원문상 11월 17일 배경이며 새 매입으로 쓰지 않는다. '
                  '갤럭시의 기존 분석 철회는 새 의견 변화지만 기존 분석 재소개는 중복이다. 익명 차트 전망·보안 취약점·추천인 광고까지 허용하는 것은 아니다.')
    return '\n팀원 허용 유형 보완: ' + detail + '\n원문·중복·관련 이미지 검증은 그대로 적용한다.\n'


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
