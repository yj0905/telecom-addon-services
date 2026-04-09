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
            all_services.extend(skt_items)
            print(f"SKT: {len(skt_items)}개")
        except Exception as e:
            print(f"SKT 크롤링 실패: {e}")

        # KT
        try:
            kt_items = crawl_kt(page)
            all_services.extend(kt_items)
            print(f"KT: {len(kt_items)}개")
        except Exception as e:
            print(f"KT 크롤링 실패: {e}")

        # LGU+
        try:
            lgu_items = crawl_lgu(page)
            all_services.extend(lgu_items)
            print(f"LGU+: {len(lgu_items)}개")
        except Exception as e:
            print(f"LGU+ 크롤링 실패: {e}")

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

    for svc in new_services:
        svc["is_new"] = True
    for svc in old_services:
        svc.pop("is_new", None)

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
