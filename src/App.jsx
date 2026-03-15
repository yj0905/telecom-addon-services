import { useState, useEffect, useMemo } from 'react'
import SearchBar from './components/SearchBar.jsx'
import FilterBar from './components/FilterBar.jsx'
import ServiceCard from './components/ServiceCard.jsx'
import Pagination from './components/Pagination.jsx'
import styles from './App.module.css'

const CATEGORIES = ['데이터', '통화/메시지', '단말케어(보험)', '콘텐츠(OTT/미디어)', '생활편의', '보안/결제', '투자']
const CARRIERS = ['SKT', 'KT', 'LGU+']
const PAGE_SIZE = 24

function formatUpdatedAt(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).replace(/\. /g, '.').replace(/\.$/, '')
}

function isFree(svc, carrier) {
  const targets = carrier === '전체' ? svc.carriers : svc.carriers.filter(c => c.carrier === carrier)
  return targets.some(c => c.price === 0)
}

function isPaid(svc, carrier) {
  const targets = carrier === '전체' ? svc.carriers : svc.carriers.filter(c => c.carrier === carrier)
  return targets.some(c => c.price !== 0)
}

export default function App() {
  const [data, setData] = useState(null)
  const [query, setQuery] = useState('')
  const [selectedCarrier, setSelectedCarrier] = useState('전체')
  const [selectedCategory, setSelectedCategory] = useState('전체')
  const [selectedPrice, setSelectedPrice] = useState('전체')
  const [page, setPage] = useState(1)

  useEffect(() => {
    fetch('/data/services.json')
      .then(r => r.json())
      .then(setData)
      .catch(console.error)
  }, [])

  // 필터 변경 시 1페이지로 리셋
  function changeCarrier(v) { setSelectedCarrier(v); setPage(1) }
  function changeCategory(v) { setSelectedCategory(v); setPage(1) }
  function changePrice(v) { setSelectedPrice(v); setPage(1) }
  function changeQuery(v) { setQuery(v); setPage(1) }

  const filtered = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLowerCase()

    return data.services.filter(svc => {
      // 통신사 필터
      if (selectedCarrier !== '전체') {
        if (!svc.carriers.some(c => c.carrier === selectedCarrier)) return false
      }
      // 카테고리 필터
      if (selectedCategory !== '전체') {
        if (svc.category !== selectedCategory) return false
      }
      // 요금 필터
      if (selectedPrice === '무료') {
        if (!isFree(svc, selectedCarrier)) return false
      } else if (selectedPrice === '유료') {
        if (!isPaid(svc, selectedCarrier)) return false
      }
      // 텍스트 검색
      if (q) {
        const inName = svc.name.toLowerCase().includes(q)
        const inDesc = svc.carriers.some(c => c.description.toLowerCase().includes(q))
        if (!inName && !inDesc) return false
      }
      return true
    })
  }, [data, query, selectedCarrier, selectedCategory, selectedPrice])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const safePage = Math.min(page, totalPages)
  const pageItems = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <h1 className={styles.title}>통신 3사 부가서비스 검색</h1>
          <p className={styles.subtitle}>SKT · KT · LGU+ 부가서비스를 한눈에 비교하세요</p>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.stickyTop}>
          <SearchBar value={query} onChange={changeQuery} />
          <FilterBar
            carriers={CARRIERS}
            categories={CATEGORIES}
            selectedCarrier={selectedCarrier}
            selectedCategory={selectedCategory}
            selectedPrice={selectedPrice}
            onCarrierChange={changeCarrier}
            onCategoryChange={changeCategory}
            onPriceChange={changePrice}
          />
        </div>

        <div className={styles.meta}>
          {data && (
            <span className={styles.updatedAt}>
              마지막 업데이트: {formatUpdatedAt(data.updated_at)}
            </span>
          )}
          {data && (
            <span className={styles.resultCount}>
              총 {filtered.length.toLocaleString()}개 서비스
            </span>
          )}
        </div>

        {!data && <div className={styles.loading}>데이터를 불러오는 중...</div>}

        {data && filtered.length === 0 && (
          <div className={styles.empty}>
            <span className={styles.emptyIcon}>🔍</span>
            <p>검색 결과가 없습니다.</p>
            <p className={styles.emptyHint}>다른 키워드나 필터를 시도해보세요.</p>
          </div>
        )}

        <div className={styles.grid}>
          {pageItems.map(svc => (
            <ServiceCard
              key={svc.name}
              service={svc}
              selectedCarrier={selectedCarrier}
            />
          ))}
        </div>

        {filtered.length > 0 && (
          <Pagination
            page={safePage}
            totalPages={totalPages}
            onChange={p => { setPage(p); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
          />
        )}
      </main>
    </div>
  )
}
