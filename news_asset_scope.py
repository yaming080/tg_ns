"""Reject outside-portfolio project adoption disguised by collateral tickers."""
import re

POLICY = 'asset-subject-20261010-1'
# Distinct project names; ambiguous English words/tickers (LINK, OP, NEAR,
# DOT, PI) deliberately require semantic review rather than substring matching.
OUTSIDE_PROJECTS = (
    ('SUI', r'Sui|수이'), ('SOL', r'Solana|솔라나'),
    ('DOGE', r'Dogecoin|도지코인'), ('AVAX', r'Avalanche|아발란체'),
    ('DOT', r'Polkadot|폴카닷'), ('POL', r'Polygon|폴리곤'),
    ('LINK', r'Chainlink|체인링크'), ('LTC', r'Litecoin|라이트코인'),
    ('ATOM', r'Cosmos|코스모스'), ('ARB', r'Arbitrum|아비트럼'),
    ('OP', r'Optimism|옵티미즘'), ('APT', r'Aptos|앱토스'),
    ('HYPE', r'Hyperliquid|하이퍼리퀴드'), ('HBAR', r'Hedera|헤데라'),
    ('INJ', r'Injective|인젝티브'), ('TIA', r'Celestia|셀레스티아'),
)

GUIDANCE = '''
최우선 포트폴리오 범위 보완: 코인 이름이 등장하는지와 새 소식의 주체를 구별하라.
도리 포트폴리오는 BTC, ETH, XRP, XLM, ADA, TRX, BNB, BCH, SHIB, ETC, FLR, ENA, ATHENA, USDC, USDT다. 수이(SUI)는 포트폴리오가 아니다.
수이 등 포트폴리오 밖 코인·체인의 자체 사업, 채택, 제휴, 플랫폼·메인넷 출시, 자금 유치, 생태계 확대가 기사의 중심이면 제외한다. BTC 담보·비트코인 보유 기업·USDC 결제·ETH 거래 지원이 나온다는 것만으로 포트폴리오 기사로 허용하지 않는다.
구체적 제외 예: Bitcoin treasury companies get two Anchorage routes into Sui's Hashi. BTC를 팔지 않고 현금을 조달하는 내용이어도 수이 해시 플랫폼의 신규 참여·도입이 중심이므로 SKIP. 수이 이름을 지우고 BTC 금융 서비스 뉴스처럼 바꾸면 안 된다.
제목에 수이가 없어도 원문에서 해당 서비스가 수이 체인의 생태계 확대임이 드러나면 같은 기준을 적용한다. 본문뿐 아니라 제목·원문을 함께 보고 판단한다.
원문 검토에서는 위 범주이면 allowed_category=false, publish=false. 기관 채택·결제·토큰화의 일반 허용 규칙보다 이 제한이 우선한다. 발행사/기업이 유명하다는 이유로 예외를 만들지 않는다.
반면 ETH 기관 스테이킹 서비스에 SOL도 함께 지원되는 경우처럼 포트폴리오 자산의 직접적인 새 서비스가 주제이고 비포트폴리오 코인은 병렬 지원 대상에 불과한 경우는 원문으로 확인해 심사한다. 포트폴리오 프로토콜 자체의 새 기능·제휴를 다른 체인 이름이 배경에 나온다는 이유만으로 제외하지 않는다.
일반 규제·거시경제·금융기관 뉴스가 중심이면 코인 이름 없이도 기존 범위에 따라 심사한다. 하단의 고정 BTC 해시태그는 기사 선정 근거가 아니다. 암호화폐 관련성이 불분명하거나 새 사업 주체를 확인할 수 없으면 보류한다.
'''


def outside_project_reason(story):
    """High precision project ownership/adoption gate, before model calls.

    Parallel asset support is intentionally not a blanket blacklist. Broader
    context is handled by the existing source review with GUIDANCE above.
    """
    title = str(story.get('title', '') or '')
    for symbol, names in OUTSIDE_PROJECTS:
        name = r'(?<![A-Za-z0-9가-힣])(?:' + names + r')(?![A-Za-z0-9])'
        if not re.search(name, title, re.I):
            continue
        ownership = name + r"(?:['’]s\s+|의\s*|\s+기반\s*)"
        destination = r'\b(?:into|via|through|built on|powered by)\s+' + name
        adoption = r'launch|mainnet|platform|ecosystem|partner|adopt|routes?|treasury|collateral|출시|메인넷|플랫폼|생태계|제휴|도입|참여|담보|금융망|서비스'
        if re.search(r'^\s*(?:\[[^\]]+\]\s*)?' + name, title, re.I) and re.search(adoption, title, re.I):
            return f'포트폴리오 외 {symbol} 사업·채택 중심'
        if (re.search(ownership, title, re.I) or re.search(destination, title, re.I)) and re.search(adoption, title, re.I):
            return f'포트폴리오 외 {symbol} 플랫폼·생태계 도입 중심'
        # Explicit "USDC launches on Sui" expands the outside chain, not USDC itself.
        on_chain = (r'\b(?:on|to)\s+' + name + r'(?:\b|\s+network)|' + name + r'(?:에서|에)\s*.{0,35}(?:출시|도입|배포)')
        if re.search(on_chain, title, re.I) and re.search(r'launch|deploy|expand|출시|도입|배포', title, re.I):
            return f'포트폴리오 외 {symbol} 체인 서비스 도입 중심'
    return ''
