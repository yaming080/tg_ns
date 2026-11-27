"""Narrow team-feedback candidates; source, freshness, event and image gates remain."""
import re
from datetime import datetime, timezone

ENABLED_AT = datetime(2026, 11, 26, 15, 52, tzinfo=timezone.utc)


def scope(story):
    title = str(story.get('title', '') or '') if isinstance(story, dict) else ''
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'rumou?r|unconfirmed|루머|미확인|price target|price prediction|목표가|급등주|sponsored|presale|giveaway|whale|고래|daily.{0,20}flow|일일.{0,10}유출입'):
        return ''
    categories = (
        ((r'Morgan Stanley|모건스탠리|Arkadios|아르카디오스|Susquehanna|서스퀘해나|wealth manager|자산운용사', r'Bitcoin|BTC|XRP|비트코인', r'ETF', r'13F|filing|disclos|holdings|stake|공시|분기|보유'), '기관 분기 ETF 보유 공시'),
        ((r'Swiss|Switzerland|스위스', r'crypto|암호화폐|가상자산|CARF', r'tax|report|data|과세|조세|정보', r'approv|clear|exchange|sharing|승인|교환'), '국가 간 암호화폐 과세 정보 교환'),
        ((r'FCA|UK Regulator|금융행위감독청', r'DeFi|디파이|탈중앙화.?금융', r'rule|regulat|규제|규정'), '금융당국 디파이 규제 추진'),
        ((r'Spain|Sepblac|스페인|셉블락', r'crypto|암호화폐|가상자산', r'freez|동결', r'account|계좌|judge|판사|사법'), '자금세탁 방지 계좌 동결 권한'),
        ((r'Korea.*police|Korean police|한국.*경찰|경찰청', r'crypto|암호화폐|가상자산', r'track|추적', r'plan|invest|software|tool|계획|투자|도입|개발|구매'), '수사기관 암호화폐 추적 도구 도입'),
        ((r'Coinbase|코인베이스', r'AI|인공지능|에이전트', r'buyback|repurchas|자사주|매입'), '코인베이스 AI 결제 사업·자본 배분 발표'),
        ((r'Shibarium|시바리움', r'privacy|프라이버시|개인정보', r'developer|개발자|ready|준비|testnet|테스트넷'), '시바리움 개발자 프라이버시 구현 준비 발표'),
        ((r'Discount Bank|디스카운트은행|디스카운트 은행', r'Bitcoin|비트코인|crypto|암호화폐', r'open|launch|trad|개시|출시|거래', r'app|앱|direct|직접'), '은행 앱 암호화폐 거래 실제 개시'),
        ((r'Old Glory|올드글로리', r'XRP', r'CEO|최고경영자|Mike Ring|마이크링|announcement|발표'), '은행 CEO XRP 서비스 일정 발표'),
        ((r'한국은행|Bank of Korea|\bBOK\b', r'기준금리|policy rate|base rate', r'인상|인하|동결|rais|hike|cut|hold'), '한국은행 기준금리 결정'),
        ((r'DOJ|Justice Department|법무부', r'Jensen|젠슨|Nvidia|엔비디아', r'probe|investigat|return|수사|복귀'), '미국 반도체 기업 관련 정부 수사 판단 보도'),
        ((r'White House|백악관', r'Coupang|쿠팡', r'fine|penalt|treat|과징금|차별|약속'), '한미 기업 규제·통상 갈등 공식 입장'),
        ((r'Russia|러시아', r'defen[cs]e|military|국방|군비', r'budget|allocat|approv|예산|편성|통과'), '정부 국방 예산 편성·의회 처리'),
        ((r'Musk|머스크|SpaceX|스페이스X', r'child|아동|어린이|트럼프.?계좌', r'share|주식|2주', r'give|donat|지급|기부|출연'), '기업·실명 인사의 아동 자산형성 계좌 출연'),
        ((r'Busan|부산항', r'blockchain|블록체인', r'physical AI|피지컬.?AI|환적운송', r'실험|실증|개발|연결|trial|develop|connect'), '항만 블록체인·물류 자동화 실증 사업'),
    )
    for patterns, label in categories:
        if all(has(p) for p in patterns):
            return label
    return ''


def requires_contextual_comparison(story):
    # A token signature cannot distinguish a scheduled opening from a live
    # service, or a new reporting period from the same filing's repeat coverage.
    # Exact URLs/titles, cached verdicts and the final full-history review remain.
    from news_intake_audit import team_review_scope
    from news_institutional_actions import contextual_comparison
    return (contextual_comparison(story) or scope(story) in {'은행 앱 암호화폐 거래 실제 개시', '기관 분기 ETF 보유 공시'}
            or team_review_scope(story) in {'실명 금융기관의 기존 분석 변경',
                '실명 경영자의 비트코인 투자 논거 발언', '실명 경영자의 시장 심리 발언'})


