"""User supplied channel history; not source verification or replay requests."""
EVENTS = (
    ('https://bloomingbit.io/feed/news/125413', '러시아 VTB은행, 적격투자자 대상 가상자산 장외거래 서비스 출시', '팀원 11월 28일 13:31 KST 게시. 적격투자자 대상 은행 OTC 서비스, 모스크바거래소 개시와 별개 사건.'),
    ('https://bloomingbit.io/feed/news/125411', '중국, 블록체인 기반 디지털신원인증 규정 발표…내년 3월 시행', '팀원 11월 28일 13:31 KST 게시. 규정 발표와 2027년 3월 시행 구별, 코인 채택 아님.'),
    ('https://timestabloid.com/xrp-rich-list-numbers-and-the-coming-insane-bull-market/', 'XRP Rich List Numbers and The Coming Insane Bull Market', '팀원 11월 28일 13:31 KST 게시. 계정 837만과 활용 지표에 근거한 Digital Asset Investor의 전망. 계정과 사람 수 구별, 가격 상승 보장 아님.'),
    ('https://timestabloid.com/trump-family-knows-ripple-and-xrp-very-well/', 'Trump Family Knows Ripple and XRP Very Well', '팀원 11월 28일 14:15 KST 게시. 에릭 트럼프의 2025년 인터뷰 재조명·갈링하우스 친분 및 개인적 평가. 현재 정부 정책 발표 아님.'),
    ('https://timestabloid.com/mastercard-is-expanding-its-partnership-with-ripple-xrp-heres-the-latest/', 'Mastercard Is Expanding Its Partnership With Ripple (XRP). Here’s the Latest', '봇 11월 27일 15:03 KST 게시 167497, 팀원 11월 28일 14:15 동일 출처 재게시. 카드 정산에서 AI 에이전트 금융으로 확대, 같은 발표 반복 금지.'),
    ('https://bloomingbit.io/feed/news/125384', '창펑자오 "블록체인 열기 식었지만…실사용 중심 성장의 시작일 수도"', '공개 채널 167512에서 11월 28일 00:37 KST 게시 확인. CZ 실사용 중심 성장 견해. 반복 재인용 금지.'),
    ('https://cryptobriefing.com/open-brl-stablecoin-launch-brazil/', 'Brazil stock exchange B3 plans Open BRL stablecoin launch with six financial firms', '공개 채널 167513에서 11월 28일 00:40 KST 게시 확인. B3·금융회사 6곳 헤알화 스테이블코인 개발·2027년 1분기 출시 추진. 같은 제휴의 발행 주체·원장 설명 보충은 중복.'),
    ('https://crypto.news/malaysia-first-bitcoin-etf-bursa-listing/', 'Malaysia’s first Bitcoin ETF to list on Bursa Dec. 2', '팀원 게시 확인. 할로겐 샤리아 현물 비트코인 ETF가 2026년 12월 2일 부르사 말레이시아 메인마켓에 상장될 예정. 기존 승인 이후 12월 2일 상장 일정이 이미 채널에 공지됐으므로 같은 일정의 반복 보도와 수수료 보충은 제외. 실제 거래 개시나 공식 일정 변경은 별개 사건.'),
)
URLS = tuple(row[0] for row in EVENTS)
