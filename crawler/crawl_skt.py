"""
SKT 부가서비스 크롤러 (Playwright)

수집 항목: 서비스명, 설명, 요금, 상세페이지 URL
실행: python crawler/crawl_skt.py
"""
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

CARRIER = "SKT"
BASE_URL = "https://www.tworld.co.kr/web/product/addon/list"
DETAIL_BASE = "https://www.tworld.co.kr/web/product/callplan"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def page_url(page_no: int) -> str:
    return (
        f"{BASE_URL}?idxCtgCd=F01200&searchFltIds=&searchOrder=recommand"
        f"&searchPageCount=10&searchPageNo={page_no}"
    )


def parse_price(text: str):
    """
    가격 문자열 → 정수 또는 문자열.
    무료 → 0, 상세참조/파싱 불가 → "유료"
    """
    text = text.strip()
    if not text or "무료" in text:
        return 0
    if "상세참조" in text:
        return "유료"
    nums = re.findall(r"[\d,]+", text)
    if not nums:
        return "유료"
    return int(nums[0].replace(",", ""))


def get_last_page(pw_page: Page) -> int:
    """맨 끝페이지 버튼의 data-page 속성으로 마지막 페이지 번호 확인"""
    el = pw_page.query_selector("a.btn.end[data-page]")
    if el:
        val = el.get_attribute("data-page")
        if val and val.isdigit():
            return int(val)
    # 버튼이 없으면 현재 페이지가 마지막
    return 1


def collect_page(pw_page: Page) -> list[dict]:
    """현재 페이지에서 서비스 목록 수집"""
    rows = pw_page.query_selector_all("table tbody tr")
    items = []

    for row in rows:
        try:
            # 서비스명 + prod_id
            name_el = row.query_selector("td:first-child span a[data-prod-id]")
            if not name_el:
                continue
            name = name_el.inner_text().strip()
            prod_id = name_el.get_attribute("data-prod-id") or ""

            # 설명
            desc_el = row.query_selector("td:first-child p")
            description = desc_el.inner_text().strip() if desc_el else ""

            # 요금
            price_el = row.query_selector("td.fee")
            price = parse_price(price_el.inner_text() if price_el else "")

            url = f"{DETAIL_BASE}/{prod_id}" if prod_id else ""

            items.append({
                "carrier": CARRIER,
                "name": name,
                "description": description,
                "price": price,
                "prod_id": prod_id,
                "url": url,
            })
        except Exception as e:
            print(f"[SKT] 행 파싱 오류: {e}")
            continue

    return items


def crawl(pw_page: Page) -> list[dict]:
    """SKT 부가서비스 전체 크롤링"""
    results = []

    # 1페이지 로드 후 마지막 페이지 확인
    pw_page.goto(page_url(1), wait_until="load", timeout=60_000)
    pw_page.wait_for_selector("a[data-prod-id]", timeout=20_000)

    last_page = get_last_page(pw_page)
    print(f"[SKT] 총 {last_page}페이지")

    items = collect_page(pw_page)
    results.extend(items)
    print(f"[SKT] 페이지 1: {len(items)}개 (누적: {len(results)}개)")

    for page_no in range(2, last_page + 1):
        pw_page.goto(page_url(page_no), wait_until="load", timeout=60_000)
        pw_page.wait_for_selector("a[data-prod-id]", timeout=20_000)

        items = collect_page(pw_page)
        results.extend(items)
        print(f"[SKT] 페이지 {page_no}: {len(items)}개 (누적: {len(results)}개)")

    print(f"[SKT] 완료: {len(results)}개")
    return results


if __name__ == "__main__":
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
        items = crawl(page)
        context.close()
        browser.close()

    import json
    out = Path(__file__).parent.parent / "public" / "data" / "skt_raw.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"저장: {out} ({len(items)}개)")
