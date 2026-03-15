"""
통신 3사 부가서비스 크롤러 메인 진입점

실행: python crawler/main.py
결과: public/data/services.json
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

# 프로젝트 루트 기준 경로
ROOT_DIR = Path(__file__).parent.parent
OUTPUT_PATH = ROOT_DIR / "public" / "data" / "services.json"

# 크롤러 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent))
from crawl_skt import crawl as crawl_skt
from crawl_kt import crawl as crawl_kt
from crawl_lgu import crawl as crawl_lgu
from merge import merge_services

KST = timezone(timedelta(hours=9))
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def load_existing_data() -> dict | None:
    """기존 services.json 로드 (fallback용)"""
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[main] 기존 데이터 로드 실패: {e}")
    return None


def save_data(data: dict) -> None:
    """services.json 저장"""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[main] 저장 완료: {OUTPUT_PATH} ({len(data.get('services', []))}개 서비스)")


def run_crawler(name: str, crawl_fn, page) -> list[dict]:
    """단일 크롤러 실행, 실패 시 빈 리스트 반환"""
    try:
        items = crawl_fn(page)
        print(f"[main] {name} 완료: {len(items)}개")
        return items
    except Exception as e:
        print(f"[main] {name} 크롤링 실패: {e}")
        return []


def main():
    print("=" * 60)
    print("통신 3사 부가서비스 크롤링 시작")
    print(f"시작 시각: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    print("=" * 60)

    existing_data = load_existing_data()
    all_items: list[dict] = []
    failed_carriers: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        # ── SKT ──────────────────────────────────────────────────
        context_skt = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )
        page_skt = context_skt.new_page()
        skt_items = run_crawler("SKT", crawl_skt, page_skt)
        context_skt.close()

        if skt_items:
            all_items.extend(skt_items)
        else:
            failed_carriers.append("SKT")

        # ── KT ───────────────────────────────────────────────────
        context_kt = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )
        page_kt = context_kt.new_page()
        kt_items = run_crawler("KT", crawl_kt, page_kt)
        context_kt.close()

        if kt_items:
            all_items.extend(kt_items)
        else:
            failed_carriers.append("KT")

        browser.close()

    # ── LGU+ (Selenium) ──────────────────────────────────────────
    lgu_items = run_crawler("LGU+", crawl_lgu, None)

    if lgu_items:
        all_items.extend(lgu_items)
    else:
        failed_carriers.append("LGU+")

    # ── 결과 처리 ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"수집 완료: 총 {len(all_items)}개 원본 항목")
    if failed_carriers:
        print(f"실패 통신사: {', '.join(failed_carriers)}")

    if not all_items:
        print("[main] 전체 크롤링 실패 → 기존 데이터 유지")
        if existing_data:
            print(f"[main] 기존 데이터 유지: {len(existing_data.get('services', []))}개 서비스")
        else:
            print("[main] 기존 데이터 없음 → 빈 파일 저장")
            save_data({"updated_at": datetime.now(KST).isoformat(), "services": []})
        sys.exit(1)

    # 병합 및 중복 제거
    merged = merge_services(all_items)
    print(f"병합 후: {len(merged)}개 서비스 (중복 제거 완료)")

    # 실패한 통신사의 기존 데이터 보존 (fallback)
    if failed_carriers and existing_data:
        existing_services = existing_data.get("services", [])
        for service in existing_services:
            for carrier_item in service.get("carriers", []):
                if carrier_item.get("carrier") in failed_carriers:
                    # 해당 통신사 데이터를 새 병합 결과에 추가
                    _inject_fallback_carrier(merged, service, carrier_item)
        print(f"[main] 실패 통신사({', '.join(failed_carriers)}) 기존 데이터 병합 완료")

    updated_at = datetime.now(KST).isoformat()
    output = {
        "updated_at": updated_at,
        "services": merged,
    }

    save_data(output)

    print("\n" + "=" * 60)
    print("크롤링 완료!")
    print(f"종료 시각: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"총 서비스 수: {len(merged)}개")
    print("=" * 60)


def _inject_fallback_carrier(merged: list[dict], old_service: dict, carrier_item: dict) -> None:
    """기존 데이터의 특정 통신사 항목을 새 병합 결과에 삽입 (없는 경우만)"""
    from merge import normalize_key

    old_key = normalize_key(old_service.get("name", ""))
    carrier = carrier_item.get("carrier", "")

    for service in merged:
        if normalize_key(service.get("name", "")) == old_key:
            # 이미 해당 통신사 있으면 스킵
            existing_carriers = {c["carrier"] for c in service.get("carriers", [])}
            if carrier not in existing_carriers:
                service["carriers"].append(carrier_item)
            return

    # 병합 결과에 없는 서비스 → 새로 추가
    merged.append({
        "name": old_service.get("name", ""),
        "raw_category": old_service.get("raw_category", ""),
        "category": old_service.get("category", None),
        "carriers": [carrier_item],
    })


if __name__ == "__main__":
    main()
