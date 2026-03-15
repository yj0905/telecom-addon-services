"""
KT 부가서비스 크롤러

전략:
- 카테고리 탭(a.ui-tab-list-btn) 클릭 후 tr 행 수집
- 각 탭에서 a.btn-more 버튼 반복 클릭
- DOM: th.title strong (이름), td.charge strong (가격), td.btns a (URL)
"""
import re
from playwright.sync_api import Page

CARRIER = "KT"
BASE_URL = "https://product.kt.com/wDic/index.do?CateCode=6003"


def parse_price(text: str) -> int:
    if not text:
        return 0
    text = text.strip()
    if "무료" in text or "free" in text.lower():
        return 0
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def crawl(page: Page) -> list[dict]:
    results = []
    seen_names = set()

    print(f"[KT] 크롤링 시작: {BASE_URL}")

    try:
        page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    except Exception as e:
        print(f"[KT] 초기 페이지 로딩 실패: {e}")
        return results

    page.wait_for_timeout(2000)

    # 탭 목록 가져오기
    tab_els = page.query_selector_all("a.ui-tab-list-btn")
    if not tab_els:
        print("[KT] 탭을 찾지 못함 → 현재 페이지 데이터만 수집")
        tab_names = ["(현재탭)"]
    else:
        tab_names = [t.inner_text().strip() for t in tab_els]
        print(f"[KT] 탭 목록: {tab_names}")

    for tab_name in tab_names:
        print(f"[KT] 탭 처리: '{tab_name}'")

        # 탭 클릭 (첫 탭은 이미 활성화)
        if tab_name != "(현재탭)":
            try:
                tab_btn = page.query_selector(f"a.ui-tab-list-btn:has-text('{tab_name}')")
                if tab_btn:
                    tab_btn.click()
                    page.wait_for_timeout(1500)
                    try:
                        page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[KT] 탭 '{tab_name}' 클릭 실패: {e}")
                continue

        # "더보기" 버튼 반복 클릭
        more_count = 0
        while True:
            more_btn = page.query_selector("a.btn-more")
            if not more_btn:
                break
            try:
                page.evaluate("el => el.scrollIntoView()", more_btn)
                more_btn.click(force=True)
                more_count += 1
                page.wait_for_timeout(1200)
            except Exception as e:
                print(f"[KT] 더보기 클릭 오류: {e}")
                break

        if more_count > 0:
            print(f"[KT] '{tab_name}' 더보기 {more_count}회 클릭")

        # tr 행에서 상품 추출
        rows = page.query_selector_all("tr")
        tab_count = 0
        for row in rows:
            try:
                # 서비스명
                title_el = row.query_selector("th.title strong")
                if not title_el:
                    continue
                name = title_el.inner_text().strip()
                if not name or name in seen_names:
                    continue
                seen_names.add(name)

                # 가격
                charge_el = row.query_selector("td.charge strong")
                if not charge_el:
                    # span 시도
                    charge_el = row.query_selector("td.charge span")
                price_text = charge_el.inner_text().strip() if charge_el else "0"
                price = parse_price(price_text)

                # 설명: plan-info 안의 p 태그들
                desc_parts = []
                plan_el = row.query_selector("td.plan-info")
                if plan_el:
                    for p in plan_el.query_selector_all("p"):
                        t = p.inner_text().strip()
                        if t:
                            desc_parts.append(t)
                description = " | ".join(desc_parts) if desc_parts else ""

                # 상세 URL
                link_el = row.query_selector("td.btns a[href]")
                href = link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://product.kt.com" + href
                detail_url = href or BASE_URL

                results.append({
                    "carrier": CARRIER,
                    "name": name,
                    "raw_category": tab_name if tab_name != "(현재탭)" else "",
                    "category": None,
                    "price": price,
                    "description": description,
                    "url": detail_url,
                })
                tab_count += 1
            except Exception as e:
                print(f"[KT] 행 파싱 오류: {e}")
                continue

        print(f"[KT] '{tab_name}': {tab_count}개 신규 수집 (누적: {len(results)}개)")

    print(f"[KT] 크롤링 완료: {len(results)}개")
    return results
