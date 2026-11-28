"""Nov28 feedback: candidate selection, never a publication bypass."""
from datetime import datetime, timezone, timedelta
import re

ENABLED_AT = datetime(2026, 11, 28, 5, 20, tzinfo=timezone.utc)


def scope(story):
    if not isinstance(story, dict):
        return ''
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'presale|giveaway|referral|sponsored|rumou?r|unconfirmed|price target|RSI|MACD|프리세일|협찬|루머|미확인|목표가|지지선|저항선'):
        return ''
    if (has(r'bank|은행') and has(r'crypto|digital.asset|암호화폐|가상자산|디지털.?자산')
            and has(r'trad|OTC|거래') and has(r'launch|start|open|offer|출시|개시|시작|제공')):
        return '은행 디지털자산 거래 서비스'
    if (has(r'Mastercard|Visa|마스터카드|비자') and has(r'Ripple|crypto|stablecoin|리플|암호화폐|스테이블코인')
            and has(r'partner|collaborat|제휴|협력') and has(r'expand|launch|extend|확대|출시|체결')):
        return '카드 네트워크 디지털자산 제휴'
    if (has(r'stock exchange|securities exchange|\bB3\b|증권거래소')
            and has(r'stablecoin|스테이블코인') and has(r'launch|issu|partner|develop|출시|발행|제휴|개발')):
        return '증권거래소 법정화폐 스테이블코인 사업'
    if (has(r'blockchain|블록체인') and has(r'digital.identit|디지털.?신원')
            and has(r'rule|standard|regulat|규정|표준|규제') and has(r'announc|issu|adopt|발표|도입|시행')):
        return '블록체인 디지털신원 제도'
    if (has(r'Changpeng Zhao|\bCZ\b|창펑자오|자오창펑')
            and has(r'blockchain|crypto|블록체인|암호화폐') and has(r'real.use|adoption|growth|실사용|성장')):
        return '실명 경영자의 블록체인 실사용 견해'
    if (has(r'Trump family|Eric Trump|트럼프.{0,4}가족|에릭.?트럼프')
            and has(r'Ripple|XRP|리플') and has(r'knows?|interview|prais|과거|인터뷰|평가')):
        return '실명 인사의 과거 리플 인터뷰 재조명'
    if (has(r'XRP|XRPL') and has(r'rich list|accounts?|보유.?계정|계정.?수')
            and has(r'bull market|상승장|강세장')):
        return 'XRP 활용 지표와 출처가 있는 시장 견해'
    return ''


def contextual_comparison(story):
    return scope(story) in {'실명 인사의 과거 리플 인터뷰 재조명', 'XRP 활용 지표와 출처가 있는 시장 견해'}


def guidance(title):
    label = scope({'title': title})
    if not label:
        return ''
    common = ('\n11월 28일 추가 허용 유형: ' + label + '\n'
              '지정 코인명 부재나 일반 전망 금지 문구만으로 재차 제외하지 않는다. '
              '후보 분류는 원문 사실을 증명하지 않는다. 원문·중복·관련 이미지 검사는 유지한다.\n')
    details = {
        '은행 디지털자산 거래 서비스': '은행의 자체 디지털자산 거래 서비스는 코인명이 없어도 심사한다. 적격투자자 등 이용 자격·장외거래 조건과 출시 단계를 보존한다. 다른 거래소의 개시 일정과 혼동하지 않는다.',
        '카드 네트워크 디지털자산 제휴': '카드 네트워크의 구체적인 디지털자산 제휴 확대를 심사하되 같은 제휴의 재보도는 제외한다. 카드 결제 정산과 AI 에이전트 금융의 지원 범위·추진 단계를 구별하고 코인 가격 효과를 추가하지 않는다.',
        '증권거래소 법정화폐 스테이블코인 사업': '증권거래소의 법정화폐 연동 스테이블코인 공동 개발·발행 계획은 허용한다. 제휴 참여와 실제 발행 주체, 예정 출시와 출시 완료를 구별한다.',
        '블록체인 디지털신원 제도': '블록체인 기반 신원인증 규정 발표와 시행 시점을 구별한다. 내년 시행은 발표 자체가 미래 허구라는 뜻이 아니다. 개인정보 조건을 보존하고 코인 채택·CBDC로 확대하지 않는다.',
        '실명 경영자의 블록체인 실사용 견해': '확인되는 실명 경영자의 실사용·산업 성장 발언은 그 인물의 견해로 귀속한다. 성장이나 가격 상승이 확정됐다고 쓰지 않는다.',
        '실명 인사의 과거 리플 인터뷰 재조명': '사용자가 승인한 과거 인터뷰 재조명도 채널에 처음 소개하는 경우 심사한다. 일반적인 새 사건 필수 규칙의 제한적 예외이며 과거 발언임을 명시한다. 에릭 트럼프의 브래드 갈링하우스에 대한 친분·개인적 평가는 미국 정부의 XRP 채택·보장·정책 결정이 아니다. 원문에 근거한 인터뷰 시점만 사용한다. 같은 인터뷰가 이미 소개됐다면 새 기사 날짜만으로 재게시하지 않는다.',
        'XRP 활용 지표와 출처가 있는 시장 견해': '원문에 발언 출처와 계정·활용 근거가 함께 있는 XRP 시장 견해는 심사한다. Digital Asset Investor 등 확인되는 발언자에게 전망을 귀속하고 역대급 상승장 확정을 쓰지 않는다. 계정 수는 고유 이용자 수가 아니다. 지표 기준일·기간을 보존하고 대출 프로토콜의 승인 진행을 도입 완료로 쓰지 않는다. 원문에 출처가 없거나 같은 견해·지표 재탕이면 보류한다.',
    }
    return common + details[label] + '\n'


def runtime_date_guidance(now=None):
    now = now or datetime.now(timezone.utc)
    return (f'실행 기준 현재 날짜: UTC {now.astimezone(timezone.utc):%Y-%m-%d}, '
            f'한국 {now.astimezone(timezone(timedelta(hours=9))):%Y-%m-%d}. '
            '모델이 기억한 날짜 대신 이 실행 날짜를 사용한다. 기사 발행일·과거 발언일·미래 시행일을 구별한다. '
            '실행 날짜 이전 기사를 미래라는 이유로 제외하지 않는다. 날짜만으로 사실성을 보장하지 않는다.\n')


def date_refusal(entry):
    result = (entry or {}).get('result', {})
    if result.get('summary'):
        return False
    reason = str(result.get('reason', ''))
    return bool(re.search(r'현재.{0,15}(?:날짜|시점).{0,15}미래|미래.{0,30}현재|future.{0,60}(?:current|today)|(?:current|today).{0,60}future', reason, re.I))
