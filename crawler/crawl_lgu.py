"""
LGU+ 부가서비스 크롤러 (Playwright)

수집 항목: 서비스명, 설명, 요금, 상세페이지 URL
카테고리별 URL 순회, 페이지네이션 버튼으로 전체 로드
실행: python crawler/crawl_lgu.py
"""
import json as json_mod
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

CARRIER = "LGU+"
BASE_URL = "https://www.lguplus.com/mobile/plan/addon"
SLUGS = [
    "addon-data",
    "addon-phonecare",
    "addon-digitalcontent",
    "addon-call-msg",
    "addon-ringtones-callertunes",
    "addon-familysafety-info",
    "addon-pass",
]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def parse_price(text: str):
    """
    요금 문자열 파싱.
    - '월 16,500원' → 16500
    - '월 1,100~11,000원' → '1100~11000'
    - '무료' → 0
    - '유료', '유료/무료' 등 → 원문 그대로
    """
    text = text.strip()
    if not text:
        return 0
    if text == "무료" or text == "월 0원":
        return 0
    # 범위 가격: 숫자~숫자
    range_m = re.search(r"([\d,]+)\s*~\s*([\d,]+)", text)
    if range_m:
        lo = int(range_m.group(1).replace(",", ""))
        hi = int(range_m.group(2).replace(",", ""))
        return f"{lo}~{hi}"
    # 단일 가격
    single_m = re.search(r"([\d,]+)\s*원", text)
    if single_m:
        return int(single_m.group(1).replace(",", ""))
    # 유료/무료 표기 통일
    if text in ("무료/유료", "유료/무료"):
        return "유료/무료"
    # 그 외 숫자로 파싱 불가한 경우 → 유료로 처리
    return "유료"


def collect_page(pw_page: Page, slug: str, seen_ids: set) -> list[dict]:
    """현재 페이지의 서비스 목록 수집"""
    items = []
    cards = pw_page.query_selector_all("ul.service-list > li, ul[class*='list'] > li")

    for card in cards:
        try:
            # 서비스명 + prod_id (data-ec-product에서 추출)
            btn = card.query_selector("button[data-ec-product]")
            if not btn:
                continue

            raw_json = btn.get_attribute("data-ec-product") or "{}"
            prod_data = json_mod.loads(raw_json)
            prod_id = prod_data.get("ecom_prd_id", "").strip()
            name_span = btn.query_selector("span")
            name = name_span.inner_text().strip() if name_span else prod_data.get("ecom_prd_name", "").strip()
            if not name:
                continue

            dedup_key = prod_id or name
            if dedup_key in seen_ids:
                continue
            seen_ids.add(dedup_key)

            # 설명
            desc_el = card.query_selector("p")
            description = desc_el.inner_text().strip() if desc_el else ""

            # 요금
            price_el = card.query_selector("div.state")
            price = parse_price(price_el.inner_text() if price_el else "")

            # 상세페이지 URL
            url = f"{BASE_URL}/{slug}/{prod_id}" if prod_id else ""

            items.append({
                "carrier": CARRIER,
                "name": name,
                "description": description,
                "price": price,
                "prod_id": prod_id,
                "url": url,
            })
        except Exception as e:
            print(f"[LGU+] 카드 파싱 오류: {e}")
            continue

    return items


def crawl_slug(pw_page: Page, slug: str, seen_ids: set) -> list[dict]:
    """단일 카테고리 URL 전체 페이지 크롤링"""
    url = f"{BASE_URL}/{slug}"
    print(f"[LGU+] {slug} 로드 중...")
    pw_page.goto(url, wait_until="networkidle", timeout=30_000)
    pw_page.wait_for_selector("button[data-ec-product]", timeout=20_000)

    results = []
    page_no = 1

    while True:
        items = collect_page(pw_page, slug, seen_ids)
        results.extend(items)
        print(f"[LGU+] {slug} 페이지 {page_no}: {len(items)}개 (누적: {len(results)}개)")

        # 다음 페이지 버튼 확인
        next_btn = pw_page.query_selector("button[aria-label='다음 페이지로 이동']")
        if not next_btn or not next_btn.is_visible() or next_btn.is_disabled():
            break

        # 페이지 변경 감지를 위해 첫 번째 서비스명 저장
        first_name = pw_page.query_selector("button[data-ec-product] span")
        before_name = first_name.inner_text() if first_name else ""

        next_btn.scroll_into_view_if_needed()
        next_btn.click()

        # 콘텐츠가 바뀔 때까지 대기
        try:
            pw_page.wait_for_function(
                f"""() => {{
                    const el = document.querySelector('button[data-ec-product] span');
                    return el && el.innerText !== {json_mod.dumps(before_name)};
                }}""",
                timeout=10_000,
            )
        except Exception:
            break

        page_no += 1

    return results


def crawl(pw_page: Page = None) -> list[dict]:
    """LGU+ 부가서비스 전체 크롤링"""
    results = []
    seen_ids: set = set()

    # crawl()이 단독 실행될 때는 pw_page가 None → 내부에서 browser 생성
    if pw_page is None:
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
            for slug in SLUGS:
                items = crawl_slug(page, slug, seen_ids)
                results.extend(items)
            context.close()
            browser.close()
    else:
        for slug in SLUGS:
            items = crawl_slug(pw_page, slug, seen_ids)
            results.extend(items)

    print(f"[LGU+] 완료: {len(results)}개")
    return results


if __name__ == "__main__":
    items = crawl()

    import json
    out = Path(__file__).parent.parent / "public" / "data" / "lgu_raw.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"저장: {out} ({len(items)}개)")
