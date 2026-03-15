"""
LGU+ 부가서비스 크롤러 (Selenium + ChromeDriver)

전략:
- 카테고리별 URL을 순회하며 raw_category를 URL에서 확정
- ul.service-list > li 항목 수집
- button[data-ec-product] JSON에서 이름/가격 추출
- p 태그에서 설명 추출
- ul.pagination 버튼으로 페이지 이동
"""
import json as json_mod
import re
import time


CARRIER = "LGU+"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 카테고리별 URL (raw_category → URL)
CATEGORY_URLS: dict[str, str] = {
    "데이터":           "https://www.lguplus.com/mobile/plan/addon/addon-data",
    "휴대폰케어":       "https://www.lguplus.com/mobile/plan/addon/addon-phonecare",
    "디지털콘텐츠":     "https://www.lguplus.com/mobile/plan/addon/addon-digitalcontent",
    "통화/문자메시지":  "https://www.lguplus.com/mobile/plan/addon/addon-call-msg",
    "통화연결음/벨소리": "https://www.lguplus.com/mobile/plan/addon/addon-ringtones-callertunes",
    "가족보호/안심":    "https://www.lguplus.com/mobile/plan/addon/addon-familysafety-info",
    "PASS/정보":        "https://www.lguplus.com/mobile/plan/addon/addon-pass",
}


def parse_price(text: str) -> tuple[int, int]:
    """(min_price, max_price) 반환. 단일 가격이면 둘이 같음.
    -1: 유료(금액 미공개), -2: 무료/유료 혼합
    """
    if not text:
        return (0, 0)
    text = str(text).strip()
    has_free = "무료" in text or "free" in text.lower()
    has_paid = "유료" in text
    if has_free and has_paid:
        return (-2, -2)  # 무료/유료 혼합
    if has_free:
        return (0, 0)
    if has_paid:
        return (-1, -1)
    # 콤마 천단위 구분자를 포함한 가격 패턴 추출 (예: 1,100 / 11,000)
    matches = re.findall(r'\d{1,3}(?:,\d{3})+|\d+', text)
    prices = [int(m.replace(',', '')) for m in matches if m]
    if not prices:
        return (0, 0)
    return (min(prices), max(prices))


def _make_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(f"user-agent={USER_AGENT}")
    opts.add_argument("--lang=ko-KR")
    opts.add_argument("--window-size=1280,900")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd(
        "Network.setExtraHTTPHeaders",
        {"headers": {"Referer": "https://www.lguplus.com/", "Accept-Language": "ko-KR,ko;q=0.9"}},
    )
    return driver


def _collect_items(driver, raw_category: str, seen_ids: set) -> list[dict]:
    from selenium.webdriver.common.by import By

    items = []
    try:
        cards = driver.find_elements(By.CSS_SELECTOR, "ul.service-list > li")
    except Exception:
        return items

    for card in cards:
        try:
            btn = card.find_element(By.CSS_SELECTOR, "button[data-ec-product]")
            raw_json = btn.get_attribute("data-ec-product")
            prod_data = json_mod.loads(raw_json)

            prod_id = prod_data.get("ecom_prd_id", "").strip()
            name = prod_data.get("ecom_prd_name", "").strip()
            price_str = prod_data.get("ecom_prd_price", "").strip()

            if not name:
                continue

            dedup_key = prod_id or name
            if dedup_key in seen_ids:
                continue
            seen_ids.add(dedup_key)

            price_min, price_max = parse_price(price_str)

            desc = ""
            try:
                desc_el = card.find_element(By.CSS_SELECTOR, "p")
                desc = desc_el.text.strip()
            except Exception:
                pass

            item = {
                "carrier": CARRIER,
                "name": name,
                "raw_category": raw_category,
                "category": None,
                "price": price_min,
                "description": desc,
            }
            if price_max != price_min:
                item["price_max"] = price_max

            items.append(item)
        except Exception as e:
            print(f"[LGU+] 카드 파싱 오류: {e}")
            continue

    return items


def _crawl_category(driver, raw_category: str, url: str, seen_ids: set) -> list[dict]:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    results = []
    print(f"[LGU+] {raw_category} 크롤링: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.service-list > li"))
        )
    except Exception:
        print(f"[LGU+] {raw_category} service-list 대기 시간 초과 → 건너뜀")
        return results

    time.sleep(1.5)

    page_no = 1
    while True:
        items = _collect_items(driver, raw_category, seen_ids)
        results.extend(items)
        print(f"[LGU+] {raw_category} 페이지 {page_no}: {len(items)}개 수집 (누적: {len(results)}개)")

        try:
            next_btn = driver.find_element(
                By.CSS_SELECTOR,
                "ul.pagination button[aria-label='다음 페이지로 이동']:not([disabled])"
            )
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(2)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.service-list > li"))
            )
            page_no += 1
        except Exception:
            break

    return results


def crawl_selenium() -> list[dict]:
    """Selenium 기반 LGU+ 크롤러 — 카테고리별 URL 순회"""
    results = []
    seen_ids: set = set()

    driver = _make_driver()
    try:
        for raw_category, url in CATEGORY_URLS.items():
            try:
                items = _crawl_category(driver, raw_category, url, seen_ids)
                results.extend(items)
            except Exception as e:
                print(f"[LGU+] {raw_category} 크롤링 오류: {e}")
    finally:
        driver.quit()

    print(f"[LGU+] 전체 완료: {len(results)}개")
    return results


# Playwright 인터페이스 호환용
def crawl(page=None) -> list[dict]:
    return crawl_selenium()
