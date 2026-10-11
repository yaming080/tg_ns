"""Already published by teammates, confirmed by the operator. Not source evidence."""
EVENTS = (
    ('https://bloomingbit.io/feed/news/121959',
     '렛저 사칭 가짜 사이트·앱이 구글 검색 상단에 노출',
     '사용자 확인 게시문(원문 검증 자료 아님): 하드웨어 지갑 렛저를 사칭한 가짜 웹사이트가 구글 검색 상단에 노출돼 이용자 주의 요구. 크립토빌리스 기기 유통 사고와 구별.'),
    ('https://crypto.news/japan-arrests-6-over-580k-crypto-laundering-case/',
     'Japan arrests 6 over $580K crypto laundering case',
     '사용자 확인 게시문(원문 검증 자료 아님): 일본 경찰이 암호화폐 자금세탁 혐의로 6명을 체포. 수사 대상 추정액 약 58만달러(9100만엔).'),
    ('https://crypto.news/russias-new-mining-rules-can-bitcoin-miners-lose-power/',
     'Russia’s new mining rules: Can Bitcoin miners lose power?',
     '사용자 확인 게시문(원문 검증 자료 아님): 러시아가 암호화폐 채굴 시설의 전력 연결에 낮은 공급 우선순위를 적용하는 새 규정을 도입.'),
    ('https://bloomingbit.io/feed/news/121953',
     '중국, 국가 차원 블록체인 네트워크 구축 추진',
     '사용자 확인 게시문(원문 검증 자료 아님): 중국 정부가 국가 블록체인 네트워크와 통합 컴퓨팅 네트워크 구축을 통한 실물·디지털 경제 융합 추진 계획을 발표.'),
)
URLS = tuple(row[0] for row in EVENTS)
