"""
LGU+ 크롤링만 실행 후 기존 services.json에 병합
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from crawl_lgu import crawl_selenium
from merge import merge_services, normalize_key

ROOT_DIR = Path(__file__).parent.parent
OUTPUT_PATH = ROOT_DIR / "public" / "data" / "services.json"
KST = timezone(timedelta(hours=9))


def main():
    # 기존 데이터 로드
    if not OUTPUT_PATH.exists():
        print("services.json 없음 → 종료")
        sys.exit(1)

    with open(OUTPUT_PATH, encoding="utf-8") as f:
        existing = json.load(f)

    existing_services = existing.get("services", [])
    print(f"기존 데이터: {len(existing_services)}개 서비스")

    # LGU+ 크롤링
    lgu_items = crawl_selenium()
    if not lgu_items:
        print("LGU+ 크롤링 결과 없음 → 기존 데이터 유지")
        sys.exit(1)

    # 기존 SKT/KT 항목을 flat 리스트로 변환
    existing_flat = []
    for svc in existing_services:
        for c in svc.get("carriers", []):
            if c["carrier"] != "LGU+":
                existing_flat.append({
                    "carrier": c["carrier"],
                    "name": svc["name"],
                    "raw_category": svc.get("raw_category", ""),
                    "category": svc.get("category"),
                    "price": c["price"],
                    "description": c["description"],
                })

    # 전체 병합
    all_items = existing_flat + lgu_items
    merged = merge_services(all_items)

    updated_at = datetime.now(KST).isoformat()
    output = {"updated_at": updated_at, "services": merged}

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 통신사별 집계
    from collections import Counter
    dist = Counter()
    for s in merged:
        for c in s.get("carriers", []):
            dist[c["carrier"]] += 1

    print(f"\n저장 완료: {OUTPUT_PATH}")
    print(f"총 서비스: {len(merged)}개")
    print(f"통신사별: {dict(dist)}")
    print(f"updated_at: {updated_at}")


if __name__ == "__main__":
    main()
