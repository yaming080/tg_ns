"""Team-reviewed screenshots, Oct 23–29, 2026. Exact removals are not topic bans.
Evidence: ChatExport_2026-10-29 photos 4485–4524, matched to posted state.
Mixed duplicate/tag feedback is not interpreted as explicit deletion.
"""
REJECTED = {'cointelegraph.com/news/sofi-bank-issued-tokenized-deposit-yield-bearing-crypto-funds?utm_source=rss_feed&utm_medium=rss&utm_campaign=rss_partner_inbound': '팀원 '
                                                                                                                                                             '불필요 '
                                                                                                                                                             '기사 '
                                                                                                                                                             '삭제 '
                                                                                                                                                             '— '
                                                                                                                                                             'SoFi '
                                                                                                                                                             'Earn '
                                                                                                                                                             '예금 '
                                                                                                                                                             '상품',
 'www.theblock.co/news/defi/2026-10-22-uniswaps-aggregator-hooks-go-live-ethereum-base-robinhood-chain-421932': '팀원 '
                                                                                                                '불필요 '
                                                                                                                '기사 '
                                                                                                                '삭제 '
                                                                                                                '— '
                                                                                                                '유니스왑 '
                                                                                                                '애그리게이터 '
                                                                                                                '훅',
 'cointelegraph.com/news/hsbc-launches-redcoin-hong-kong-dollar-stablecoin-payme?utm_source=rss_feed&utm_medium=rss&utm_campaign=rss_partner_inbound': '팀원 '
                                                                                                                                                       '중복·보충 '
                                                                                                                                                       '기사 '
                                                                                                                                                       '삭제/이동 '
                                                                                                                                                       '— '
                                                                                                                                                       'HSBC '
                                                                                                                                                       'RedCoin '
                                                                                                                                                       '지갑 '
                                                                                                                                                       '순차 '
                                                                                                                                                       '제공',
 'bloomingbit.io/feed/news/122858': '팀원 중복·보충 기사 삭제/이동 — 프랭클린템플턴 sgBENJI 추가 발행',
 'crypto.news/tether-15-bitcoin-mining-firms-ai-automation-mdk': '팀원 중복·보충 기사 삭제/이동 — 테더 MDK 채굴 협력',
 'www.tokenpost.kr/news/cryptocurrency/427298': '팀원 불필요 기사 삭제 — Utexo 기관용 비트코인 브리지 USDT',
 'news.bitcoin.com/featured/ripple-wins-final-us-bank-charter-ceo-calls-it-big-news-ahead-of-swell': '팀원 '
                                                                                                     '중복·보충 '
                                                                                                     '기사 '
                                                                                                     '삭제/이동 '
                                                                                                     '— 리플 '
                                                                                                     'OCC 최종 '
                                                                                                     '은행 인가',
 'bloomingbit.io/feed/news/123015': '팀원 중복·보충 기사 삭제/이동 — 블랙록·SBI·스타테일 JPYSC·MMF 협약',
 'cryptobriefing.com/binance-files-brazil-crypto-license': '팀원 중복·보충 기사 삭제/이동 — 바이낸스 브라질 라이선스 신청',
 'bloomingbit.io/feed/news/123046': '팀원 중복·보충 기사 삭제/이동 — 반에크 웰스빌더 ETF',
 'news.bitcoin.com/finance/major-banks-sign-on-as-dtcc-launches-tokenized-securities-service': '팀원 중복·보충 기사 '
                                                                                               '삭제/이동 — DTCC '
                                                                                               '같은 출시의 20개 '
                                                                                               '참여사 계약 설명',
 'crypto.news/google-crypto-custody-mpc-security-2027': '팀원 중복·보충 기사 삭제/이동 — 구글 멀티파티 컴퓨트 2027 계획'}

