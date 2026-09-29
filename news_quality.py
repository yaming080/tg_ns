"""Reviewable editorial safeguards; no network access or posting side effects."""
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit


# User-confirmed manual posts, not a live Telegram history integration.
# Keep these out of the queue when an editorial rule becomes less restrictive.
MANUALLY_POSTED_ARTICLES = frozenset({
    ('crypto.news', '/spain-says-self-custody-crypto-does-not-need-form-721-reporting'),
    ('crypto.news', '/tether-faces-senate-scrutiny-over-iran-linked-usdt'),
    ('crypto.news', '/cardano-foundation-ucla-partner-blockchain-education'),
    ('crypto.news', '/coinbase-can-now-settle-derivatives-24-7-with-usdc'),
    ('bloomingbit.io', '/feed/news/121184'),
    ('cryptobriefing.com', '/tech-giant-oracle-integrates-with-swift-blockchain-ledger-to-connect-banks-tokenized-deposits'),
    ('coingape.com', '/breaking-franklin-templeton-partners-with-bybit-to-offer-tokenized-money-market-funds'),
    ('bloomingbit.io', '/feed/news/121107'),
    ('bloomingbit.io', '/feed/news/121086'),
    ('bloomingbit.io', '/feed/news/121109'),
    ('bloomingbit.io', '/feed/news/121114'),
    ('bloomingbit.io', '/feed/news/121132'),
    ('timestabloid.com', '/expert-presents-blackrock-xrp-endgame-heres-what-happened'),
    ('timestabloid.com', '/the-genius-act-will-amplify-xrps-use-case-expert-presents-proof'),
    ('etoday.co.kr', '/news/view/2629433'),
    ('etoday.co.kr', '/news/view/2629507'),
    ('crypto.news', '/circle-gains-binance-backing-in-usdc-tether-race'),
    ('crypto.news', '/south-korea-weighs-liquidity-rules-for-won-stablecoins'),
})

# User-confirmed removals stay blocked beyond rolling history retention.
EDITOR_REJECTED_ARTICLES = {
    ('news.bitcoin.com', '/stablecoins/un-circle-foundation-partner-to-speed-aid-via-stablecoins'): '팀원 중복 삭제 확인: 서클 재단 유엔 구호사업',
    ('tokenpost.kr', '/news/blockchain/414798'): '사용자 삭제: BIP138 기술 설명 불명확',
    ('bloomingbit.io', '/feed/news/121125'): '사용자 제외 확인: 아서 헤이즈 전망·의견 기사',
}

# Only newly published geopolitical news enters review after this policy change.
# Keep this fixed across restarts; never reset existing source/posting state.
GEOPOLITICS_ENABLED_AT = datetime(2026, 9, 28, 8, 22, 31, tzinfo=timezone.utc)
GEOPOLITICS_SCOPE = '주요 국제정세·외교·통상 진행'
INSTITUTIONAL_ENABLED_AT = datetime(2026, 9, 28, 9, 7, 42, tzinfo=timezone.utc)
INSTITUTIONAL_SCOPE = '금융기관 디지털자산 사업·토큰화'
INSTITUTIONAL_SERVICES_ENABLED_AT = datetime(2026, 9, 28, 15, 54, 21, tzinfo=timezone.utc)
CRYPTO_IPO_ENABLED_AT = datetime(2026, 9, 29, 5, 27, 27, tzinfo=timezone.utc)
CRYPTO_IPO_SCOPE = '암호화폐 기업의 기업공개 진행'
REGULATORY_PAYMENT_ENABLED_AT = datetime(2026, 9, 29, 6, 43, 25, tzinfo=timezone.utc)
TAX_REPORTING_ENABLED_AT = datetime(2026, 9, 29, 7, 55, 43, tzinfo=timezone.utc)
TAX_REPORTING_SCOPE = '암호화폐 세금·신고 제도 안내'


