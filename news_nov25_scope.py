"""Team editorial examples select candidates, never bypass publication checks."""
import re
from datetime import datetime, timezone

ENABLED_AT = datetime(2026, 11, 25, 7, 0, tzinfo=timezone.utc)


def excluded_claim(title):
    return bool(re.search(r'Nvidia|엔비디아', title, re.I)
                and re.search(r'XRP|리플', title, re.I)
                and re.search(r'rumou?r|unconfirmed|루머|미확인', title, re.I))


def scope(story):
    title = str(story.get('title', '') or '') if isinstance(story, dict) else ''
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'rumou?r|루머|목표가|price target|price prediction|sponsored|presale|giveaway'):
        return ''
    categories = (
        ((r'원화|won|KRW', r'스테이블코인|stablecoin', r'인가|발행|자기자본|licen|issu|capital'), '원화 스테이블코인 발행 인가 요건'),
        ((r'Moscow|MOEX|모스크바', r'USDT|암호화폐|crypto', r'VAT|tax|부가세|과세'), '거래소 디지털자산 매매 과세 조건'),
        ((r'XRPL|XRP.?Ledger|XRP레저', r'Evernorth|에버노스|분기|Q[1-4]|quarter', r'DEX|거래소', r'보고서|report|volume|거래량'), 'XRPL 분기 시장구조 보고서'),
        ((r'Swiss National Bank|SNB|스위스.*중앙은행|헬베티아|Helvetia', r'tokeniz|tokenis|토큰화|settlement|결제', r'explor|trial|test|검토|시험|실증'), '중앙은행 토큰화 결제 실증'),
        ((r'UniCredit|유니크레디?트|유니크레딧', r'Bitcoin|비트코인|ETP', r'certificate|증서|원금|capital.protect', r'open|launch|introduc|출시|개방'), '은행 개인투자자용 비트코인 연계 증서 출시'),
        ((r'Trump|트럼프', r'Nvidia|엔비디아|Jensen|젠슨', r'pardon|stake|equity|사면|지분'), '미국 정부의 반도체 기업 정책 발언'),
        ((r'Arthur Hayes|아서.?헤이즈', r'AI|인공지능', r'bubble|bailout|거품|구제금융'), '실명 인사의 AI·유동성 거시경제 발언'),
        ((r'Threads|스레드', r'crypto|stock|cashtag|암호화폐|주식|시세', r'launch|add|introduc|도입|제공|출시'), '소셜 플랫폼 금융 시세 기능 도입'),
        ((r'Franklin Templeton|프랭클린.?템플턴', r'Stellar|스텔라', r'cost|fee|비용|수수료'), '실명 자산운용사 블록체인 처리 비용 비교'),
        ((r'Pundit to XRP and XLM Holders', r'You Need to Know How Big This Is'), '실명 자산운용사 비용 비교의 출처 확인'),
        ((r'Chen Jining|천지닝', r'Xi|시진핑|주석|정치국|Shanghai|상하이', r'purge|investigat|disciplin|숙청|조사|기율'), '중국 고위 정치인 공식 기율 조사'),
        ((r'거래소|exchange', r'은행|bank', r'1거래소|1은행|one.exchange|one.bank', r'유지|maintain|retain|정책'), '거래소 실명계좌 은행 제도 유지'),
    )
    for patterns, label in categories:
        if all(has(p) for p in patterns):
            return label
    return ''


def guidance(title):
    if not scope({'title': title}):
        return ''
    return '''
11월 25일 팀원 편집 보완: 해당 유형은 코인명 부재·보고서·전망이라는 이유만으로 SKIP하지 않는다. 신규 발표·서비스·실명 기관 연구·정책 발언의 원문과 날짜를 확인해 심사한다. 새 내용 없는 가격·거래량 재탕은 제외하며 기존 사실·중복·이미지 검증을 유지한다.
원화 스테이블코인 자기자본 기준은 인가 추진안인지 시행 규정인지 구별한다. 1거래소 1은행 유지 방침은 현재 정책이며 영구 금지나 새 은행 허가가 아니다.
모스크바 거래소 USDT 부가세는 매수/매도, 적용 시점, 대상 자산, 면제와 제재 관련 제한을 정확히 보존한다. 비트코인·이더리움 매도 면제를 매수까지 확대하지 않는다. XRP 지수 선물과 XRP 현물 상장 승인은 다르며 분석가의 기대를 확정 상장으로 바꾸지 않는다. 동일 개장 소식을 새 전망만 더해 반복하지 않는다.
XRPL 분기 보고서는 실명 작성기관·분기·시장구조 변화가 확인될 때 심사한다. 일간 거래량 숫자만 바뀐 기사는 제외한다. Evernorth 보고서의 DEX 거래량 증감과 토큰화 자산 잔고 증감은 별개 지표다. 2026년 3분기 원문의 DEX 전분기 대비 26%와 토큰화 자산 34%를 혼동하지 않는다.
스위스 중앙은행 Helvetia는 토큰화 자산 결제 실증·검토이며 CBDC 일반 발행 완료가 아니다. 유니크레딧 증서는 6년 만기 보유 시 원금 100%, 총수익 최대 65%, 최소 1000유로 등 조건을 묶어 설명한다. 조기매도까지 원금보장하거나 연 65% 수익으로 쓰지 않는다.
트럼프 사면 가능성·정부 지분 검토는 발언자의 의견이며 실행 완료가 아니다. 아서 헤이즈의 새 AI 거품·구제금융 인터뷰는 조건부 거시경제 견해로 귀속한다. 확인되지 않은 미래 붕괴·가격 상승을 사실로 쓰지 않는다.
스레드 시세 조회 기능은 거래·중개 서비스 출시가 아니다. 프랭클린템플턴 비용 비교는 비교 기간·처리 건수·블록체인 거래 처리비 범위가 있어야 하며 전체 펀드 운영비 절감이나 XRP·XLM 가격 상승을 보장하지 않는다. 오래된 수치를 새 게시물로 재소개했을 뿐이면 제외한다.
천지닝 공식 기율 조사와 숙청 동기·차기 주석 전망은 사실과 해석을 분리한다. 조사 착수를 유죄 확정으로 쓰지 않는다. 엔비디아 XRP 매입 루머는 공식 확인이 없으므로 매입 예정·이미 보유로 게시하지 않는다.
'''


LAYOUT_GUIDANCE = '''
팀원 편집 형식: 첫 문장은 주체·행동·핵심 결과를 짧게 쓴다. 상품 조건·참여 기관·이용 범위처럼 설명이 여러 항목이면 첫 문장 아래 빈 줄을 두고 • 불릿 2~3개로 묶는다. 같은 조건은 한 불릿으로 묶되 만기·보장 조건·수익 상한·최소 투자액 등 필수 한정은 삭제하지 않는다. 반복 정의와 부차적인 청약 일정을 줄여 총 320자 이내로 작성한다. 태그는 후처리가 붙이므로 원문 사실을 먼저 정확히 작성한다.
'''


def readable_summary(summary):
    """Presentation only: preserve every sentence/condition already validated."""
    parts = [p.strip() for p in summary.split('\n\n') if p.strip()]
    if len(parts) >= 3 and not any(p.startswith('• ') for p in parts):
        return parts[0] + '\n\n' + '\n\n'.join('• ' + p for p in parts[1:])
    return summary
