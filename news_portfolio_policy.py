"""User's portfolio editorial preference; no model or network calls."""
import re

POLICY = 'portfolio-adverse-20261010-1'

GUIDANCE = '''
최우선 사용자 편집 기준(2026-10-10): 도리 포트폴리오 코인 자체, 발행사 또는 해당 네트워크의 악재가 핵심인 기사는 게시하지 않는다.
대상: BTC/비트코인, ETH/이더리움, XRP/리플/XRP레저, XLM/스텔라, ADA/카르다노, TRX/트론, BNB/바이낸스코인, BCH/비트코인캐시, SHIB/시바이누/시바리움, ETC/이더리움클래식, FLR/플레어, ENA/에테나, ATHENA/아테나, USDC, USDT.
이 코인·발행사·네트워크의 취약점·해킹·오류 악용·무단 발행·네트워크 중단·디페깅·지급불능·사기 의혹·불리한 판결·상장폐지·비관적 전망 등 부정적인 사건/주장이 기사 핵심이면 SKIP. 원문 검사에서는 allowed_category=false 및 publish=false.
수정판 배포, 패치 완료, 실제 악용 증거 없음 등이 함께 있어도 기사의 중심이 해당 취약점이나 악재 공개이면 제외한다. 부정적인 내용을 삭제하여 보안 강화·업그레이드 호재처럼 바꿔 게시하지 않는다.
사진 예시: XRP레저의 탈중앙화 거래소 결제 계산 오류로 총공급량 초과 XRP가 생성될 수 있는 취약점 공개는 xrpld 3.4.1 배포 및 악용 증거 없음이 함께 있어도 제외한다.
기사의 주제와 피해 대상을 구별한다. 일반 거시경제·과세·수사 기사에 BTC가 배경으로 나오거나, 제3자 거래소·지갑 피해 자산이 BTC라는 이유만으로 비트코인 네트워크 자체의 악재라고 판단하지 않는다. 바이낸스 거래소의 합의 조사도 BNB 자체·체인에 대한 악재 보도와 구별한다. 고정 하단 BTC 태그는 판단 근거가 아니다.
평범한 보안 개선·기능 업그레이드·위험 예방 기능 출시가 중심이고 현재 또는 공개된 취약점/사고가 핵심이 아니면 이 기준만으로 제외하지 않는다. 채택·제휴·사용 확대도 기존 사실·조건 검사를 거쳐 심사한다. 불명확하면 원문을 근거로 보류하고 호재로 추정하지 않는다.
이 기준은 앞의 보안·기업·인물 발언 허용 예외보다 우선한다. 원문에 없는 효과나 가격 상승을 만들지 않는다.
'''


def adverse_portfolio_reason(story, asset_finder):
    """Conservative cheap headline gate; ambiguous body context uses source review.

    Never scan channel footer tags. A ticker in background/third-party losses
    isn't proof that the token or its own network is the subject of the harm.
    """
    title = str(story.get('title', '') or '')
    assets = set(asset_finder(title))
    assets.update(re.findall(r'\b(?:USDC|USDT|ATHENA)\b', title, re.I))
    if not assets:
        return ''
    # Reserve third-party exchange/wallet incidents for semantic source review.
    external = r'^(?:Ledger|레저)(?![A-Za-z])|Coldcard|콜드카드|Trezor|트레저|CryptoBilis|크립토빌리스|하드웨어\s*지갑|hardware wallet|거래소.*(?:해킹|조사)|exchange.*(?:hack|investigat)'
    if re.search(external, title, re.I):
        return ''
    if re.search(r'vulnerability (?:detection|scanner|prevention)|취약점\s*(?:탐지|예방)\s*(?:도구|기능)|'
                 r'denies|debunks|no security flaw|부인|반박|사실무근', title, re.I):
        return ''  # Context-sensitive reporting belongs to the source review.
    technical = r'취약점|보안\s*결함|계산\s*오류|무단\s*발행|공급량.{0,12}초과|네트워크\s*중단|체인\s*중단|vulnerabilit\w*|security flaw|unauthorized mint\w*|network outage|consensus failure'
    # Explicit technical defects tied to a portfolio headline are sufficient;
    # a "patched" qualifier does not negate the vulnerability's subject.
    if re.search(technical, title, re.I):
        return '도리 포트폴리오 악재 중심: 취약점·네트워크 결함'
    direct = r'^\s*(?:\[[^\]]{1,20}\]\s*)?#?(?:XRP|XRPL|Ripple|Bitcoin|BTC|Ethereum|ETH|Stellar|XLM|Cardano|ADA|Tron|TRX|BNB|BCH|SHIB|ETC|Flare|FLR|Ethena|ENA|ATHENA|USDC|USDT|리플|비트코인|이더리움|스텔라|카르다노|에이다|트론|바이낸스코인|시바이누|시바리움|플레어|에테나|아테나)(?![A-Za-z0-9])'
    adverse = r'디페깅|페그\s*붕괴|지급불능|상장\s*폐지|사기\s*의혹|패소|해킹|탈취|급락|붕괴|depeg\w*|insolven\w*|delist\w*|fraud allegation|loses lawsuit|hack(?:ed|ing)|crash\w*|collaps\w*'
    # Negated allegations should be judged as a whole, not by this keyword gate.
    negated = r'부인|반박|사실무근|무혐의|기각|denies|debunks|dismisses|not hacked|no depeg'
    if re.search(direct, title, re.I) and re.search(adverse, title, re.I) and not re.search(negated, title, re.I):
        return '도리 포트폴리오 악재 중심'
    return ''