def tax_reporting_scope_reason(title):
    """Official reporting/tax developments, not tax tips or personal opinions."""
    has = lambda pattern: bool(re.search(pattern, title, re.I))
    if has(r'절세\s*팁|신고\s*방법|전망|루머|소문|'
           r'\b(?:how to|tips?|guide|opinion|rumou?rs?|could|might|predict\w*)\b'):
        return ''
    crypto = r'\b(?:crypto|cryptocurrency|cryptocurrencies|digital[ -]assets?|bitcoin|stablecoins?)\b|암호화폐|가상자산|디지털\s*자산|비트코인|스테이블코인'
    authority = r'\b(?:government|tax authority|tax authorities|revenue service|Treasury|IRS|HMRC|Spain|Spanish)\b|정부|세무당국|국세청|재무부|스페인'
    reporting = r'\b(?:tax|taxes|taxation|reporting|declaration|disclosure|form\s+\d+)\b|세금|과세|납세|신고|보고\s*의무'
    action = r'\b(?:says?|said|clarif\w*|announc\w*|confirm\w*|exempt\w*|requir\w*|propos\w*|approv\w*|issues?|issued)\b|밝힘|발표|안내|명확화|확인|면제|제외|의무화|제안|승인'
    return TAX_REPORTING_SCOPE if has(crypto) and has(authority) and has(reporting) and has(action) else ''


def tax_reporting_intake_reason(story):
    if channel_scope_reason(story) != TAX_REPORTING_SCOPE:
        return ''
    return _scope_intake_reason(story, TAX_REPORTING_ENABLED_AT, '세금·신고 제도')


def regulatory_payment_scope_reason(title):
    """Concrete oversight and settlement changes; no incidental quote pairs."""
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'가격\s*전망|목표가|루머|소문|\b(?:rumou?rs?|could|might|price prediction|price target)\b'):
        return ''
    subject = r'\b(?:crypto|cryptocurrency|stablecoins?|USDT|USDC|Tether|Coinbase)\b|암호화폐|가상자산|스테이블코인|테더|코인베이스'
    authority = r'\b(?:Senate|senators?|Congress|Treasury|DOJ|SEC|CFTC|regulators?|prosecutors?)\b|상원|하원|의회|재무부|법무부|검찰|금융당국'
    inquiry = r'\b(?:scrutiny|investigat\w*|inquir\w*|probe\w*|subpoena\w*|hearings?)\b|조사|수사|자료\s*(?:요구|요청)|청문회'
    approval = r'\b(?:approv\w*|authoriz\w*)\b|승인|인가'
    if has(subject) and has(authority) and has(inquiry + '|' + approval):
        return '암호화폐 감독·조사·승인 진행'
    settlement = r'\b(?:settle(?:s|d)?|settlement|clearing)\b|결제|정산|청산소'
    change = r'\b(?:can now|now supports?|launch\w*|enabl\w*|introduc\w*|rolls? out|adopt\w*)\b|도입|지원|개시|시작'
    if has(r'\b(?:stablecoins?|USDC|USDT|RLUSD)\b|스테이블코인') and has(settlement) and has(change):
        return '스테이블코인 결제·정산 도입'
    return ''


def regulatory_payment_intake_reason(story):
    if channel_scope_reason(story) not in ('암호화폐 감독·조사·승인 진행', '스테이블코인 결제·정산 도입'):
        return ''
    return _scope_intake_reason(story, REGULATORY_PAYMENT_ENABLED_AT, '감독·조사·결제')


def official_oversight_context(story):
    """Permit source review of attributed official findings, not wallet rumors."""
    title = str(story.get('title', '') or '')
    if regulatory_payment_scope_reason(title) != '암호화폐 감독·조사·승인 진행':
        return False
    source = str(story.get('article_text', '') or '')
    return bool(re.search(
        r'\b(?:Senate|subcommittee|regulator|Treasury|DOJ|SEC|CFTC)\b[^.\n]{0,160}'
        r'\b(?:released|published|filed|issued)\b[^.\n]{0,60}\b(?:report|findings|letter|complaint)\b|'
        r'(?:상원|소위원회|금융당국|검찰).{0,100}(?:보고서|조사\s*결과|서한).{0,30}(?:발표|공개|제출)', source, re.I))


