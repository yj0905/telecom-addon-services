# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

통신 3사(SKT, KT, LGU+) 부가서비스를 크롤링하여 한눈에 비교할 수 있는 웹사이트.

- **프론트엔드**: React + Vite (CSS Modules, 외부 UI 라이브러리 없음)
- **크롤러**: Python (SKT/KT는 Playwright, LGU+는 Selenium)
- **데이터**: `public/data/services.json` — 크롤러가 생성하고 프론트엔드가 fetch로 읽음
- **자동화**: GitHub Actions가 매일 오전 9시 KST에 크롤러 실행 후 변경분 커밋

## 명령어

### 프론트엔드
```bash
npm run dev       # 개발 서버 (localhost:5173)
npm run build     # dist/ 빌드
npm run preview   # 빌드 결과 미리보기
```

### 크롤러
```bash
# 의존성 설치 (처음 한 번)
pip install -r crawler/requirements.txt
python -m playwright install chromium --with-deps

# 전체 크롤링 실행 (public/data/services.json 업데이트)
python crawler/main.py

# 카테고리 재분류만 (크롤링 없이 services.json의 category 필드 갱신)
python crawler/apply_category.py

# LGU+ 단독 크롤링 (디버깅용)
python crawler/run_lgu_only.py
```

## 아키텍처

### 데이터 파이프라인

```
crawl_skt.py  ─┐
crawl_kt.py   ─┼─→ main.py → merge.py → public/data/services.json
crawl_lgu.py  ─┘              ↓
                        apply_category.py (category 필드 채우기)
```

- `crawl_*.py`: 각 통신사 사이트에서 서비스 목록을 수집, `{name, carrier, price, description, prod_id, raw_category}` 형태의 dict 리스트 반환
- `merge.py`: 3사 결과를 병합하고 중복 제거. 정규화 키는 공백 제거 + `PASS` 접두사 제거 + 소문자 변환
- `apply_category.py`: `raw_category`를 표준 카테고리로 변환. 우선순위: `MANUAL_OVERRIDE` → `RAW_TO_CATEGORY` 매핑 → 키워드 분류
- 크롤링 실패 시 해당 통신사의 기존 데이터를 보존(fallback)

### services.json 스키마

```json
{
  "updated_at": "<ISO 8601, KST>",
  "services": [
    {
      "name": "서비스명",
      "raw_category": "통신사 원본 카테고리",
      "category": "표준 카테고리 | null",
      "carriers": [
        {
          "carrier": "SKT | KT | LGU+",
          "price": 0,          // 0=무료, -1=유료(불명), -2=무료/유료 혼재
          "price_max": 9900,   // 가격 범위가 있을 때만 존재
          "description": "설명",
          "prod_id": "상품 ID"  // 상세 URL 생성에 사용
        }
      ]
    }
  ]
}
```

표준 카테고리: `데이터`, `통화/메시지`, `단말케어(보험)`, `콘텐츠(OTT/미디어)`, `생활편의`, `보안/결제`, `투자`

### 프론트엔드 구조

- `App.jsx`: 상태 관리(필터/검색/페이지), `useMemo`로 필터링, 페이지당 24개
- `FilterBar.jsx`: 통신사 · 카테고리 · 요금(무료/유료) 탭 필터
- `ServiceCard.jsx`: 카드 클릭으로 상세 펼침, `prod_id`로 각 통신사 상세 URL 생성
- `SearchBar.jsx`, `Pagination.jsx`: 검색 입력, 페이지네이션

데이터는 앱 마운트 시 `/data/services.json`을 fetch하여 로드. 필터 변경 시 항상 1페이지로 리셋.
