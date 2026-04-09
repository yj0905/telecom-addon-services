"""
KT 부가서비스 크롤러 (Playwright)

수집 항목: 서비스명, 설명, 요금, 상세페이지 URL
FilterCode 140~147 순회, 각 필터에서 '더보기' 클릭으로 전체 로드
실행: python crawler/crawl_kt.py
"""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

CARRIER = "KT"
BASE_URL = "https://product.kt.com/wDic/index.do"
DETAIL_BASE = "https://product.kt.com/wDic/productDetail.do"
FILTER_CODES = range(140, 148)  # 140~147
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def filter_url(filter_code: int) -> str:
    return f"{BASE_URL}?CateCode=6003&FilterCode={filter_code}"


def parse_price(text: str) -> int:
    """가격 문자열 → 정수. 무료 → 0, 파싱 불가 → -1"""
    text = text.strip()
    if not text or "무료" in text:
        return 0
    nums = re.findall(r"[\d,]+", text)
    if not nums:
        return -1
    return int(nums[0].replace(",", ""))


def extract_item_code(href: str) -> str:
    """href에서 ItemCode 추출"""
    m = re.search(r"ItemCode=(\w+)", href)
    return m.group(1) if m else ""


def get_total_count(pw_page: Page) -> int:
    """'총 N건' 텍스트에서 전체 서비스 수 추출"""
    for el in pw_page.query_selector_all("strong"):
        text = el.inner_text().strip()
        m = re.search(r"총\s*(\d+)건", text)
        if m:
            return int(m.group(1))
    return 0


def load_all_items(pw_page: Page) -> None:
    """'더보기' 버튼이 사라질 때까지 계속 클릭"""
    while True:
        more_btn = pw_page.query_selector("a.btn-more")
        if not more_btn or not more_btn.is_visible():
            break
        before = len(pw_page.query_selector_all("tr:has(th.title)"))
        more_btn.scroll_into_view_if_needed()
        more_btn.click()
        # 새 항목이 로드될 때까지 대기 (최대 10초)
        try:
            pw_page.wait_for_function(
                f"document.querySelectorAll('tr:has(th.title)').length > {before}",
                timeout=10_000,
            )
        except Exception:
            break


def parse_description(td_el) -> str:
    """
    td.plan-info 안의 ul.plans > li > p 텍스트 수집.
    - 같은 <p> 안의 <span>은 합쳐서 한 줄
    - 여러 <p>는 줄바꿈으로 구분
    """
    lines = []
    p_els = td_el.query_selector_all("ul.plans p")
    for p in p_els:
        text = p.inner_text().strip()
        # 줄바꿈/탭을 공백으로 정리
        text = re.sub(r"\s+", " ", text)
        if text:
            lines.append(text)
    return "\n".join(lines)


def collect_page(pw_page: Page) -> list[dict]:
    """현재 페이지에서 서비스 목록 수집 (th.title 기준으로 서비스 단위 순회)"""
    rows = pw_page.query_selector_all("table tbody tr:has(th.title)")
    items = []

    for row in rows:
        try:
            # 서비스명
            name_el = row.query_selector("th.title strong")
            if not name_el:
                continue
            name = re.sub(r"\s+", " ", name_el.inner_text().strip())

            # 설명
            desc_td = row.query_selector("td.plan-info")
            description = parse_description(desc_td) if desc_td else ""

            # 요금
            price_el = row.query_selector("td.charge strong")
            price = parse_price(price_el.inner_text() if price_el else "")

            # 상세페이지 URL
            link_el = row.query_selector("td.btns a[href]")
            item_code = ""
            url = ""
            if link_el:
                href = link_el.get_attribute("href") or ""
                item_code = extract_item_code(href)
                if item_code:
                    url = f"{DETAIL_BASE}?ItemCode={item_code}"

            items.append({
                "carrier": CARRIER,
                "name": name,
                "description": description,
                "price": price,
                "prod_id": item_code,
                "url": url,
            })
        except Exception as e:
            print(f"[KT] 행 파싱 오류: {e}")
            continue

    return items


def crawl(pw_page: Page) -> list[dict]:
    """KT 부가서비스 전체 크롤링 (FilterCode 140~147)"""
    results = []
    seen_ids: set = set()

    for filter_code in FILTER_CODES:
        print(f"[KT] FilterCode={filter_code} 로드 중...")
        pw_page.goto(filter_url(filter_code), wait_until="networkidle", timeout=30_000)
        pw_page.wait_for_selector("table tbody tr", timeout=15_000)

        total = get_total_count(pw_page)
        print(f"[KT] FilterCode={filter_code}: 총 {total}건")

        if total > 10:
            load_all_items(pw_page)

        items = collect_page(pw_page)

        # 필터 간 중복 제거 (ItemCode 기준)
        new_items = []
        for item in items:
            key = item["prod_id"] or item["name"]
            if key not in seen_ids:
                seen_ids.add(key)
                new_items.append(item)

        results.extend(new_items)
        print(f"[KT] FilterCode={filter_code}: {len(new_items)}개 수집 (누적: {len(results)}개)")

    print(f"[KT] 완료: {len(results)}개")
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
    out = Path(__file__).parent.parent / "public" / "data" / "kt_raw.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"저장: {out} ({len(items)}개)")