def crypto_ipo_scope_reason(story):
    """Corporate IPO steps, not token listings or public-stock price cards."""
    title = str(story.get('title', '') or '')
    has = lambda p: bool(re.search(p, title, re.I))
    if has(r'주가|목표가|매수\s*추천|루머|소문|상장설|'
           r'\b(?:stock price|price target|price prediction|rumou?rs?|could|might)\b'):
        return ''
    company = (r'블록체인닷컴|코인베이스|크라켄|제미니|빗고|불리시|'
               r'(?:암호화폐|가상자산|디지털자산).{0,20}(?:기업|업체|거래소|수탁사)|'
               r'\b(?:Blockchain\.com|Coinbase|Kraken|Gemini|BitGo|Bullish)\b|'
               r'\b(?:crypto|digital[ -]asset)\b.{0,30}\b(?:firm|company|exchange|custodian)\b')
    ipo = r'기업공개|(?:증시|나스닥|뉴욕증권거래소)\s*상장|\bIPO\b|initial public offering|go(?:ing)? public'
    step = (r'추진|신청|제출|승인|공모|주관사|조달|(?:상장|기업공개|IPO)\s*(?:완료|철회|연기)|'
            r'\b(?:files?|filed|filing|plans?|planning|eyes?|seeks?|seeking|'
            r'announc\w*|rais\w*|approv\w*|complet\w*|launch\w*|withdraw\w*|postpon\w*)\b')
    return CRYPTO_IPO_SCOPE if has(company) and has(ipo) and has(step) else ''


def crypto_ipo_intake_reason(story):
    if channel_scope_reason(story) != CRYPTO_IPO_SCOPE:
        return ''
    return _scope_intake_reason(story, CRYPTO_IPO_ENABLED_AT, '암호화폐 기업공개')


def institutional_scope_reason(story, *, expanded=True):
    """Select institutional adoption, not token recommendations or event ads."""
    title = str(story.get('title', '') or '')
    has = lambda pattern: bool(re.search(pattern, title, re.I))
    if has(r'목표가|가격\s*전망|주가|배당|분배금|매수\s*추천|'
           r'\b(?:price target|price prediction|dividends?|stock price)\b|'
           r'(?:컨퍼런스|행사|포럼).{0,30}(?:참가|참석|연사|개최)|'
           r'\b(?:conference|summit|forum)\b.{0,40}\b(?:attend\w*|speaker|ticket\w*)\b'):
        return ''
    institution = (r'미래에셋|블랙록|피델리티|프랭클린\s*템플턴|제이피모건|JP모건|'
                   r'골드만삭스|모건스탠리|찰스슈왑|금융그룹|금융기관|은행|증권|자산운용|'
                   r'\b(?:Mirae Asset|BlackRock|Fidelity|Franklin Templeton|JPMorgan|'
                   r'Goldman Sachs|Morgan Stanley|Charles Schwab|banks?|brokerage|'
                   r'asset manager|asset management|financial institution)\b')
    subject = (r'디지털\s*자산|가상\s*자산|암호화폐|토큰화|온체인|실물연계자산|'
               r'\b(?:digital[ -]assets?|crypto|tokeni[sz]\w*|on[ -]?chain|RWA)\b')
    business = (r'사업|산업|금융\s*상품|상품\s*온체인화|토큰화|플랫폼|인프라|'
                r'\b(?:business|products?|tokeni[sz]\w*|platform|infrastructure|services?)\b')
    action = (r'본격화|진출|확대|추진|출시|도입|구축|설립|제휴|협력|계약|체결|'
              r'(?:전략|계획|사업|로드맵).{0,20}(?:발표|공개)|'
              r'\b(?:launch\w*|expand\w*|enter\w*|partner\w*|adopt\w*|'
              r'build\w*|develop\w*|plans?|announc\w*|unveil\w*)\b')
    if expanded:
        institution += r'|씨티그룹|시티그룹|스위프트|국제은행간통신협회|\b(?:Citigroup|Citi|SWIFT)\b'
        business += r'|예금|결제|담보|펀드|\b(?:deposits?|payments?|collateral|funds?|settlement)\b'
        action += (r'|통합|연결|지원|제공|담보\s*(?:채택|활용|인정)|'
                   r'\b(?:integrat\w*|connect\w*|brings?|brought|adds?|added|'
                   r'accept\w*|offers?|offered|enabl\w*|support\w*|taps?)\b')
    if has(institution) and has(subject) and has(business) and has(action):
        return INSTITUTIONAL_SCOPE
    return ''


