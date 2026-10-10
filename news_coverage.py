"""Bounded intake expansion from the user's October 10 examples.

These rules select candidates, never authorize publication. Source, event and
image reviews still run. Newly eligible old articles cannot enter the queue.
"""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re

ENABLED_AT = datetime(2026, 10, 10, 9, 25, tzinfo=timezone.utc)
POLICY = 'luna-coverage-20261010-2'

CRYPTO = r'crypto|digital.asset|blockchain|bitcoin|ethereum|stablecoin|tokeniz|\b(?:BTC|ETH|XRP|XLM|XRPL|USDC)\b|암호화폐|가상자산|디지털.?자산|블록체인|비트코인|이더리움|스테이블코인|토큰화'
COMPANY = r'Evernorth|Evernoth|Ripple|Robinhood|Blockchain\.com|Moscow Exchange|Ledger|Binance|HashKey|BitGo|에버노스|리플|로빈후드|블록체인닷컴|모스크바거래소|레저|바이낸스|해시키|비트고'


def coverage_scope(story):
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'presale|airdrop|giveaway|referral|sponsored|technical analysis|price prediction|price target|RSI|MACD|프리세일|에어드롭|추천인|협찬|차트.?분석|목표가|지지선|저항선|뉴스.?브리핑|weekly.{0,20}recap'):
        return ''
    if has(r'FOMC|Federal Reserve|\bFed\b|Treasury|연준|재무부') and has(r'minutes|buyback|rate.{0,20}(?:decision|probabilit)|의사록|바이백|금리.{0,15}(?:결정|확률)'):
        return '통화정책·국채 매입·금리 확률'
    if has(CRYPTO) and has(r'tax|과세|국외전출세') and has(r'Greece|France|government|ministry|committee|bill|그리스|프랑스|정부|재무부|의회|법안|세무당국') and has(r'propos|approv|advanc|introduc|추진|승인|발의|통과|도입'):
        return '디지털자산 조세 제도 진행'
    if has(r'DOJ|CFTC|SEC|Bessent|법무부|금융위원|베센트|재무장관') and (has(CRYPTO) or has(COMPANY)) and has(r'investigat|review|scrutin|seiz|compliance|approval|register|조사|압류|이행|준수|신청|등록|승인'):
        return '디지털자산 감독·수사·인가 진행'
    if has(COMPANY) and has(r'merger|SPAC|Nasdaq|corporate strategy|합병|스팩|나스닥|기업.?전략|사업.?전략'):
        return '암호화폐 기업 합병·상장·사업 전략'
    if has(COMPANY) and has(r'trad|custody|staking|tokeniz|ETF|brokerage|liquidity|crypto.{0,30}product|거래|수탁|스테이킹|토큰화|증권중개|자금.?공급|프라임') and has(r'launch|open|plan|explor|expand|add|partner|seek|offer|진출|출시|개시|추진|확대|추가|검토|계약'):
        return '기관 디지털자산 서비스 진행'
    if has(r'Ripple|리플') and has(r'Wall Street|월가|월스트리트') and has(r'prime|brokerage|expand|threat|프라임|중개|경쟁|확대'):
        return '기관 금융 사업의 구체적 확대 보도'
    if has(r'Trump|트럼프|정부|administration') and has(r'quantum|양자') and has(r'plan|initiative|funding|unveils|계획|발표|예산'):
        return '정부의 양자 기술 정책 발표'
    if has(r'IMF|국제통화기금') and has(r'Salvador|엘살바도르') and has(r'Bitcoin|BTC|비트코인|crypto') and has(r'restrict|limit|approv|제한|승인'):
        return '국제기구의 국가 디지털자산 조건'
    if has(r'Ledger|CryptoBilis|레저|크립토빌리스') and has(r'investigat|probe|halt|suspend|조사|중단') and has(r'wallet|reseller|drain|loss|지갑|판매|유출|탈취'):
        return '지갑 유출 조사·판매 중단'
    if has(r'IMF|J\.?P\.?\s*Morgan|JP모건|국제통화기금') and has(CRYPTO) and has(r'report|research|inflow|billion|보고서|분석|유입|모멘텀'):
        return '실명 기관의 디지털자산 보고서'
    if has(r'Arthur Hayes|Jesse Pollak|Andrew Cuomo|Justin Sun|아서\s*헤이즈|제시\s*폴락|쿠오모|저스틴\s*선') and (has(CRYPTO) or has(r'강세장|bull market')) and has(r'says?|predict|warn|argu|explains?|발언|밝|주장|전망|["“]'):
        return '실명 주요 인물의 새 발언'
    if has(r'MARA|마라홀딩스|마라\s*홀딩스') and has(r'BTC|Bitcoin|비트코인') and has(r'transfer|move|dump|sell|sold|이체|이동|매도'):
        return '상장기업의 구체적 자산 이동 보도'
    if has(r'Chris Larsen|크리스\s*라센') and has(r'donat|기부|정치자금'):
        return '주요 업계 인사의 정치자금 공개'
    if has(r'Ripple|리플') and has(r'Canton|칸톤|DTCC') and has(r'integrat|통합'):
        return '기관 금융 인프라 통합'
    return ''


