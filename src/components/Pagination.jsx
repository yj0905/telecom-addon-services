import styles from './Pagination.module.css'

const WINDOW = 2 // 현재 페이지 양쪽에 보여줄 페이지 수

export default function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null

  // 표시할 페이지 번호 계산
  const pages = []
  const start = Math.max(1, page - WINDOW)
  const end = Math.min(totalPages, page + WINDOW)

  if (start > 1) {
    pages.push(1)
    if (start > 2) pages.push('...')
  }
  for (let i = start; i <= end; i++) pages.push(i)
  if (end < totalPages) {
    if (end < totalPages - 1) pages.push('...')
    pages.push(totalPages)
  }

  return (
    <nav className={styles.nav} aria-label="페이지 탐색">
      <button
        className={styles.btn}
        onClick={() => onChange(page - 1)}
        disabled={page === 1}
        aria-label="이전 페이지"
      >
        ‹
      </button>

      {pages.map((p, i) =>
        p === '...' ? (
          <span key={`ellipsis-${i}`} className={styles.ellipsis}>…</span>
        ) : (
          <button
            key={p}
            className={`${styles.btn} ${p === page ? styles.active : ''}`}
            onClick={() => onChange(p)}
            aria-label={`${p}페이지`}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        )
      )}

      <button
        className={styles.btn}
        onClick={() => onChange(page + 1)}
        disabled={page === totalPages}
        aria-label="다음 페이지"
      >
        ›
      </button>
    </nav>
  )
}