EVENTS = (('https://cointelegraph.com/news/hsbc-launches-redcoin-hong-kong-dollar-stablecoin-payme?utm_source=rss_feed&utm_medium=rss&utm_campaign=rss_partner_inbound',
  'HSBC launches Hong Kong dollar stablecoin for retail payments',
  '#HSBC 가 홍콩달러 #스테이블코인 레드코인 지갑을 페이미 이용자에게 순차 제공하고 있으며, #토큰화 투자 상품 청약 지원과 기관용 활용으로 확대할 계획임'),
 ('https://www.tokenpost.kr/news/blockchain/426844',
  '스텔라서 USDM1 담보 기관 repo 72시간 거래',
  '어센드마켓츠와 엠원엑스 글로벌이 10월 16~19일 스텔라 네트워크에서 디지털 국채 USDM1을 담보로 #USDC 를 결제 자산으로 쓴 기관 간 환매조건부채권(repo·담보를 맡기고 자금을 '
  '조달한 뒤 약정에 따라 다시 매입하는 거래)을 72시간 진행했으며, 원금과 참여 기관은 공개하지 않음'),
 ('https://bloomingbit.io/feed/news/122858',
  '프랭클린템플턴, XRP레저에 1억5000만달러 규모 토큰화 펀드 추가 발행',
  '#프랭클린템플턴 이 10월 22일 #XRP 레저에서 #싱가포르 설정 머니마켓펀드 지분 #토큰 sgBENJI 약 1억5000만달러어치를 추가 발행함\n'
  '\n'
  '해당 #펀드 의 XRP레저 발행량은 약 4800만개에서 1억9300만개로 늘었으며, 새 토큰은 한 지갑에 모였지만 단일 투자자 소유인지는 확인되지 않음'),
 ('https://news.bitcoin.com/regulation-and-legal/senator-probes-tether-reported-6m-deal-ex-trump-crypto-advisor',
  'Senator Probes Tether’s Reported $6M Deal With Firm Tied to Ex-Trump Crypto Advisor',
  '민주당 리처드 블루멘털 상원의원이 #테더 와 보 히인스 전 #백악관 디지털자산 자문관이 공동 설립한 컨설팅사 넥섬의 관계를 조사하며 계약서와 암호화폐 지급 기록 등을 요구함\n'
  '\n'
  '테더가 넥섬에 약 630만 달러를 지급했다는 보도와 관련한 자료 요청이며, 두 회사는 11월 6일까지 답변해야 하고 위법 사실은 확인되지 않음'),
 ('https://www.tokenpost.kr/news/cryptocurrency/426849',
  '카돈, 부동산·비트코인 결합 거래 7건 진행',
  '그랜트 카돈이 임대 부동산 현금흐름으로 BTC를 매입하는 부동산·비트코인 결합 거래 7건을 진행했다고 말했으며, 카돈 캐피털이 제시한 15~50% 편입 범위는 #펀드 의 실제 보유 비중이 '
  '아님'),
 ('https://news.bitcoin.com/featured/interpol-africa-sweep-nets-1462-arrests-exposes-crypto-laundering',
  'Interpol Africa Sweep Nets 1,462 Arrests, Exposes Crypto Laundering',
  '인터폴이 아프리카 20개국과 #미국 이 참여한 사이버범죄 단속 작전으로 용의자 1,462명을 체포하고 1억500만 달러 이상을 회수했으며, 나이지리아 투자 사기 수사에서는 범죄수익 의심 '
  '자금 240만 달러 이상이 추적됐고 상당액이 암호화폐 거래로 세탁된 정황이 확인됨\n'
  '\n'
  '작전은 6월 29일부터 8월 31일까지 진행됐으며, 앙골라에서는 불법 암호화폐 채굴 시설 2곳을 적발해 용의자 9명을 체포하고 채굴기 2,000대 이상을 압수함'),
 ('https://www.tokenpost.kr/news/policy/427126',
  '가상자산 과세, 첫 정보교환 2년 뒤로…연동 법안 발의',
  '더불어민주당 박민규 의원 등 14명이 국제 암호자산 거래정보의 첫 교환 시점에 연동해 암호화폐 과세를 시행하는 소득세법 개정안을 발의함\n'
  '\n'
  '첫 정보교환이 2027년에 이뤄지고 법안이 통과되면 과세는 2029년 1월 1일부터 시작되며, #한국 의 교환 시점과 법안 통과 여부는 아직 정해지지 않음'),
 ('https://www.tokenpost.kr/news/blockchain/427227',
  '리도, 2048 ETH 검증인 경로 열어…초기 배정은 32 ETH',
  '#리도 가 검증인 한 명의 유효 잔액을 최대 2048 #이더리움 까지 지원하는 0x02 커뮤니티 #스테이킹 모듈을 가동함\n'
  '\n'
  '초기에는 검증인 키마다 32 ETH를 배정해 활성화 절차를 진행하고, 이후 추가 지분을 배정함\n'
  '\n'
  '추가 지분 대기열은 출시 시점에 32석으로 제한되며, 모듈 배정 지분 한도는 리도 코어 총예치액의 0.01%임\n'
  '\n'
  '유효 잔액은 이더리움 합의 과정에 반영되는 검증인 잔액임'),
 ('https://crypto.news/tether-15-bitcoin-mining-firms-ai-automation-mdk',
  'Tether wins backing from 15 Bitcoin mining firms for AI automation tools',
  '#테더 가 비트코인 채굴업체·장비 제조사·채굴풀 15곳과 오픈소스 채굴 개발 도구 MDK의 연동 소프트웨어를 개발·유지하기로 함\n'
  '\n'
  'MDK는 서로 다른 채굴 장비와 서비스를 공통 시스템으로 연결하며, 테더의 QVAC 채굴 에이전트가 이미 작동 중이고 정식 버전 1.0은 2026년 말 출시를 목표로 함'),
 ('https://bloomingbit.io/feed/news/122895',
  'ECB "디지털 유로, 유럽 결제 주권 확보 핵심"…내년 시범사업 추진',
  '#유럽중앙은행(ECB) 집행이사 피에로 치폴로네는 디지털 유로 도입으로 역외 결제업체 의존을 낮추고 유럽의 결제 주권을 확보해야 한다는 입장을 밝힘\n'
  '\n'
  'ECB는 내년 시범사업에서 ECB와 각국 중앙은행 직원이 실제 거래에 참여하고, 시장 참여자 36곳과 준비 작업을 진행할 계획이며 정식 발행 여부는 관련 법안 확정 후 결정함'),
 ('https://news.bitcoin.com/regulation-and-legal/from-stripe-to-bitcoin-card-fraud-case-ends-in-prison-sentence',
  'From Stripe to Bitcoin: Card Fraud Case Ends in Prison Sentence',
  '미 법무부가 무단 신용카드 결제금을 은행 계좌와 #코인베이스 를 거쳐 비트코인으로 바꿔 공범에게 보낸 티모시 워즈워스에게 징역 51개월을 선고했다고 발표함\n'
  '\n'
  '워즈워스는 #스트라이프 를 통해 310건, 총 167만 달러 상당의 결제를 시도했으며, 법원은 배상금 81만965.19달러와 범죄수익 81만956.19달러의 몰수를 명령함'),
 ('https://crypto.news/ripple-aviva-investors-sterling-fund-xrp-ledger',
  'Ripple brings Aviva Investors’ £22B fund share class to XRP Ledger',
  '아비바 인베스터스가 적격 투자자를 대상으로 220억 파운드 규모 스털링 #유동성 #펀드 의 #토큰화 지분 클래스를 #XRP 레저에서 출시하고 5,000만 파운드를 투자함\n'
  '\n'
  '220억 파운드는 기존 펀드의 운용자산 규모이며 블록체인에 이전된 금액이 아님'),
 ('https://news.bitcoin.com/blockchain/binance-founder-cz-backs-bnb-chain-new-high-speed-layer-1-network',
  'Binance Founder CZ Backs BNB Chain’s New High-Speed Layer 1 Network',
  '#바이낸스코인 체인이 메인 네트워크와 병행 운영할 고속 레이어1 네트워크를 준비함\n'
  '\n'
  '새 네트워크는 EVM 호환을 지원하고, 가스비· #스테이킹·거버넌스에 BNB를 사용하며 별도 #토큰 은 발행하지 않을 계획임'),
 ('https://bloomingbit.io/feed/news/122989',
  '美 OCC, 지역은행에 스테이블코인 발행 참여 독려…내년 1월 규제 시행',
  '#미국 통화감독청(#OCC)이 지역은행에 직접 또는 자회사를 통해 허가받은 결제용 #스테이블코인 발행기관이 되는 방안을 검토하라고 권고함\n'
  '\n'
  'OCC는 #지니어스법 시행 규칙을 확정했으며, 법은 내년 1월부터 시행될 예정임'),
 ('https://news.bitcoin.com/featured/ripple-wins-final-us-bank-charter-ceo-calls-it-big-news-ahead-of-swell',
  'Ripple Wins Final US Bank Charter: CEO Calls It ‘Big News’ Ahead of Swell',
  '#리플 이 #미국 내 내셔널 트러스트 뱅크 설립에 대한 연방 최종 승인을 받아 영업을 시작할 수 있게 됐으며, 해당 기관은 미국 은행 감독을 받게 됨\n'
  '\n'
  '리플은 이를 바탕으로 #RLUSD 준비금 관리와 기업 대상 암호화폐 #수탁 사업을 추진함'),
 ('https://bloomingbit.io/feed/news/123015',
  '"블랙록·SBI·스타테일, 토큰화 MMF와 엔화 스테이블코인 연계 추진"',
  '#블랙록, #SBI 홀딩스, 스타테일그룹이 SBI의 엔화 #스테이블코인 JPYSC와 #토큰화 머니마켓펀드(MMF)를 연계하는 방안을 검토하기로 하고 양해각서(MOU)를 체결함\n'
  '\n'
  '세 회사는 기술·인프라, 사업·유통, #규제·시장 개발을 검토하며, 협력에는 #일본 안팎의 금융기관과 기업도 참여할 수 있음'),
 ('https://cryptobriefing.com/binance-files-brazil-crypto-license',
  'Binance files for Brazil crypto license ahead of October 30 deadline',
  '#바이낸스 가 #브라질 현지 법인 비브라질을 통해 암호화폐 서비스 제공업자 라이선스를 신청했으며, 10월 30일 신청 마감일까지 심사가 이어지는 동안 영업을 계속할 수 있음\n'
  '\n'
  '바이낸스는 10월 27일부터 브라질 이용자 대상 #토큰 22종의 거래를 중단하고 대출·마진 거래·클라우드 채굴 등 상품 8종을 제한했으며, 기존 포지션은 축소하거나 종료할 수 있음'),
 ('https://www.tokenpost.kr/news/blockchain/428206',
  '라이트닝 랩스, 비트코인 결제 도구 웨이브렝스 메인넷 공개',
  '라이트닝 랩스가 이용자가 개인 키를 직접 관리하는 지갑에 비트코인 결제를 연결하는 도구 웨이브렝스를 시험망 알파 공개에 이어 실제 비트코인 네트워크인 메인넷에 공개함\n'
  '\n'
  '이용자는 별도 라이트닝 노드 운영이나 결제 채널· #유동성 관리 없이 비트코인을 보내고 받을 수 있으며, #스테이블코인 지원은 향후 계획으로 구체적인 출시일은 정해지지 않음'),
 ('https://news.bitcoin.com/stablecoins/mexican-peso-stablecoin-gains-anchorage-custody-ethereum',
  'Mexican Peso Stablecoin Gains Anchorage Custody on Ethereum and Beyond',
  '#앵커리지디지털 은행이 비트소와 협력을 확대해 멕시코 페소 #스테이블코인 MXNB의 #수탁 을 #아비트럼·베이스· #이더리움 · #폴리곤·아발란체· #아크 등 6개 블록체인에서 지원함\n'
  '\n'
  '비트소는 웨스턴유니언 발행 USDPT와 #테더 발행 USAT를 추가했으며, 멕시코 고객은 앱에서 페소로 USDPT를 사고팔 수 있고 비트소 비즈니스 계정을 이용하는 웨스턴유니언 대리점은 '
  'USDPT를 지원 통화로 교환할 수 있음'),
 ('https://bloomingbit.io/feed/news/123046',
  '반에크, 주식·채권·실물자산·비트코인 투자 통합 ETF 출시',
  '반에크가 주식·채권·실물자산과 비트코인(BTC)에 함께 투자하는 상장지수펀드(#ETF) ‘웰스 빌더 ETF’를 출시함'),
 ('https://www.tokenpost.kr/news/cryptocurrency/428503',
  '시큐리타이즈, 스텔라 지원망에 추가…토큰화 선택지 넓혀',
  '시큐리타이즈가 기관용 자산 #토큰화 플랫폼의 지원 블록체인에 스텔라를 추가해 발행사가 토큰화 자산의 기반망으로 선택할 수 있게 함\n'
  '\n'
  '토큰화는 주식·채권· #펀드 등의 권리나 가치를 블록체인 기반 #토큰 으로 발행·관리하는 방식임\n'
  '\n'
  '스텔라 기반 상품이나 출시 일정은 발표되지 않음'),
 ('https://bloomingbit.io/feed/news/123116',
  '美 DTCC, 증권 토큰화 서비스 출시…비트고·블록데몬 등 협력사 선정',
  '#미국 증권예탁결제원(#DTCC)이 #증권 34종을 대상으로 #토큰화 서비스를 출시함\n'
  '\n'
  '#토큰 은 미국 중앙예탁기관(DTC)이 보관하는 증권과 1대1 연동되며, 보유자는 기초 증권과 같은 법적·경제적 권리를 가짐\n'
  '\n'
  '초기 지갑·앱 협력사에는 #비트고·블록데몬·파이어블록스· #해시키 가 포함됨'),
 ('https://news.bitcoin.com/finance/major-banks-sign-on-as-dtcc-launches-tokenized-securities-service',
  'Major Banks Sign on as DTCC Launches Tokenized Securities Service',
  '#미국 예탁결제기관 #DTCC 가 적격 기관이 예탁결제회사(DTC)에 보관된 #증권 을 블록체인 #토큰 으로 전환·이전할 수 있는 #토큰화 서비스를 출시함\n'
  '\n'
  '#JP모건 · #뱅크오브아메리카 등 20개 DTC 참여사가 서비스 이용 계약을 맺었으며, 증권은 기존 보관 체계에 남고 DTCC의 114조 달러 규모 관리 자산 전체가 블록체인으로 옮겨가는 '
  '것은 아님'),
 ('https://bloomingbit.io/feed/news/123114',
  '브라질 최대 은행, 암호화폐 거래·수탁 사업 추진…현지 최초',
  '#브라질 최대 은행 이타우 우니방쿠가 10월 27일 암호화폐 거래· #수탁 사업 추진을 브라질 중앙은행에 신고했으며, 서비스를 개시하면 현지 은행권 최초 사례가 됨'),
 ('https://cryptopotato.com/more-xrp-evernorth-makes-its-next-move-after-nasdaq-debut-with-80-7m-funding-plan',
  'More XRP? Evernorth Makes Its Next Move After Nasdaq Debut With $80.7M Funding Plan',
  '#에버노스 가 캔터 피츠제럴드와 8,070만 달러 규모의 지분 조달 계약을 마련해 나스닥 데뷔 이후 #XRP 추가 매입을 추진함'),
 ('https://cryptopotato.com/mirae-asset-securities-and-grvt-collaborate-on-tokenised-funding-note-issuance',
  'Mirae Asset Securities and Grvt Collaborate on Tokenised Funding Note Issuance',
  '미래에셋증권 #홍콩 자회사와 그르브트가 #토큰화 자금조달 채권 발행을 위한 협력에 나섰으며, 그르브트는 우선 해당 채권에 투자하고 향후 토큰화 국채·회사채· #ETF 도 #규제 요건에 따라 '
  '검토할 예정임'),
 ('https://www.tokenpost.kr/news/cryptocurrency/428608',
  '에테나 페이, 달러 예치 기능 출시…최대 12% 수익률 제시',
  '#에테나 페이가 달러 예치 기능 ‘Earn+’를 출시했으며, 프로·VIP 이용자에게 먼저 제공하고 며칠 안에 전체 이용자로 순차 확대할 계획임'),
 ('https://cryptobriefing.com/tether-launches-fase-foundation-stablecoin-aid',
  'Tether launches FASE Foundation to fight scams and pilot stablecoin aid',
  '#테더 가 스위스 비영리단체 금융 접근 및 시스템 역량 강화 재단(FASE)을 출범함\n'
  '\n'
  '재단은 11개 창립 주체와 유엔마약범죄사무소를 전략 파트너로 두고, 아프리카·라틴아메리카·동남아시아 청소년의 디지털 안전 교육, 인신매매 생존자 지원, 약 100만 명을 대상으로 한 '
  '#스테이블코인 기반 인도주의 지원 시범사업을 추진함'),
 ('https://thecryptobasic.com/2026/10/28/cardano-community-weighs-9-6-million-ada-proposal-to-expand-blockchain-based-police-evidence-system',
  'Cardano Community Weighs 9.6 Million ADA Proposal to Expand Blockchain-Based Police Evidence System',
  '트리볼브 테크와 #카르다노 재단이 #인도 경찰 증거 관리 시스템을 확대하기 위해 960만 ADA 지원안을 제출했으며, 블록체인에는 증거 파일이 아닌 위·변조 확인용 지문을 기록하는 방식임\n'
  '\n'
  '안이 승인되면 텔랑가나주에 처음 도입될 예정이며, 11월 20일까지 대의원 투표에서 67%의 찬성을 얻어야 함'),
 ('https://cryptobriefing.com/coinbase-adds-ripple-usd-support-boosting-stablecoins-accessibility',
  'Coinbase adds Ripple USD support, boosting stablecoin’s accessibility',
  '#코인베이스 와 코인베이스 프라임이 #리플 의 #스테이블코인 #RLUSD 지원을 추가해 #미국 달러와 1:1 전환을 지원함'),
 ('https://crypto.news/google-crypto-custody-mpc-security-2027',
  'Google previews crypto custody security system ahead of 2027 launch',
  '#구글 이 개인키 서명 권한을 여러 컴퓨팅 환경에 나눠 관리하는 기관용 암호화폐 보안 서비스 ‘구글 멀티파티 컴퓨트’를 금융기관 몇 곳과 비공개 시험 중임\n'
  '\n'
  '상용 제공은 시험 프로그램 완료를 전제로 2027년 초를 목표로 하며, 참여 기관과 가격은 공개되지 않음'),
 ('https://bloomingbit.io/feed/news/123143',
  '美 연준 의장 "내년 가을 FOMC 일정 개편…2028년 금리 결정 회의 6회로"',
  '케빈 워시 #미국 #연준 의장이 2027년 가을부터 연방공개시장위원회(#FOMC) 일정을 개편하고, 연 8회 회의 중 한 차례는 금리 표결 없이 통화정책 전략 논의에 집중할 계획이라고 '
  '밝힘\n'
  '\n'
  '2028년에는 기준금리를 결정하는 회의를 6차례 열 것으로 예상함'),
 ('https://blockchainreporter.net/fed-rate-decision-october-2026-bitcoin',
  'Fed Rate Decision October 2026: Bitcoin’s December Test',
  '미 #연준 이 10월 28일 기준금리 목표 범위를 3.75~4.00%로 동결함\n'
  '\n'
  '리사 쿡과 베스 해맥은 0.25%포인트 인상을 주장하며 결정에 반대했으며, 다음 금리 결정은 12월 9일 예정임'),
 ('https://www.tokenpost.kr/news/cryptocurrency/428826',
  '스텔라·USDC로 미국발 엘살바도르 송금 정산 계획',
  '무반타이스가 #미국 에서 엘살바도르로 보내는 송금 정산에 스텔라 네트워크와 #USDC 를 적용할 계획임\n'
  '\n'
  '정산 구간은 주말·공휴일을 포함해 24시간 운영하도록 설계됐으며, 현지 파트너가 수취인에게 달러를 지급할 예정이고 적용 시점은 공개되지 않음'))