def geopolitics_scope_reason(story):
    """Headline-only candidate selection, followed by the normal source review."""
    title = str(story.get('title', '') or '')
    has = lambda pattern: bool(re.search(pattern, title, re.I))
    if has(r'전망|예측|가능성|관측|낙관론|비관론|목표가|통신비|생활비|지도\s*게시|'
           r'\b(?:forecast|predict\w*|rumou?rs?|could|might|opinion|price target)\b'):
        return ''
    actor = (r'미국|중국|이란|이스라엘|러시아|우크라이나|북한|한국|일본|유럽연합|'
             r'트럼프|시진핑|백악관|외교부|국무부|안보리|유엔|나토|'
             r'\b(?:US|U\.S\.|China|Iran|Israel|Russia|Ukraine|Korea|Japan|EU|'
             r'Trump|Xi Jinping|White House|State Department|UN|NATO)\b')
    subject = (r'호르무즈|수에즈|홍해|해협|휴전|종전|평화\s*협상|핵무기|핵\s*협상|'
               r'관세|무역\s*(?:협상|합의|협정)|경제\s*제재|제재\s*(?:부과|해제|완화|강화)|'
               r'수출\s*(?:통제|규제)|정상\s*회담|군사\s*공격|미사일\s*공격|침공|'
               r'\b(?:Hormuz|Suez|Red Sea|Taiwan Strait|ceasefire|peace talks|'
               r'nuclear|tariffs?|trade talks|trade deal|sanctions?|export controls?|'
               r'summit|military strike|missile attack|invasion)\b')
    action = (r'합의|체결|서명|발표|공개|승인|발효|부과|철회|해제|중단|재개|'
              r'거부|수락|제안|조건\s*유지|공식\s*답변|개최|회담|공격\s*(?:개시|감행)|'
              r'\b(?:agree\w*|sign\w*|announc\w*|approv\w*|impos\w*|reject\w*|'
              r'accept\w*|propos\w*|resum\w*|reopen\w*|halt\w*|lift\w*|'
              r'hold\w*|maintain\w*|launch\w*|takes? effect)\b')
    if has(actor) and has(subject) and has(action):
        return GEOPOLITICS_SCOPE
    return ''


def geopolitics_intake_reason(story):
    """Avoid releasing the old queue when the editorial scope expands."""
    if channel_scope_reason(story) != GEOPOLITICS_SCOPE:
        return ''
    return _scope_intake_reason(story, GEOPOLITICS_ENABLED_AT, '국제정세')


def institutional_intake_reason(story):
    if channel_scope_reason(story) != INSTITUTIONAL_SCOPE:
        return ''
    # New matches have a separate cutoff; do not release old manual coverage.
    cutoff = (INSTITUTIONAL_ENABLED_AT if institutional_scope_reason(story, expanded=False)
              else INSTITUTIONAL_SERVICES_ENABLED_AT)
    return _scope_intake_reason(story, cutoff, '금융기관 디지털자산')


def _scope_intake_reason(story, enabled_at, label):
    value = str(story.get('pub', '') or '')
    try:
        try:
            published = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            published = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if published.tzinfo is None:
            return f'{label} 기사 발행 시각의 시간대 불명확'
        if published <= enabled_at:
            return f'{label} 범위 확대 전 기사: 과거 대기열 발송 방지'
    except (ValueError, TypeError, OverflowError):
        return f'{label} 기사 발행 시각 확인 불가'
    return ''


def manual_post_reason(story):
    try:
        parts = urlsplit(str(story.get('url', '') or ''))
        host = (parts.hostname or '').lower().removeprefix('www.')
    except ValueError:
        return ''
    rejected = EDITOR_REJECTED_ARTICLES.get((host, parts.path.rstrip('/')))
    if rejected:
        return rejected
    if (host, parts.path.rstrip('/')) in MANUALLY_POSTED_ARTICLES:
        return '사용자가 확인한 팀원 기존 게시 기사'
    return ''


