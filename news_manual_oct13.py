"""Operator-confirmed existing posts, used only for duplicate prevention."""
EVENTS = (
 ('https://bloomingbit.io/feed/news/122105', '바이낸스 한국 주식 투자상품 출시 검토', '바이낸스가 한국 시가총액 상위 10개 종목 수요를 언급하며 주식 투자상품 출시를 검토. 출시 확정 아님.'),
 ('https://crypto.news/sanctioned-russian-payment-network-a7-unveils-new-usdt-service/', '제재 대상 러시아 결제망 A7 새 USDT 서비스 공개', '제재 대상 A7의 새 USDT 결제 서비스 발표.'),
 ('https://crypto.news/sberbank-wins-russia-approval-crypto-exchange-services/', '스베르방크 러시아 암호화폐 거래 서비스 승인', '스베르방크의 암호화폐 교환 업무 등록·승인. 과거 수탁 등록과 구별.'),
 ('https://bloomingbit.io/feed/news/122069', '미국 암호화폐 업계 중간선거 후보 지원에 270만달러 투입', '친암호화폐 후보 지원 선거자금 270만달러 집행.'),
 ('https://coingape.com/singapore-gulf-bank-partners-with-bny-to-expand-24-7-usd-payments/', '싱가포르 걸프은행 BNY 제휴 24시간 달러 결제 확대', '적격 고객의 연중무휴 USD 송금 확대. 과거 크라켄 제휴와 별개.'),
 ('https://bloomingbit.io/feed/news/122005', '캐롤라인 팸 전 CFTC 위원장 대행 현행 규제로 감독 가능 발언', '별도 시장구조법 없이도 현행 규제 체계로 감독 가능하다는 의견. AI 연산 자원 기반 파생상품과 개인 대상 레버리지 암호화폐 거래 언급.'),
 ('https://cointelegraph.com/news/xrp-treasury-evernorth-rise-nasdaq-opening', '에버노스 나스닥 실제 첫 거래와 운용 책임자 영입', '상장 첫 거래에서 주가 5% 상승. 전 코인베이스 투자 책임자 영입 및 XRP 운용 전략. 합병 완료·상장 예정과 실제 첫 거래 단계 구별.'),
 ('https://www.theblock.co/news/markets/2026-10-12-morgan-stanley-tokenized-equities-q1-2027-418256', '모건스탠리 토큰화 주식 거래 지원 목표 2027년 1분기', '에이미 올든버그가 지원 목표 시점을 2027년 1분기로 제시. 2030년 RWA 시장 3조~10조달러는 발언자의 전망.'),
)
EVENTS = tuple((u, t, '사용자 확인 게시문(원문 검증 자료 아님): '+s) for u,t,s in EVENTS)
URLS = tuple(row[0] for row in EVENTS)
