import { useState } from 'react'
import styles from './ServiceCard.module.css'

const CARRIER_META = {
  SKT:  { label: 'SKT',  color: '#0064FF', bg: '#EBF2FF' },
  KT:   { label: 'KT',   color: '#E8001D', bg: '#FDEAEC' },
  'LGU+': { label: 'LGU+', color: '#9B26AF', bg: '#F5EAF8' },
}

function formatPrice(price) {
  if (price === 0) return '무료'
  if (price === -1) return '유료'
  if (typeof price === 'string') {
    // "1100~11000" → "1,100원~11,000원"
    const rangeMatch = price.match(/^(\d+)~(\d+)$/)
    if (rangeMatch) {
      const lo = Number(rangeMatch[1]).toLocaleString('ko-KR')
      const hi = Number(rangeMatch[2]).toLocaleString('ko-KR')
      return `${lo}원~${hi}원`
    }
    return price  // "유료", "유료/무료" 등
  }
  return price.toLocaleString('ko-KR') + '원'
}

function getPriceRange(carriers) {
  const prices = carriers.map(c => c.price)
  const numPrices = prices.filter(p => typeof p === 'number')
  const strPrices = prices.filter(p => typeof p === 'string')

  if (numPrices.length === 0 && strPrices.length > 0) {
    const unique = [...new Set(strPrices)]
    return unique.length === 1 ? unique[0] : unique.join(' / ')
  }
  if (numPrices.length > 0) {
    const min = Math.min(...numPrices)
    const max = Math.max(...numPrices)
    const base = min === max ? formatPrice(min) : `${formatPrice(min)} ~ ${formatPrice(max)}`
    if (strPrices.length > 0) return `${base} / ${[...new Set(strPrices)].join(' / ')}`
    return base
  }
  return ''
}

function isNew(new_since) {
  if (!new_since) return false
  const diff = Date.now() - new Date(new_since).getTime()
  return diff < 30 * 24 * 60 * 60 * 1000
}

export default function ServiceCard({ service, selectedCarrier }) {
  const [expanded, setExpanded] = useState(false)

  const priceCarriers = selectedCarrier === '전체'
    ? service.carriers
    : service.carriers.filter(c => c.carrier === selectedCarrier)

  const priceLabel = getPriceRange(priceCarriers)
  const description = service.description || ''

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
            {service.carriers.map(c => {
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

        <h2 className={styles.name}>
          {isNew(service.new_since) && <span className={styles.badgeNew}>신규</span>}
          {service.name}
        </h2>

        <div className={styles.footer}>
          {service.category && (
            <span className={styles.category}>{service.category}</span>
          )}
          {!expanded && <span className={styles.price}>{priceLabel}</span>}
        </div>
      </div>

      {/* ── 펼쳐진 상세 ── */}
      {expanded && (
        <div className={styles.detail} onClick={e => e.stopPropagation()}>
          {description && <p className={styles.desc}>{description}</p>}
          {service.carriers.map(c => {
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
                  <span className={styles.carrierPrice}>{formatPrice(c.price)}</span>
                  {c.url && (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.detailLink}
                      onClick={e => e.stopPropagation()}
                    >
                      자세히보기 →
                    </a>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </article>
  )
}
