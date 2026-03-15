import styles from './SearchBar.module.css'

export default function SearchBar({ value, onChange }) {
  return (
    <div className={styles.wrap}>
      <svg className={styles.icon} viewBox="0 0 20 20" fill="none" aria-hidden>
        <circle cx="8.5" cy="8.5" r="5.5" stroke="currentColor" strokeWidth="1.8"/>
        <path d="M13 13l3.5 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
      </svg>
      <input
        className={styles.input}
        type="search"
        placeholder="서비스명, 설명으로 검색..."
        value={value}
        onChange={e => onChange(e.target.value)}
        aria-label="서비스 검색"
      />
      {value && (
        <button className={styles.clear} onClick={() => onChange('')} aria-label="검색어 지우기">
          ✕
        </button>
      )}
    </div>
  )
}
