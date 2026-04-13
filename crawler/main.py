"""
통신 3사 부가서비스 크롤러 메인 진입점

실행: python crawler/main.py
결과: public/data/services.json
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from crawl_skt import crawl as crawl_skt
from crawl_kt import crawl as crawl_kt
from crawl_lgu import crawl as crawl_lgu
from merge import merge
from categorize import classify

KST = timezone(timedelta(hours=9))
OUTPUT_PATH = Path(__file__).parent.parent / "public" / "data" / "services.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def load_fallback(carrier: str) -> list[dict]:
    """기존 services.json에서 특정 통신사 데이터를 복원"""
    if not OUTPUT_PATH.exists():
        return []
    try:
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            existing = json.load(f)
        items = []
        for svc in existing.get("services", []):
            for c in svc.get("carriers", []):
                if c["carrier"] == carrier:
                    items.append({
                        "name": svc["name"],
                        "carrier": carrier,
                        "price": c["price"],
                        "description": svc.get("description", ""),
                        "prod_id": c.get("prod_id", ""),
                        "url": c.get("url", ""),
                    })
        return items
    except Exception:
        return []


def main():
    started_at = datetime.now(KST)
    print(f"크롤링 시작: {started_at.strftime('%Y-%m-%d %H:%M:%S KST')}")

    all_services = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )
        page = context.new_page()

        # SKT
        try:
            skt_items = crawl_skt(page)
            if skt_items:
                all_services.extend(skt_items)
                print(f"SKT: {len(skt_items)}개")
            else:
                raise ValueError("수집된 항목 없음")
        except Exception as e:
            fallback = load_fallback("SKT")
            all_services.extend(fallback)
            print(f"SKT 크롤링 실패 ({e}), 기존 데이터 {len(fallback)}개 유지")

        # KT
        try:
            kt_items = crawl_kt(page)
            if kt_items:
                all_services.extend(kt_items)
                print(f"KT: {len(kt_items)}개")
            else:
                raise ValueError("수집된 항목 없음")
        except Exception as e:
            fallback = load_fallback("KT")
            all_services.extend(fallback)
            print(f"KT 크롤링 실패 ({e}), 기존 데이터 {len(fallback)}개 유지")

        # LGU+
        try:
            lgu_items = crawl_lgu(page)
            if lgu_items:
                all_services.extend(lgu_items)
                print(f"LGU+: {len(lgu_items)}개")
            else:
                raise ValueError("수집된 항목 없음")
        except Exception as e:
            fallback = load_fallback("LGU+")
            all_services.extend(fallback)
            print(f"LGU+ 크롤링 실패 ({e}), 기존 데이터 {len(fallback)}개 유지")

        context.close()
        browser.close()

    merged_services, price_diffs = merge(all_services)

    if price_diffs:
        print("\n=== 통신사 간 요금 차이 ===")
        for line in price_diffs:
            print(f"  {line}")

    # 기존 services.json과 비교해 신규 서비스를 앞에 배치
    existing_keys = set()
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, encoding="utf-8") as f:
                existing = json.load(f)
            from merge import normalize_key
            existing_keys = {normalize_key(s["name"]) for s in existing.get("services", [])}
        except Exception:
            pass

    new_services = [s for s in merged_services if normalize_key(s["name"]) not in existing_keys]
    old_services = [s for s in merged_services if normalize_key(s["name"]) in existing_keys]

    today = started_at.date().isoformat()
    for svc in new_services:
        svc["new_since"] = today

    # 기존 서비스의 new_since 유지
    existing_new_since = {}
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, encoding="utf-8") as f:
                existing = json.load(f)
            for s in existing.get("services", []):
                if "new_since" in s:
                    existing_new_since[normalize_key(s["name"])] = s["new_since"]
        except Exception:
            pass
    for svc in old_services:
        key = normalize_key(svc["name"])
        if key in existing_new_since:
            svc["new_since"] = existing_new_since[key]

    sorted_services = new_services + old_services

    # 카테고리 자동 분류 (기존 카테고리가 없는 서비스만)
    for svc in sorted_services:
        if not svc.get("category"):
            svc["category"] = classify(svc["name"], svc.get("description", ""))

    if new_services:
        print(f"\n신규 서비스: {len(new_services)}개")
        for s in new_services:
            print(f"  {s['name']}")

    output = {
        "updated_at": started_at.isoformat(),
        "services": sorted_services,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {OUTPUT_PATH}")
    print(f"병합 전: {len(all_services)}개 → 병합 후: {len(merged_services)}개")


if __name__ == "__main__":
    main()