def coverage_intake_reason(story):
    if not coverage_scope(story):
        return ''
    try:
        value = story.get('pub', '')
        try:
            dt = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None or dt <= ENABLED_AT:
            return '2차 범위 확대 전 기사: 과거 대기열 발송 방지'
    except (ValueError, TypeError, AttributeError, OverflowError):
        return '2차 범위 발행 시각 확인 필요'
    return ''


GUIDANCE = '''
2026-10-10 편집 범위: 다음은 위 일반 금지 규칙의 제한적 예외이며 자동 게시 승인이 아니다.
정부의 암호화폐 과세 법안·감독 조사·압류, 거래소의 암호화폐 거래 진출, 기업의 SPAC 합병 완료·상장 일정 변경, 기관 서비스·토큰화 사업 전략과 지갑 사고의 새 조사·판매 중단을 심사한다. 특정 지정 코인이 없어도 허용한다.
FOMC 의사록·재무부 국채 바이백·칼시의 연준 금리 확률은 발표 주체와 기준 시점을 보존한다. 금리 확률은 예측시장 수치이며 연준의 결정이 아니다.
IMF·JP모건 등 실명 기관의 새 보고서와 아서 헤이즈·제시 폴락·앤드루 쿠오모·저스틴 선의 새 인터뷰·발언도 심사한다. 누가 말한 의견인지 귀속하고 봇의 전망이나 확정 사실로 쓰지 않는다. 과거 사건에 대한 새 인터뷰는 발언 자체를 요약하되 과거 행동을 현재 행동으로 만들지 않는다. 익명 차트 분석·목표가 홍보·재탕은 제외한다.
MARA 같은 실명 상장기업의 근거 있는 자산 이동 보도와 크리스 라센의 공개 정치자금 기록도 심사한다. 거래소로 이체했다는 사실만으로 매도 확정이라고 쓰지 말라. 지갑 귀속의 근거가 불충분하면 보류한다.
기사 발행일, 기사에서 설명하는 사건 발생일, 인용·삽입 X 게시물 날짜를 구별한다. 삽입 게시물의 날짜를 기사 발행일로 쓰지 말라. 최신 발행일만으로 오래된 사건을 새 사건으로 인정하지 말고 실제 새 사실을 확인한다. 서로 충돌하면 근거 없이 날짜를 선택하지 않는다.
계획·신청·예상·추정·조건부 등 정확한 한정 표현 자체는 금지 사유가 아니다. 승인 예상과 승인 완료를 구분한다. 합병 승인→합병 완료, 조사 착수→판매 중단처럼 새 단계는 중복 설명과 구별한다.
본문은 기본 1~2문장, 180~220자를 목표로 하되 중요한 조건 보존에 필요하면 최대 320자까지 허용한다. 필요 없는 USDC·스테이블코인 사전식 정의는 붙이지 않는다. 기술 위험·법적 제한의 이해에 꼭 필요한 설명만 짧게 포함한다. 기술명·회사명은 통용 한국어로, V2·REVO·USDC 같은 식별자는 유지한다.
'''


def source_packet(story, source):
    """Keep provenance separate from quoted event dates; preserve actual evidence."""
    import json
    return json.dumps({'rss_published_at': story.get('pub', ''),
                       'page_published_at': story.get('page_published_at', ''),
                       'source_url': story.get('url', ''),
                       'article_body': source[:8200]}, ensure_ascii=False)