def channel_scope_reason(story):
    """Allow relevant policy/use cases without requiring a portfolio ticker.

    Only the headline establishes the subject; incidental source paragraphs
    must not turn an unrelated story into channel news. This is not approval
    to publish: exclusions and source review still run.
    """
    title = str(story.get('title', '') or '')
    # A quote currency in an unrelated token listing is not its subject.
    title = re.sub(r'\b[A-Za-z0-9]+\s*[/_-]\s*(?:USDT|USDC|RLUSD)\b', '', title, flags=re.I)
    title = re.sub(r'(?:USDT|USDC|RLUSD|테더)\s*(?:마켓|거래쌍|페어)', '', title, flags=re.I)
    stablecoin = r'\bstablecoins?\b|\b(?:USDC|USDT|RLUSD|PYUSD|EURC|JPYC)\b|스테이블코인'
    crypto = r'crypto|digital.asset|bitcoin|blockchain|암호화폐|가상자산|디지털.?자산|비트코인|블록체인|' + stablecoin
    policy = r'licen[cs]|bitlicen[cs]e|regulat|legislat|\brules?\b|guidance|\bFAQs?\b|bill|charter|GENIUS|CLARITY|법안|라이선스|인가|규제|은행업|준비금|reserve|지침|유동성\s*요건'
    action = r'pass(?:es|ed)?|approv|grant|obtain|win[sn]?|propos|introduc|file|adopt|review|consider|\bweighs?\b|\bissues?\b|updat|clarif|검토|제안|발의|통과|승인|획득|도입|제출|공개|발표|개정|명확화'
    has = lambda pattern: bool(re.search(pattern, title, re.I))
    if has(r'stablecoin|스테이블코인') and has(r'pilot|실증') and has(r'launch|start|join|participat|출시|시작|착수|참여'):
        return '스테이블코인 실증 사업'
    if has(policy) and has(action) and (has(crypto) or has(r'GENIUS|CLARITY|지니어스|클래리티|BitLicense')):
        return '암호화폐 정책·법안·인가 진행'
    if has(stablecoin) and has(r'\bCircle\b|\bTether\b|\bPaxos\b|서클|써클|테더|팍소스|발행사|issuer') and has(r'\b(?:partners?|partnership|deal|agreement|investment)\b|\bgains?\b.{0,40}\bbacking\b|제휴|협약|계약|투자\s*유치'):
        return '스테이블코인 발행사 제휴·투자 계약'
    if has(crypto) and has(r'card|payment|settlement|custody|wallet|카드|결제|정산|수탁|지갑') and has(r'launch|integrat|partner|adopt|support|roll.?out|출시|통합|제휴|도입|지원'):
        return '암호화폐 실사용·결제 서비스'
    if has(r'K.?Bank|케이뱅크|Upbit|업비트') and has(r'bank|은행|계좌|입출금|결제|제휴|licen[cs]|라이선스|인가') and has(action + r'|launch|partner|출시|제휴'):
        return '거래소 연계 은행 서비스'
    if has(r'Jack Dorsey|잭\s*도시|잭\s*도르시') and has(r'\bBlock\b|블록') and has(r'\bAI\b|artificial intelligence|인공지능') and has(r'organization|hierarchy|management|조직|경영|구조'):
        return '블록의 AI 조직 개편'
    return (institutional_scope_reason(story) or crypto_ipo_scope_reason(story)
            or geopolitics_scope_reason(story) or regulatory_payment_scope_reason(title)
            or tax_reporting_scope_reason(title))


def quantity_followup_reason(story):
    """Block ongoing loss tallies even without prior channel-history access."""
    title = str(story.get('title', '') or '')
    lead = title + '\n' + str(story.get('desc', '') or '')
    security = r'hack|exploit|stolen|theft|drain|breach|해킹|탈취|유출|도난|피해'
    ongoing = r'continu(?:e|es|ed|ing)|ongoing|additional|another|more.{0,20}(?:stolen|drained)|누적|추가|계속|지속'
    action = r'arrest|indict|charg(?:e|ed|es)|recover|seiz|patch|fix(?:es|ed)?|resume|체포|기소|회수|압수|패치|수정|재개'
    if re.search(security, lead, re.I) and re.search(ongoing, lead, re.I) and not re.search(action, title, re.I):
        return '기존 유출·탈취 사건의 지속 경고·추가 피해 집계'
    return ''


def freshness_reason(story, now=None, max_age_hours=72):
    """Check publication time, never mistake an old date in background for freshness."""
    value = story.get('pub', '')
    if not value:
        return ''  # Missing publication date is handled by the source-based review.
    try:
        try:
            published = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            published = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if published.tzinfo is None:
            return '발행 시각의 시간대 불명확: 검토 필요'
        now = now or datetime.now(timezone.utc)
        if published > now + timedelta(hours=6):
            return '미래 발행 시각: 검토 필요'
        if now - published > timedelta(hours=max_age_hours):
            return '오래된 발행 기사: 새 사실 확인 필요'
    except (ValueError, TypeError, OverflowError):
        return '발행 시각 해석 실패: 검토 필요'
    return ''


