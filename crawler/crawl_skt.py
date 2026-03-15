"""
SKT 부가서비스 크롤러

전략:
- 카테고리 필터(F01231~F01236)별로 API 순회하여 raw_category 확보
- 마지막에 전체(필터 없음)로 미수집 상품 보완
- API: /core-product/v1/submain/ont-products
- page.evaluate()로 내부 fetch() 호출 (쿠키/세션 자동 포함)
"""
import re
from playwright.sync_api import Page

CARRIER = "SKT"
BASE_PAGE = "https://www.tworld.co.kr/web/product/addon/list?idxCtgCd=F01200"
API_BASE = (
    "https://www.tworld.co.kr/core-product/v1/submain/ont-products"
    "?idxCtgCd=F01200&searchOrder=&searchPageCount=100&searchPageNo="
)
DETAIL_URL = "https://www.tworld.co.kr/web/product/addon/detail?prodId="

# 카테고리 필터 ID → 원본 카테고리명
FILTERS = {
    "F01231": "데이터",
    "F01232": "혜택/편의",
    "F01233": "안심/보험",
    "F01234": "통화/메시지",
    "F01235": "콘텐츠이용",
    "F01236": "인증/결제",
}


def parse_price(text: str) -> int:
    if not text:
        return 0
    text = str(text).strip()
    if text == "0" or "무료" in text:
        return 0
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def _fetch_all_pages(page: Page, filter_id: str) -> list[dict]:
    """특정 필터 ID로 모든 페이지 수집"""
    results = []
    page_no = 1
    while True:
        url = f"{API_BASE}{page_no}&searchFltIds={filter_id}"
        try:
            data = page.evaluate(f"""async () => {{
                const resp = await fetch('{url}', {{
                    headers: {{ 'Accept': 'application/json', 'Referer': '{BASE_PAGE}' }}
                }});
                return resp.json();
            }}""")
        except Exception as e:
            print(f"[SKT] fetch 오류 (filter={filter_id}, page={page_no}): {e}")
            break

        products = data.get("result", {}).get("products", [])
        if not products:
            break
        results.extend(products)

        # 전체 카운트 확인
        if page_no == 1:
            total = data.get("result", {}).get("productCount", 0)
            total_pages = (total + 99) // 100  # pageCount=100
            if total_pages <= 1:
                break

        if len(results) >= data.get("result", {}).get("productCount", 0):
            break
        page_no += 1

    return results


def crawl(page: Page) -> list[dict]:
    results: list[dict] = []
    seen_ids: set[str] = set()

    print("[SKT] 크롤링 시작 (카테고리 필터별 순회)")

    # 메인 페이지 로드로 쿠키/세션 확보
    try:
        page.goto(BASE_PAGE, wait_until="networkidle", timeout=30000)
    except Exception as e:
        print(f"[SKT] 페이지 로드 실패: {e}")
        return results

    # ── 카테고리 필터별 수집 ──
    for flt_id, flt_name in FILTERS.items():
        print(f"[SKT] 카테고리 '{flt_name}' ({flt_id}) 수집 중...")
        products = _fetch_all_pages(page, flt_id)
        cat_new = 0
        for prod in products:
            prod_id = prod.get("prodId", "")
            if prod_id in seen_ids:
                continue  # 다른 카테고리에서 이미 수집
            seen_ids.add(prod_id)
            results.append(_make_item(prod, flt_name))
            cat_new += 1
        print(f"[SKT]   → {len(products)}개 중 신규 {cat_new}개 (누적: {len(results)}개)")

    # ── 카테고리 없는 상품 보완 (전체 목록에서 미수집 항목) ──
    print("[SKT] 전체 목록으로 미수집 상품 보완 중...")
    uncategorized_page_no = 1
    uncategorized_new = 0
    while True:
        url = f"{API_BASE}{uncategorized_page_no}&searchFltIds="
        try:
            data = page.evaluate(f"""async () => {{
                const resp = await fetch('{url}', {{
                    headers: {{ 'Accept': 'application/json', 'Referer': '{BASE_PAGE}' }}
                }});
                return resp.json();
            }}""")
        except Exception as e:
            print(f"[SKT] 전체 목록 fetch 오류 (page={uncategorized_page_no}): {e}")
            break

        products = data.get("result", {}).get("products", [])
        if not products:
            break

        for prod in products:
            prod_id = prod.get("prodId", "")
            if prod_id in seen_ids:
                continue
            seen_ids.add(prod_id)
            results.append(_make_item(prod, ""))  # raw_category 빈 문자열
            uncategorized_new += 1

        if uncategorized_page_no == 1:
            total = data.get("result", {}).get("productCount", 0)
            total_pages = (total + 99) // 100
            if total_pages <= 1:
                break
        if len(seen_ids) >= data.get("result", {}).get("productCount", 0):
            break
        uncategorized_page_no += 1

    if uncategorized_new:
        print(f"[SKT] 미분류 보완: {uncategorized_new}개")

    print(f"[SKT] 크롤링 완료: {len(results)}개")
    return results


def _make_item(prod: dict, raw_category: str) -> dict:
    prod_id = prod.get("prodId", "")
    return {
        "carrier": CARRIER,
        "name": prod.get("prodNm", "").strip(),
        "raw_category": raw_category,
        "category": None,
        "price": parse_price(prod.get("basFeeAmt", "0")),
        "description": prod.get("prodSmryDesc", "").strip(),
        "url": f"{DETAIL_URL}{prod_id}" if prod_id else BASE_PAGE,
    }
