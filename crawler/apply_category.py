"""
카테고리 보정 스크립트

public/data/services.json의 category 필드를 raw_category 기반으로 채워넣는다.
SKT의 raw_category가 빈 문자열인 경우 서비스명 키워드로 분류한다.

실행: python crawler/apply_category.py
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
OUTPUT_PATH = ROOT_DIR / "public" / "data" / "services.json"

# ── 매핑 테이블 ──────────────────────────────────────────────────
RAW_TO_CATEGORY: dict[str, str] = {
    "데이터": "데이터",
    # 통화/메시지
    "통화/메시지": "통화/메시지",
    "통화편의": "통화/메시지",
    "문자편의": "통화/메시지",
    "통화/문자메시지": "통화/메시지",
    "통화연결음/벨소리": "통화/메시지",
    # 단말케어
    "단말케어(보험)": "단말케어(보험)",
    "휴대폰케어": "단말케어(보험)",
    # 콘텐츠
    "콘텐츠이용": "콘텐츠(OTT/미디어)",
    "OTT/미디어": "콘텐츠(OTT/미디어)",
    "디지털콘텐츠": "콘텐츠(OTT/미디어)",
    # 생활편의
    "혜택/편의": "생활편의",
    "생활편의": "생활편의",
    # 보안/결제
    "보안/안심": "보안/결제",
    "가족보호/안심": "보안/결제",
    "인증/결제": "보안/결제",
    "금융결제": "보안/결제",
    "PASS/정보": "보안/결제",
}

# SKT raw_category가 "" 또는 "안심/보험"인 경우 서비스명 키워드 분류
SKT_CARE_KEYWORDS = re.compile(r"보험|케어|파손|분실|수리|갤럭시|아이폰|폰교체")
SKT_SECURITY_KEYWORDS = re.compile(r"스팸|차단|보안|안심|백신|인증|필터|결제|보호|피싱|OTP|로그인|사인|키퍼|유심")
SKT_CALL_KEYWORDS = re.compile(r"스마트콜|약속번호|통화")

# 서비스명·설명 분석 기반 수동 오버라이드 (null로 남은 항목 처리)
MANUAL_OVERRIDE: dict[str, str] = {
    "스마트안티피싱":          "보안/결제",       # 보이스피싱·피싱문자·사기전화 차단
    "PASS내정보지키미":        "보안/결제",       # 개인정보 노출 모니터링·금융거래 차단
    "EBS 속도제어해제":        "데이터",          # EBS 데이터팩 전용데이터 속도 제어
    "멜론 익스트리밍 플러스":  "콘텐츠(OTT/미디어)",  # 멜론 음원 스트리밍 무제한
    "멜론 익스트리밍":         "콘텐츠(OTT/미디어)",  # 멜론 음원 스트리밍 무제한
    "팅 미디어 데이터팩":      "콘텐츠(OTT/미디어)",  # Wavve 동영상 전용 데이터팩
    "인피니티 클럽":           "단말케어(보험)",   # 단말 교체 + 보험 연계
    "배터리교체서비스":        "단말케어(보험)",   # 배터리 교체 케어
    "NEW프리미엄클럽3_A":      "단말케어(보험)",   # 단말 교체 + 분실파손 보험
    "NEW프리미엄클럽3_R":      "단말케어(보험)",   # 단말 교체 + 분실파손 보험
    "지켜줘서 고마워_현역플랜": "생활편의",        # 현역 군인 특화 혜택
    "0캠퍼스":                "생활편의",        # 캠퍼스 전용 데이터·할인 혜택
    "0플랜 수능_프로모션":     "생활편의",        # 수험생 대상 특화 프로모션
    "인포세이프박스":          "보안/결제",       # 개인정보·보안 자료 보관
    "T&캡스":                 "보안/결제",       # 보안 솔루션 (캡스 연계)
    "리모콘":                  "생활편의",        # 스마트 리모콘 앱 서비스
    # LGU+ PASS/정보 수동 분류
    "PASS":                    "보안/결제",       # PASS 인증 플랫폼
    "PASS인증서":              "보안/결제",       # 공동인증서 대체
    "PASS휴대폰안심":          "보안/결제",       # 명의·번호 보호
    "PASS금융사기방지":        "보안/결제",       # 금융사기 탐지·차단
    "PASS신용관리":            "생활편의",        # 신용점수 조회·관리
    "PASS스탁":                "투자",            # 주식 정보 서비스
    "슈퍼스탁":                "투자",            # 주식 정보 서비스
    "명의도용방지":            "보안/결제",       # 명의 무단 사용 차단
    "주민등록증 모바일 확인서비스": "보안/결제",  # 신분증 진위 확인
    "모바일운전면허 확인서비스": "보안/결제",     # 운전면허 진위 확인
    "쇼핑로그인":              "보안/결제",       # PASS 간편 쇼핑 로그인
    "휴대폰 본인확인":         "보안/결제",       # 본인인증 서비스
    "PASS펫키퍼":              "생활편의",        # 반려동물 관리
    "더펫케어":                "생활편의",        # 반려동물 케어
    "PASS오피스도우미":        "생활편의",        # 업무 편의 서비스
    "PASS블랙박스분석서비스":  "생활편의",        # 블랙박스 영상 분석
    "PASS서베이":              "생활편의",        # 설문 참여 서비스
    "PASS 쿠폰팩":             "생활편의",        # 쿠폰·혜택 팩
    "PASS헬스케어":            "생활편의",        # 건강 관리
    "PASS투데이":              "생활편의",        # 일상 정보 피드
    # 통화/메시지로 재분류 (링·콜 관련)
    "오토콜":                          "통화/메시지",
    "손누리링":                        "통화/메시지",
    "SKT콜렉트콜수신거부":             "통화/메시지",
    "T메모링":                         "통화/메시지",
    "T메모링 프리미엄":                "통화/메시지",
    "V 컬러링 라이트":                 "통화/메시지",
    "내맘대로오토링":                  "통화/메시지",
    "네임컬러링":                      "통화/메시지",
    "오토컬러링":                      "통화/메시지",
    "컬러링플러스2":                   "통화/메시지",
    "무제한컬러링플러스":              "통화/메시지",
    "벨링 콘텐츠 이용동의":           "통화/메시지",
    "V컬러링 음악감상 플러스":         "통화/메시지",
    "뮤직벨링(통화연결음,벨소리,MP3,지니뮤직 음악감상)": "통화/메시지",
    # 투자 카테고리
    "PASS 연금투자정보":       "투자",            # 연금·투자 정보
    "부동산경매노트":          "투자",            # 부동산 경매 정보
    "부동산레터":              "투자",            # 부동산 시장 정보
    "주식레터":                "투자",            # 주식 시장 정보
    "PASS부동산지키미":        "투자",            # 부동산 정보 알림
    "PASS해외주식정보":        "투자",            # 해외 주식 정보
    "투자 시그널":             "투자",            # 투자 신호 분석
    "퀀트업-미국주식":         "투자",            # 미국 주식 퀀트 분석
    "주식투자노트":            "투자",            # 주식 투자 기록
    "주식투자마스터":          "투자",            # 주식 투자 학습
    "PASS 주식정보":           "투자",            # 주식 정보
}


def classify_by_raw(raw: str) -> str | None:
    """raw_category → category 변환. 매핑 없으면 None(미분류)."""
    raw = raw.strip()
    if not raw:
        return None  # 빈 문자열은 별도 처리
    return RAW_TO_CATEGORY.get(raw, None)


def classify_skt_by_name(name: str) -> str | None:
    """SKT raw_category 빈 문자열 → 서비스명 키워드로 분류."""
    is_care = bool(SKT_CARE_KEYWORDS.search(name))
    is_security = bool(SKT_SECURITY_KEYWORDS.search(name))

    if is_care and not is_security:
        return "단말케어(보험)"
    if is_security and not is_care:
        return "보안/결제"
    # 둘 다 해당하거나 아무것도 해당 안 되면 null 유지
    return None


def apply_categories(services: list[dict]) -> tuple[list[dict], list[str]]:
    """
    services 리스트의 category를 채워넣는다.
    Returns: (수정된 서비스 목록, null로 남은 서비스명 목록)
    """
    null_services: list[str] = []

    for svc in services:
        raw = svc.get("raw_category", "").strip()
        name = svc.get("name", "")
        carriers = [c["carrier"] for c in svc.get("carriers", [])]

        # 수동 오버라이드가 있으면 raw_category 무관하게 우선 적용
        if name in MANUAL_OVERRIDE:
            svc["category"] = MANUAL_OVERRIDE[name]
            continue

        # raw_category가 있으면 매핑 테이블 사용
        if raw:
            # "안심/보험"은 서비스명 키워드로 세분류
            if raw == "안심/보험":
                if SKT_CARE_KEYWORDS.search(name):
                    svc["category"] = "단말케어(보험)"
                elif SKT_SECURITY_KEYWORDS.search(name):
                    svc["category"] = "보안/결제"
                elif SKT_CALL_KEYWORDS.search(name):
                    svc["category"] = "통화/메시지"
                else:
                    svc["category"] = None
            else:
                svc["category"] = classify_by_raw(raw)
            continue

        # raw_category 빈 문자열: 키워드 분류
        else:
            category = classify_skt_by_name(name)
            if category is not None:
                svc["category"] = category
            else:
                svc["category"] = None
                null_services.append(f"  [{', '.join(carriers)}] {name}")

    return services, null_services


def main():
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        data = json.load(f)

    services = data.get("services", [])
    print(f"총 서비스 수: {len(services)}개")

    services, null_services = apply_categories(services)
    data["services"] = services

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 통계 출력 ──
    cat_counter: Counter = Counter()
    for svc in services:
        cat_counter[svc.get("category") or "(null)"] += 1

    print("\n=== 카테고리별 서비스 수 ===")
    for cat, cnt in sorted(cat_counter.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}개")

    print(f"\n=== null로 남은 서비스: {len(null_services)}개 ===")
    if null_services:
        for line in null_services:
            print(line)

    print(f"\n저장 완료: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