def source_promotion_reason(story):
    """Explicit disclosure and conversion copy, including full article evidence."""
    text = '\n'.join(str(story.get(k, '') or '') for k in ('title','desc','article_text'))
    # Reporting an enforcement case about sponsored content is not an ad label.
    text = re.sub(r'(?i)\b(?:regulator|authority|court)\b[^.\n]{0,80}\b(?:investigated|banned|prohibited)\b[^.\n]{0,50}\bsponsored\s+content\b',
                  'reported advertising enforcement', text)
    disclosure = r'(?i)\b(?:sponsored\s+(?:content|article|post)|paid\s+(?:content|press release|advertisement)|advertorial)\b|유료\s*광고|협찬\s*(?:기사|콘텐츠)'
    conversion = r'(?i)(?:sign\s+up|register|가입|등록).{0,60}(?:referral\s+code|추천인\s*코드)|(?:use|enter|입력).{0,35}(?:referral\s+code|추천인\s*코드)'
    if re.search(disclosure, text):
        return '본문 광고·협찬 표시'
    if re.search(conversion, text):
        return '가입·추천인 유도'
    # Funding an educational activity is not a paid placement of this article.
    # Mask only explicit noun phrases, leaving ad disclosures elsewhere intact.
    education = r'(?:fellowships?|scholarships?|certifications?|research\s+grants?)'
    sponsorship_text = re.sub(r'\bsponsored\s+' + education + r'\b', 'education funding', text, flags=re.I)
    sponsorship_text = re.sub(r'\b' + education + r'\s+(?:(?:is|are|was|were)\s+)?sponsored\s+by\b',
                              'education funded by', sponsorship_text, flags=re.I)
    if re.search(r'\bsponsored\b', sponsorship_text, re.I):
        return '본문 광고·협찬 표시'
    return ''


def approval_stage_tokens(text):
    if not re.search(r'(?i)licen[cs]e|regulator|approval|승인|인가|라이선스', text):
        return set()
    stages = set()
    if re.search(r'(?i)preliminary|in[- ]principle|provisional|예비\s*승인|원칙적\s*승인', text):
        stages.add('stage_approval_preliminary')
    if re.search(r'(?i)(?:final|full)\s+(?:regulatory\s+)?(?:approval|licen[cs]e)|정식\s*(?:승인|인가|라이선스)|최종\s*승인', text):
        stages.add('stage_approval_final')
    # Both can occur in an article describing progress: its latest explicit stage wins.
    return {'stage_approval_final'} if 'stage_approval_final' in stages else stages


def event_conflicts(cur, old):
    for prefix in ('stage_approval_', 'reference_version_', 'reference_eip_', 'reference_bip_'):
        a = {t for t in cur if t.startswith(prefix)}
        b = {t for t in old if t.startswith(prefix)}
        if a and b and a.isdisjoint(b):
            return True
    return False


def quantity_only_update(cur, old):
    """Quantity changes alone do not earn another post; retain stage/version anchors."""
    # Different loan contracts or vulnerabilities must not become the same
    # event solely because this representation happens to share entity tokens.
    if not {'object_corporate_crypto_purchase', 'object_etf_holdings'} & (cur & old):
        return False
    prefixes = ('amount_', 'count_')
    quantities_a = {t for t in cur if t.startswith(prefixes)}
    quantities_b = {t for t in old if t.startswith(prefixes)}
    core_a, core_b = cur - quantities_a, old - quantities_b
    return bool(
        quantities_a and quantities_b and quantities_a != quantities_b
        and core_a == core_b
        and any(t.startswith('entity_') for t in core_a)
        and any(t.startswith('action_') for t in core_a)
        and any(t.startswith('object_') for t in core_a)
    )


class CaptionParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]; self.stack=[]; self.valid=True
    def handle_starttag(self, tag, attrs):
        if tag != 'a' or self.stack or not dict(attrs).get('href', '').startswith(('http://','https://')):
            self.valid=False
        self.stack.append(tag)
    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop()!=tag:
            self.valid=False
    def handle_data(self, data):
        self.parts.append(data)


def valid_caption(caption):
    """Conservative UTF-16 bound on visible text; preserve complete HTML and tags."""
    parser=CaptionParser()
    try:
        parser.feed(caption); parser.close()
    except Exception:
        return False
    return parser.valid and not parser.stack and len(''.join(parser.parts).encode('utf-16-le'))//2 <= 1024
