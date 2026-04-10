"""
서비스 카테고리 분류 스크립트

카테고리: 데이터, 통화/문자, 기기케어, 안심/보안, 인증/결제, 혜택/편의, 콘텐츠
실행: python crawler/categorize.py
"""
import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
OUTPUT_PATH = ROOT_DIR / "public" / "data" / "services.json"

CATEGORIES = ['데이터', '통화/문자', '기기케어', '안심/보안', '인증/결제', '혜택/편의', '콘텐츠']

# ── 키워드 규칙 (순서 중요: 앞에 있을수록 우선) ───────────────────────────────

DATA_KW = re.compile(
    r"데이터|쉐어링|나눠쓰기|데이터팩|QoS|속도제어|데이터충전|데이터쿠폰|데이터옵션"
    r"|데이터플러스|데이터상품권|테더링|공유데이터|데이터차단|데이터안심|로밍"
)

CALL_KW = re.compile(
    r"컬러링|벨소리|벨링|통화|문자|메시지|착신|발신|번호표시|콜|링서비스|ringback"
    r"|오토링|네임링|메모링|소리샘|콜키퍼|약속번호|스마트콜|수신거부|콜렉트콜"
    r"|문자발송|SMS|MMS|영상통화",
    re.IGNORECASE
)

CARE_KW = re.compile(
    r"폰케어|기기케어|단말케어|휴대폰케어|스크린케어|디바이스케어|갤럭시케어|아이폰케어"
    r"|파손|분실|수리|교체|단말보험|휴대폰보험|기기보험|스크린보험"
    r"|배터리교체|액정수리|액정교체|단말|스크린|액정|프리미엄클럽|인피니티클럽"
)

SECURITY_KW = re.compile(
    r"안심|스팸|차단|피싱|백신|사기방지|사기탐지|도용|보호|불법카메라"
    r"|스미싱|해킹|악성|바이러스|개인정보보호|명의도용|번호보호|안티바이러스"
    r"|스마트안티|사이버|보안관제"
)

AUTH_KW = re.compile(
    r"인증|결제|PASS인증|본인확인|간편결제|OTP|공동인증|전자서명|운전면허확인"
    r"|주민등록.*확인|모바일.*확인|신원확인|금융인증|쇼핑로그인",
    re.IGNORECASE
)

BENEFIT_KW = re.compile(
    r"혜택|할인|쿠폰|포인트|생활|여행|주차|단속알림|캠퍼스|수능|군인|군장병"
    r"|로밍할인|요금할인|리모콘|날씨|교통|지도|주유|편의|생활정보|오피스"
    r"|펫|반려|건강|헬스|블랙박스|설문|서베이|투데이|일상"
)

CONTENT_KW = re.compile(
    r"OTT|미디어|음악|영화|독서|전자책|게임|웹툰|스트리밍|넷플릭스|디즈니|유튜브"
    r"|멜론|지니|티빙|왓챠|시즌|유플릭스|Wavve|웨이브|시리즈|애니|만화|소설"
    r"|뮤직|뮤지컬|공연|스포츠중계|골프|낚시|요리|쿠킹|교육|어학|강의|클래스"
    r"|교보문고|sam|밀리|리디|북|콘텐츠|미디어팩|동영상|VOD|라이브|스튜디오"
    r"|구글원|iCloud|클라우드|드라이브|스토리지",
    re.IGNORECASE
)

