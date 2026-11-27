"""Institutional actions need not name a portfolio ticker in the headline.

Intake eligibility only; source attribution, duplicate and image gates remain.
"""
import re
from datetime import datetime, timezone

ENABLED_AT = datetime(2026, 11, 27, 14, 47, tzinfo=timezone.utc)


def scope(story):
    title = str(story.get('title', '') or '') if isinstance(story, dict) else ''
    has = lambda pattern: bool(re.search(pattern, title, re.I))
    if has(r'rumou?r|unconfirmed|presale|giveaway|referral|sponsored|price prediction|price target|루머|미확인|목표가|협찬|고래|whale'):
        return ''
    categories = (
        ((r'crypto|digital.asset|코인|암호화폐|가상자산',
          r'Russia|Russian|러시아|(?:^|\s)러[,，\s]|government|regulator|central bank|정부|금융당국|중앙은행',
          r'retail|individual|개인|일반.?투자자',
          r'exam|test|eligib|qualif|시험|자격|적격',
          r'trad|buy|allow|permit|거래|매수|산다|허용'), '개인 암호화폐 투자 자격·시험 제도'),
        ((r'crypto|digital.asset|암호화폐|가상자산',
          r'market.?mak|trading firm|trading company|liquidity provider|시장.?조성|트레이딩.?업체|유동성.?공급.?업체',
          r'wind(?:s|ing)?[ -]?down|shut(?:s|ting)?[ -]?down|cease|clos.{0,20}operation|사업.{0,15}종료|영업.{0,15}종료|운영.{0,15}종료|폐업'), '암호화폐 시장조성 기업 사업 종료'),
        ((r'crypto|digital.asset|Web3|ISAC|암호화폐|가상자산',
          r'security|cyber|hack|incident|보안|해킹|사이버',
          r'partner|agreement|MOU|taps|협약|협력|제휴|활용',
          r'response|detect|intelligence|대응|탐지|위협.?정보'), '암호화폐 업계 보안 대응 협약'),
        ((r'Homeland Security|\bDHS\b|국토안보부|government.affiliated research|정부.?연계.?연구',
          r'XRP|Ripple|리플|digital.payment|디지털.?결제',
          r'years ago|historical|past report|old report|과거|재조명|2014'), '기관 과거 결제 연구 보고서 재조명'),
        ((r'Bitcoin|BTC|비트코인', r'spot|현물', r'ETF',
          r'approv|authoriz|승인|인가'), '현물 비트코인 ETF 인가'),
    )
    for patterns, label in categories:
        if all(has(pattern) for pattern in patterns):
            return label
    return ''


def guidance(title):
    label = scope({'title': title})
    details = {
        '개인 암호화폐 투자 자격·시험 제도': '시험·투자 자격·허용 자산·시행 시점은 규제 사실이다. 특정 코인명이 제목에 없어도 심사한다. 제안과 확정 시행을 구별하고 비트·이더·테더를 임의의 다른 자산으로 확대하지 않는다. 기존 허용 발표와 별도로 시험 의무가 새로 도입·개정된 근거가 있으면 새 조치이며, 같은 규정의 조건을 뒤늦게 설명한 것뿐이면 중복 또는 보충이다.',
        '암호화폐 시장조성 기업 사업 종료': '시장조성 업체의 사업 종료는 업계 기업 사건이며 코인 자체 악재 금지와 구별한다. 오로스(Auros) 보도는 소식통을 인용한 사업 정리 보도이며 회사의 공식 확정 발표, 파산 확정, 청산 완료로 쓰지 않는다. 미공개 사유·종료 시점을 추정하지 않고 2022~2023년 재무 문제를 현재 발생한 사건으로 쓰지 않는다.',
        '암호화폐 업계 보안 대응 협약': '보안 단체의 새 협약·위협정보 공유·사고 대응 체계 구축은 심사한다. 배경의 과거 해킹 피해를 해당 코인 네트워크의 현재 취약점으로 오인하지 않는다. MOU 체결을 공격 방어 성공·피해 복구 완료로 바꾸지 않는다. SEAL은 Security Alliance이며 코인 티커가 아니다.',
        '기관 과거 결제 연구 보고서 재조명': '사용자가 허용한 과거 연구 자료 재조명 유형이다. 오래된 연구라는 이유만으로 allowed_category나 new_substantive_fact를 false로 두지 않는다. 원문이 실명 연구기관·문서·평가 내용을 뒷받침하고 기존 채널에 같은 문서·평가가 없을 때 역사적 연구 소개로 심사한다. 보고서의 작성 연도는 확인되는 경우만 쓰고 현재 기사 날짜와 구별한다. DHS 관련 연구기관의 Ripple형 결제 수단 가능성 평가는 미국 정부의 XRP 채택·구매·정책 결정 또는 보장이 아니다. 제3자 X 해석을 보고서 원문 주장으로 바꾸지 않는다. 기존에 같은 연구 내용을 소개했다면 새 기사나 새 X 인용이 있어도 반복 게시하지 않는다.',
        '현물 비트코인 ETF 인가': '국가·규제당국·운용사·상품별 실제 인가 사건을 심사한다. 샤리아 준수는 상품의 조건이며 투자 수익 보장이나 모든 종교기관의 승인으로 확대하지 않는다. 인가와 실제 상장·거래 개시를 구별한다. 다른 나라 ETF와 합치지 않고 같은 인가 재보도는 중복 처리한다.',
    }
    if not label:
        return ''
    return '\n추가 허용 유형: ' + label + '. 원문 근거·조건·중복·관련 이미지 검사는 유지한다.\n' + details[label] + '\n'


def contextual_comparison(story):
    return scope(story) in {'개인 암호화폐 투자 자격·시험 제도', '기관 과거 결제 연구 보고서 재조명'}
