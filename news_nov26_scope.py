"""Specific domestic financial rulemaking, independent of source or coin name."""
import re
from datetime import datetime, timezone

ENABLED_AT=datetime(2026,11,26,9,45,tzinfo=timezone.utc)


def scope(story):
    title=str(story.get('title','') or '') if isinstance(story,dict) else ''
    has=lambda p:bool(re.search(p,title,re.I))
    if has(r'목표가|협찬|광고|이벤트|price target|sponsored|giveaway|rumou?r|루머'):
        return ''
    authority=has(r'금융위|금융당국|금감원|정부|국회|기획재정|재정경제|한국은행|\bFSC\b|regulator|ministry')
    digital=has(r'디지털.?자산|가상자산|암호화폐|닥사|DAXA|digital.asset|crypto')
    action=has(r'설립|신설|추진|초안|제정|개정|입법|발의|통과|시행|승인|확정|검토|propos|draft|establish|legislat|amend|approv|enact')
    if authority and digital and action and has(r'협회|자율규제|보호재단|거래지원|이상거래|업무규정|기본법|association|self.regulat|market.surveillance'):
        return '디지털자산 법정협회·자율규제 제도 입법 진행'
    if has(r'외국환거래법|foreign.exchange.{0,15}(?:act|law|rule)') and action:
        return '외국환거래법 개정·시행 절차'
    return ''


def guidance(title):
    if not scope({'title':title}):return ''
    return '''
11월 26일 제도 뉴스 보완: 정부·금융당국의 디지털자산 법정협회, 자율규제·표준약관·이상거래 감시 업무규정 및 보호재단 신설, 기본법 제정안·초안·발의·시행은 코인명이 없어도 심사한다. 제목이 '역할 변화 예고'여도 실제 초안의 신규 조항과 주체가 확인되면 구체 사건이다. 민간 협회 홍보·행사·회원 수·익명 기대감은 예외가 아니다.
뉴시스가 입수해 보도한 정부 제정안 초안은 언론이 확인한 초안 단계로 귀속한다. 한국디지털자산업협회 설립 추진을 이미 설립·운영 중으로 쓰지 않는다. 금융위가 설립준비위원회를 구성하도록 정한 조항과 실제 위원회 구성 완료는 다르다. 닥사의 법정협회 전환 여부는 미정이며 자동 전환이나 해산 확정으로 쓰지 않는다. 표준약관·자율규제·이용자 보호 등 이해하기 쉬운 핵심 역할을 짧게 요약한다.
외국환거래법 개정·시행은 원문에서 개정 주체·개정 대상·정확한 시행일·대상 조건이 확인될 때만 심사한다. 협회 설립 기사와 별도 외국환거래법 시행일을 합쳐 쓰지 않는다. 법안 발의·정부 초안·국회 통과·공포·시행 단계는 구별한다. 날짜만 바꾼 재소개와 이미 게시한 조항 반복은 제외하고, 실질적인 새 입법 단계는 사건 검토로 구별한다.
기존 원문 사실검사·중복 판정·관련 이미지 검증은 모두 유지한다.
'''