# 수동 오버라이드
MANUAL: dict[str, str] = {
    "발신번호표시제한": "통화/문자",
    "V컬러링": "통화/문자",
    "인포세이프박스": "안심/보안",
    "PASS": "인증/결제",
    "PASS인증서": "인증/결제",
    "휴대폰 본인확인": "인증/결제",
    "모바일운전면허 확인서비스": "인증/결제",
    "주민등록증 모바일 확인서비스": "인증/결제",
    "명의도용방지": "안심/보안",
    "T&캡스": "안심/보안",
    "더치트 프리미엄": "안심/보안",
    "리모콘": "혜택/편의",
    "부동산경매노트": "혜택/편의",
    "부동산레터": "혜택/편의",
    "주식레터": "혜택/편의",
    "해외주식노트": "혜택/편의",
    "투자 시그널": "혜택/편의",
    "퀀트업-미국주식": "혜택/편의",
    "주식투자노트": "혜택/편의",
    "주식투자마스터": "혜택/편의",
    "공모주정보": "혜택/편의",
    "생활정보": "혜택/편의",
    "연금투자정보": "혜택/편의",
    "PASS 연금투자정보": "혜택/편의",
    "PASS 주식정보": "혜택/편의",
    "PASS해외주식정보": "혜택/편의",
    "PASS부동산지키미": "혜택/편의",
    "슈퍼스탁": "혜택/편의",
    # 미분류 수동 지정
    "국제전화음성안내거부": "통화/문자",
    "T ARS": "통화/문자",
    "T ARS 라이트": "통화/문자",
    "T RING플러스(무료)": "통화/문자",
    "넘버플러스II": "통화/문자",
    "자동연결(유료)": "통화/문자",
    "링투유 오토체인지": "통화/문자",
    "KT 투폰": "통화/문자",
    "번호변경안내(모바일)": "통화/문자",
    "번호변경안내(유료)": "통화/문자",
    "번호변경안내(무료)": "통화/문자",
    "투폰서비스(3G)": "통화/문자",
    "통합사서함": "통화/문자",
    "HD 보이스 (VoLTE)": "통화/문자",
    "듀얼넘버 온앤오프": "통화/문자",
    "자동응답": "통화/문자",
    "원넘버": "통화/문자",
    "AI보이스링 캐릭터플러스": "통화/문자",
    "원키퍼": "안심/보안",
    "모션키": "인증/결제",
    "로그인플러스": "인증/결제",
    "휴대폰간편로그인": "인증/결제",
    "신용지키미": "혜택/편의",
    "PASS 신용지키미_O": "혜택/편의",
    "부동산지키미": "혜택/편의",
    "이용요금알리미": "혜택/편의",
    "요금납부알림서비스": "혜택/편의",
    "영문이용요금알리미": "혜택/편의",
    "KDB × T high5 적금": "혜택/편의",
    "PASS신용관리": "혜택/편의",
    "PASS스탁": "혜택/편의",
    "모아진 (무제한 매거진)": "콘텐츠",
    "딥엘 (DeepL)": "콘텐츠",
    "위치정보자기제어": "안심/보안",
    "내위치전송 서비스": "안심/보안",
    "지하철Wi-Fi": "혜택/편의",
    "구글 원(Google One)": "콘텐츠",
    "플레이스(번호안내 서비스)": "혜택/편의",
    "아파트청약케어": "혜택/편의",
    "소호지키미": "혜택/편의",
    "갤럭시S22 클럽": "기기케어",
}


def classify(name: str, description: str) -> str | None:
    if name in MANUAL:
        return MANUAL[name]

    text = name + " " + description

    # PASS 서비스: 이름에 PASS 포함 → 인증/결제 우선 검토 후 키워드로 세분류
    if re.match(r"^pass", name.strip(), re.IGNORECASE):
        if AUTH_KW.search(text):
            return "인증/결제"
        if SECURITY_KW.search(text):
            return "안심/보안"
        if CONTENT_KW.search(text):
            return "콘텐츠"
        if BENEFIT_KW.search(text):
            return "혜택/편의"

    if DATA_KW.search(text):
        return "데이터"
    if CARE_KW.search(text):
        return "기기케어"
    if CALL_KW.search(text):
        return "통화/문자"
    if CONTENT_KW.search(text):
        return "콘텐츠"
    if AUTH_KW.search(text):
        return "인증/결제"
    if SECURITY_KW.search(text):
        return "안심/보안"
    if BENEFIT_KW.search(text):
        return "혜택/편의"

    return None


def main():
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        data = json.load(f)

    services = data["services"]
    null_list = []

    from collections import Counter
    cat_counter = Counter()

    for svc in services:
        name = svc.get("name", "")
        desc = svc.get("description", "")
        category = classify(name, desc)
        svc["category"] = category
        cat_counter[category or "(미분류)"] += 1
        if category is None:
            carriers = [c["carrier"] for c in svc.get("carriers", [])]
            null_list.append({
                "name": name,
                "carriers": carriers,
                "description": desc[:60] if desc else "",
            })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("=== 카테고리별 서비스 수 ===")
    for cat in CATEGORIES:
        print(f"  {cat}: {cat_counter.get(cat, 0)}개")
    print(f"  (미분류): {cat_counter.get('(미분류)', 0)}개")

    print(f"\n=== 미분류 서비스: {len(null_list)}개 ===")
    with open(ROOT_DIR / "public" / "data" / "uncategorized.json", "w", encoding="utf-8") as f:
        json.dump(null_list, f, ensure_ascii=False, indent=2)
    print("미분류 목록 → public/data/uncategorized.json")


if __name__ == "__main__":
    main()
