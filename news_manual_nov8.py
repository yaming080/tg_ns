"""User-confirmed team posts; duplicate evidence, not source verification."""
EVENTS = (
    ('https://bloomingbit.io/feed/news/123882',
     '"美 중간선거 당선자 69.5%는 친 가상자산…2024년보다 높아"',
     '팀원 게시 확인: 미국 중간선거 당선자 중 69.5%가 친암호화폐 인사로 분류됐다는 집계 및 2024년 비교. 법안 통과 확정이나 모든 당선자의 공식 약속을 뜻하지 않음'),
    ('https://u.today/ripple-joins-blackrock-standard-chartered-in-new-tokenization-report',
     'Ripple Joins BlackRock, Standard Chartered in New Tokenization Report',
     '팀원 게시 확인: 리플이 블랙록·스탠다드차타드와 함께 DFSA 토큰화 백서에 기여. 토큰화 담보 인프라와 XRP레저의 연결 가능성을 실제 채택·구현 완료로 해석하지 않음'),
    ('https://u.today/fidelitys-jurrien-timmer-explains-why-he-still-prefers-bitcoin-over-gold',
     "Fidelity's Jurrien Timmer Explains Why He Still Prefers Bitcoin Over Gold",
     '팀원 게시 확인: 피델리티 주리엔 팀머의 비트코인·금 비교 선호 견해. 하락 중 상대적 가격 방어력 및 주식시장 동조화 과제. 기관의 공식 매수 결정이나 수익 보장 아님'),
)
URLS = tuple(e[0] for e in EVENTS)
