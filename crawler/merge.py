"""
크롤링 결과 병합 및 중복 제거 모듈

중복 처리 규칙:
1. 정규화 키: 띄어쓰기 제거 + 'PASS' 접두사 제거 + 소문자 변환
2. 대표 이름: PASS 붙은 이름 우선, 없으면 먼저 수집된 이름
3. 같은 통신사 내 중복은 첫 번째 항목만 유지
"""
import re


def normalize_key(name: str) -> str:
    """이름 정규화 키 생성: 공백 제거 + PASS 접두사 제거 + 소문자"""
    key = name.strip()
    key = re.sub(r"\s+", "", key)           # 공백 전부 제거
    key = re.sub(r"^pass", "", key, flags=re.IGNORECASE)  # 앞의 PASS 제거
    key = key.lower()
    return key


def pick_representative_name(names: list[str]) -> str:
    """
    대표 이름 결정:
    1. PASS가 붙은 이름 우선
    2. PASS 이름이 여럿이면 띄어쓰기 없는 버전 우선 (PASSfoo > PASS foo)
    3. PASS 없으면 첫 번째 이름
    """
    pass_names = [n for n in names if re.match(r"^pass", n, re.IGNORECASE)]
    if not pass_names:
        return names[0]

    # 띄어쓰기 없는 버전 우선 (예: PASS스팸차단 > PASS 스팸차단)
    no_space = [n for n in pass_names if " " not in n.strip()]
    if no_space:
        return no_space[0]
    return pass_names[0]


def merge_services(all_items: list[dict]) -> list[dict]:
    """
    통신사별 크롤링 결과를 병합하여 중복 제거된 서비스 목록 반환.

    반환 형식:
    [
      {
        "name": "대표 이름",
        "raw_category": "첫 번째 수집 기준 카테고리",
        "category": null,
        "carriers": [
          {"carrier": "SKT", "price": 990, "description": "...", "url": "..."},
          ...
        ]
      },
      ...
    ]
    """
    # 정규화 키 → 그룹 매핑
    groups: dict[str, dict] = {}  # key → {"names": [...], "raw_category": str, "carriers_map": {carrier: item}}

    for item in all_items:
        name = item.get("name", "").strip()
        if not name:
            continue

        key = normalize_key(name)
        carrier = item.get("carrier", "")

        if key not in groups:
            groups[key] = {
                "names": [name],
                "raw_category": item.get("raw_category", ""),
                "carriers_map": {},  # carrier → first item
            }
        else:
            if name not in groups[key]["names"]:
                groups[key]["names"].append(name)

        # 같은 통신사 내 중복은 첫 번째만 유지
        if carrier not in groups[key]["carriers_map"]:
            groups[key]["carriers_map"][carrier] = {
                "carrier": carrier,
                "price": item.get("price", 0),
                "description": item.get("description", ""),
                "url": item.get("url", ""),
            }

    # 최종 결과 생성
    merged = []
    for key, group in groups.items():
        rep_name = pick_representative_name(group["names"])
        carriers = list(group["carriers_map"].values())

        merged.append({
            "name": rep_name,
            "raw_category": group["raw_category"],
            "category": None,
            "carriers": carriers,
        })

    return merged