def guidance(title):
    if not scope({'title': title}):
        return ''
    details = '''
11월 27일 팀원 피드백: 해당 유형은 후보일 뿐 자동 게시 승인이 아니다. 코인명 부족이나 '분기 보유 공시'라는 이유만으로 제외하지 않는다. 원문·발표 시점·기존 사건·이미지 검증은 유지한다.
기관 13F는 분기 말 보유 내역 공시다. 보고 기간·공시일·기관이 확인된 새 공시는 심사하되 같은 분기 재보도와 고래 매매·일간 ETF 유출입은 제외한다. 보유 평가액을 신규 매수액으로 쓰거나 고객·운용 계정 보유를 은행 고유자금 매수로 단정하지 않는다. Arkadios의 총 운용자산 약 90억달러는 XRP 투자액이 아니다. 펀드명·수량이 비공개라면 추정하지 않는다. Morgan Stanley의 Strategy 155만주는 증가분이며 총보유량과 구별한다.
스위스 CARF는 암호화폐 과세정보 교환 체계다. 57개 관할 승인과 2028년 교환 개시, 참여 의사·정보보호 요건을 구별한다. 스페인 Sepblac의 계좌 동결은 자금세탁·테러자금 의심 시 최대 5영업일, 진행 중 거래 정지는 10영업일이다. 의회 승인과 2027년 시행 예정 조건을 삭제하거나 이미 무제한 동결 중이라고 쓰지 않는다. FCA 규제 추진은 해킹 사건의 단순 재탕과 구별한다.
경찰청의 자금추적 도구 구매·수사관 교육 계획은 실제 도입 완료가 아니다. 믹서·탈중앙화 거래소·블록체인 간 브리지를 거친 자금 추적이며 거래소와 블록체인을 새로 연결하는 서비스가 아니다.
코인베이스 자사주 매입과 CEO의 AI 결제 사업 전망은 별개 사실로 귀속한다. 미공개 당분기 매입액을 기존 승인 한도나 전분기 실적으로 채우지 않는다. 시바리움 개발자의 준비·테스트넷 발언은 메인넷 출시 완료가 아니다. 실제 구현·시험 근거 없이 장래 기대만 있으면 보류한다.
디스카운트은행의 예정 공지와 실제 개시는 구별하고, 외부 지갑 입출금 불가·이용자 자격 등 핵심 조건을 보존한다. 올드글로리은행의 '출시 약 30일 후'는 CEO의 대략적인 계획이며 확정 날짜가 아니다. 이전 기사에 같은 일정이 있으면 반복하지 않는다. 새로운 설명만 추가된 경우 중복 검사를 통과시키지 않는다.
한국은행 금리 변동 폭은 %p와 %를 구별한다. 원문 본문이 없는 제목만의 속보나 매체 기본 이미지만 있는 기사는 강제로 발송하지 않는다. 젠슨황 관련 소식통 보도는 로이터 보도로 귀속하며 무혐의·안보 위험 없음 확정으로 바꾸지 않는다. 쿠팡 과징금의 미국 측 차별 주장과 한국 측 적법 집행 반박을 구별한다. 러시아 하원 예산 처리와 최종 시행, 3년 합계와 단년도 금액을 혼동하지 않는다.
스페이스X 아동 주식 출연은 활성화된 트럼프 계좌 대상이라는 실제 조건을 보존하고 모든 아동 지급 완료로 쓰지 않는다. 부산항 블록체인 운송 시스템과 2029년 로봇 실증 목표는 서로 다른 단계다. 과거 사업 재소개만이면 보류하고 새 진행 근거를 확인한다.
'''
    # Send only the relevant source constraints, keeping per-article prompt cost bounded.
    label = scope({'title': title})
    prefixes = {
        '기관 분기 ETF 보유 공시': '기관 13F',
        '국가 간 암호화폐 과세 정보 교환': '스위스 CARF',
        '금융당국 디파이 규제 추진': '스위스 CARF',
        '자금세탁 방지 계좌 동결 권한': '스위스 CARF',
        '수사기관 암호화폐 추적 도구 도입': '경찰청',
        '코인베이스 AI 결제 사업·자본 배분 발표': '코인베이스',
        '시바리움 개발자 프라이버시 구현 준비 발표': '코인베이스',
        '은행 앱 암호화폐 거래 실제 개시': '디스카운트은행',
        '은행 CEO XRP 서비스 일정 발표': '디스카운트은행',
        '한국은행 기준금리 결정': '한국은행',
        '미국 반도체 기업 관련 정부 수사 판단 보도': '한국은행',
        '한미 기업 규제·통상 갈등 공식 입장': '한국은행',
        '정부 국방 예산 편성·의회 처리': '한국은행',
        '기업·실명 인사의 아동 자산형성 계좌 출연': '스페이스X',
        '항만 블록체인·물류 자동화 실증 사업': '스페이스X',
    }
    return '\n'.join(line for line in details.splitlines()
                     if line.startswith(('11월 27일', prefixes[label]))) + '\n'


EDIT_GUIDANCE = '''
팀원 편집 기준 추가: 단일 제휴·발언은 핵심 한 문장으로 충분하면 끝낸다. 두 번째 문장은 이용 제한·법적 단계·새로운 일정처럼 의미 있는 조건이 있을 때만 쓴다. 수탁·ETF·지갑 등 문맥상 이미 이해 가능한 용어를 설명하려고 본문을 불필요하게 늘리지 않는다. 낯선 핵심 용어는 쉬운 말로 대체하거나 짧게 설명한다. Yapı Kredi / Yapi Kredi의 한글 표기는 야피크레디다.
'''
