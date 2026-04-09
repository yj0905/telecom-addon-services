"""
통신 3사 크롤링 결과 병합 모듈

- 서비스명 정규화: 공백 제거 + PASS 접두사 제거 + 소문자
- 대표명: PASS 없는 이름 우선
- 설명 우선순위: SKT > LGU+ > KT
"""
import re
from collections import defaultdict

CARRIER_PRIORITY = ["SKT", "LGU+", "KT"]


def normalize_key(name: str) -> str:
    key = re.sub(r"\s+", "", name.strip())
    key = re.sub(r"^pass", "", key, flags=re.IGNORECASE)
    return key.lower()


def pick_name(names: list[str]) -> str:
    """PASS 없는 이름 우선, 없으면 PASS 있는 것 중 가장 짧은 것"""
    no_pass = [n for n in names if not re.match(r"^pass", n.strip(), re.IGNORECASE)]
    if no_pass:
        return min(no_pass, key=len)
    return min(names, key=len)


def pick_description(carrier_items: list[dict]) -> str:
    """SKT > LGU+ > KT 순으로 설명 선택"""
    by_carrier = {item["carrier"]: item.get("description", "") for item in carrier_items}
    for carrier in CARRIER_PRIORITY:
        desc = by_carrier.get(carrier, "")
        if desc:
            return desc
    return ""


def merge(services: list[dict]) -> tuple[list[dict], list[str]]:
    """
    flat 서비스 목록을 병합.

    반환:
    - merged: 병합된 서비스 목록
    - price_diff_report: 통신사 간 요금이 다른 서비스 보고
    """
    groups: dict[str, dict] = {}  # key → {names, items}

    for item in services:
        name = item.get("name", "").strip()
        if not name:
            continue
        key = normalize_key(name)
        if key not in groups:
            groups[key] = {"names": [], "items": []}
        if name not in groups[key]["names"]:
            groups[key]["names"].append(name)
        # 같은 통신사 중복은 첫 번째만 유지
        existing_carriers = {i["carrier"] for i in groups[key]["items"]}
        if item["carrier"] not in existing_carriers:
            groups[key]["items"].append(item)

    merged = []
    price_diff_report = []

    for key, group in groups.items():
        items = group["items"]
        name = pick_name(group["names"])
        description = pick_description(items)

        carriers = []
        for item in items:
            entry = {
                "carrier": item["carrier"],
                "price": item["price"],
                "prod_id": item.get("prod_id", ""),
                "url": item.get("url", ""),
            }
            carriers.append(entry)

        # 통신사 순서 정렬
        carrier_order = {c: i for i, c in enumerate(CARRIER_PRIORITY)}
        carriers.sort(key=lambda c: carrier_order.get(c["carrier"], 99))

        # 통신사 간 요금 차이 확인 (숫자 요금만 비교)
        int_prices = {c["carrier"]: c["price"] for c in carriers if isinstance(c["price"], int)}
        if len(set(int_prices.values())) > 1:
            # 요금이 다르면 통신사별로 분리하고 이름에 통신사 표기
            price_str = ", ".join(f"{carrier}: {price:,}원" for carrier, price in int_prices.items())
            price_diff_report.append(f"{name} → {price_str}")
            for carrier_entry in carriers:
                carrier_desc = next(
                    (i.get("description", "") for i in items if i["carrier"] == carrier_entry["carrier"]),
                    description,
                )
                merged.append({
                    "name": f"{name}({carrier_entry['carrier']})",
                    "description": carrier_desc,
                    "carriers": [carrier_entry],
                })
            continue

        merged.append({
            "name": name,
            "description": description,
            "carriers": carriers,
        })

    return merged, price_diff_report
