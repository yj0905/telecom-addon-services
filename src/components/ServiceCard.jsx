import { useState } from 'react'
import styles from './ServiceCard.module.css'

const CARRIER_META = {
  SKT:  { label: 'SKT',  color: '#0064FF', bg: '#EBF2FF' },
  KT:   { label: 'KT',   color: '#E8001D', bg: '#FDEAEC' },
  'LGU+': { label: 'LGU+', color: '#9B26AF', bg: '#F5EAF8' },
}

function formatPrice(price, priceMax) {
  if (price === 0) return '무료'
  if (price === -1) return '유료'
  if (price === -2) return '무료/유료'
  const base = price.toLocaleString('ko-KR') + '원'
  if (priceMax != null && priceMax !== price) {
    return base + ' ~ ' + priceMax.toLocaleString('ko-KR') + '원'
  }
  return base
}

function getPriceRange(carriers) {
  const allPrices = carriers.flatMap(c => {
    const ps = [c.price]
    if (c.price_max != null && c.price_max !== c.price) ps.push(c.price_max)
    return ps
  })
  const min = Math.min(...allPrices)
  const max = Math.max(...allPrices)
  if (min === max) return formatPrice(min)
  return `${formatPrice(min)} ~ ${formatPrice(max)}`
}

export default function ServiceCard({ service, selectedCarrier }) {
  const [expanded, setExpanded] = useState(false)

  const visibleCarriers = selectedCarrier === '전체'
    ? service.carriers
    : service.carriers.filter(c => c.carrier === selectedCarrier)

  const priceLabel = getPriceRange(visibleCarriers)

  return (
    <article
      className={`${styles.card} ${expanded ? styles.expanded : ''}`}
      onClick={() => setExpanded(v => !v)}
      role="button"
      tabIndex={0}
      onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && setExpanded(v => !v)}
      aria-expanded={expanded}
    >
      {/* ── 카드 헤더 ── */}
      <div className={styles.header}>
        <div className={styles.top}>
          <div className={styles.badges}>
            {visibleCarriers.map(c => {
              const meta = CARRIER_META[c.carrier] ?? { label: c.carrier, color: '#666', bg: '#eee' }
              return (
                <span
                  key={c.carrier}
                  className={styles.badge}
                  style={{ color: meta.color, background: meta.bg }}
                >
                  {meta.label}
                </span>
              )
            })}
          </div>
          <span className={styles.chevron} aria-hidden>
            {expanded ? '▲' : '▼'}
          </span>
        </div>

        <h2 className={styles.name}>{service.name}</h2>

        <div className={styles.footer}>
          {service.category && (
            <span className={styles.category}>{service.category}</span>
          )}
          <span className={styles.price}>{priceLabel}</span>
        </div>
      </div>

      {/* ── 펼쳐진 상세 ── */}
      {expanded && (
        <div className={styles.detail} onClick={e => e.stopPropagation()}>
          {visibleCarriers.map(c => {
            const meta = CARRIER_META[c.carrier] ?? { label: c.carrier, color: '#666', bg: '#eee' }
            return (
              <div key={c.carrier} className={styles.carrierBlock}>
                <div className={styles.carrierHeader}>
                  <span
                    className={styles.carrierBadgeLg}
                    style={{ color: meta.color, borderColor: meta.color }}
                  >
                    {meta.label}
                  </span>
                  <span className={styles.carrierPrice}>{formatPrice(c.price, c.price_max)}</span>
                </div>
                {c.description && (
                  <p className={styles.desc}>{c.description}</p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </article>
  )
}