PUBLISHED = {'https://blockchainreporter.net/fed-rate-decision-october-2026-bitcoin': 'Wed, 28 Oct 2026 18:03:45 +0000',
 'https://bloomingbit.io/feed/news/122858': 'Fri, 23 Oct 2026 23:28:37 -0700',
 'https://bloomingbit.io/feed/news/122895': 'Sun, 25 Oct 2026 17:23:00 -0500',
 'https://bloomingbit.io/feed/news/122989': 'Mon, 26 Oct 2026 19:31:42 -0400',
 'https://bloomingbit.io/feed/news/123015': 'Tue, 27 Oct 2026 01:41:28 -0500',
 'https://bloomingbit.io/feed/news/123046': 'Tue, 27 Oct 2026 08:09:34 -0700',
 'https://bloomingbit.io/feed/news/123114': 'Wed, 28 Oct 2026 06:16:15 -0500',
 'https://bloomingbit.io/feed/news/123116': 'Wed, 28 Oct 2026 06:46:11 -0500',
 'https://bloomingbit.io/feed/news/123143': 'Wed, 28 Oct 2026 13:48:02 -0500',
 'https://cointelegraph.com/news/hsbc-launches-redcoin-hong-kong-dollar-stablecoin-payme?utm_source=rss_feed&utm_medium=rss&utm_campaign=rss_partner_inbound': 'Fri, '
                                                                                                                                                               '23 '
                                                                                                                                                               'Oct '
                                                                                                                                                               '2026 '
                                                                                                                                                               '08:47:34 '
                                                                                                                                                               '+0000',
 'https://crypto.news/google-crypto-custody-mpc-security-2027': 'Wed, 28 Oct 2026 12:03:44 +0000',
 'https://crypto.news/ripple-aviva-investors-sterling-fund-xrp-ledger': 'Mon, 26 Oct 2026 10:21:22 +0000',
 'https://crypto.news/tether-15-bitcoin-mining-firms-ai-automation-mdk': 'Sun, 25 Oct 2026 06:48:16 +0000',
 'https://cryptobriefing.com/binance-files-brazil-crypto-license': 'Tue, 27 Oct 2026 08:21:50 +0000',
 'https://cryptobriefing.com/coinbase-adds-ripple-usd-support-boosting-stablecoins-accessibility': 'Wed, 28 '
                                                                                                   'Oct 2026 '
                                                                                                   '12:13:22 '
                                                                                                   '+0000',
 'https://cryptobriefing.com/tether-launches-fase-foundation-stablecoin-aid': 'Wed, 28 Oct 2026 13:52:28 '
                                                                              '+0000',
 'https://cryptopotato.com/mirae-asset-securities-and-grvt-collaborate-on-tokenised-funding-note-issuance': 'Tue, '
                                                                                                            '27 '
                                                                                                            'Oct '
                                                                                                            '2026 '
                                                                                                            '13:44:08 '
                                                                                                            '+0000',
 'https://cryptopotato.com/more-xrp-evernorth-makes-its-next-move-after-nasdaq-debut-with-80-7m-funding-plan': 'Tue, '
                                                                                                               '27 '
                                                                                                               'Oct '
                                                                                                               '2026 '
                                                                                                               '05:13:32 '
                                                                                                               '+0000',
 'https://news.bitcoin.com/blockchain/binance-founder-cz-backs-bnb-chain-new-high-speed-layer-1-network': 'Mon, '
                                                                                                          '26 '
                                                                                                          'Oct '
                                                                                                          '2026 '
                                                                                                          '23:15:09 '
                                                                                                          '+0000',
 'https://news.bitcoin.com/featured/interpol-africa-sweep-nets-1462-arrests-exposes-crypto-laundering': 'Sat, '
                                                                                                        '24 '
                                                                                                        'Oct '
                                                                                                        '2026 '
                                                                                                        '07:30:18 '
                                                                                                        '+0000',
 'https://news.bitcoin.com/featured/ripple-wins-final-us-bank-charter-ceo-calls-it-big-news-ahead-of-swell': 'Tue, '
                                                                                                             '27 '
                                                                                                             'Oct '
                                                                                                             '2026 '
                                                                                                             '02:15:22 '
                                                                                                             '+0000',
 'https://news.bitcoin.com/finance/major-banks-sign-on-as-dtcc-launches-tokenized-securities-service': 'Wed, '
                                                                                                       '28 '
                                                                                                       'Oct '
                                                                                                       '2026 '
                                                                                                       '13:35:52 '
                                                                                                       '+0000',
 'https://news.bitcoin.com/regulation-and-legal/from-stripe-to-bitcoin-card-fraud-case-ends-in-prison-sentence': 'Mon, '
                                                                                                                 '26 '
                                                                                                                 'Oct '
                                                                                                                 '2026 '
                                                                                                                 '03:30:25 '
                                                                                                                 '+0000',
 'https://news.bitcoin.com/regulation-and-legal/senator-probes-tether-reported-6m-deal-ex-trump-crypto-advisor': 'Sat, '
                                                                                                                 '24 '
                                                                                                                 'Oct '
                                                                                                                 '2026 '
                                                                                                                 '01:05:31 '
                                                                                                                 '+0000',
 'https://news.bitcoin.com/stablecoins/mexican-peso-stablecoin-gains-anchorage-custody-ethereum': 'Tue, 27 '
                                                                                                  'Oct 2026 '
                                                                                                  '18:35:13 '
                                                                                                  '+0000',
 'https://thecryptobasic.com/2026/10/28/cardano-community-weighs-9-6-million-ada-proposal-to-expand-blockchain-based-police-evidence-system': 'Wed, '
                                                                                                                                              '28 '
                                                                                                                                              'Oct '
                                                                                                                                              '2026 '
                                                                                                                                              '08:53:09 '
                                                                                                                                              '+0000',
 'https://www.tokenpost.kr/news/blockchain/426844': 'Sat, 24 Oct 2026 04:47:08 +0000',
 'https://www.tokenpost.kr/news/blockchain/427227': 'Sun, 25 Oct 2026 20:06:59 +0000',
 'https://www.tokenpost.kr/news/blockchain/428206': 'Tue, 27 Oct 2026 18:40:14 +0000',
 'https://www.tokenpost.kr/news/cryptocurrency/426849': 'Sat, 24 Oct 2026 05:02:44 +0000',
 'https://www.tokenpost.kr/news/cryptocurrency/428503': 'Wed, 28 Oct 2026 09:10:29 +0000',
 'https://www.tokenpost.kr/news/cryptocurrency/428608': 'Wed, 28 Oct 2026 13:28:17 +0000',
 'https://www.tokenpost.kr/news/cryptocurrency/428826': 'Wed, 28 Oct 2026 19:29:39 +0000',
 'https://www.tokenpost.kr/news/policy/427126': 'Sun, 25 Oct 2026 07:57:50 +0000'}
