import styles from './FilterBar.module.css'

function PillGroup({ label, options, selected, onChange, allLabel = '전체' }) {
  return (
    <div className={styles.group}>
      <span className={styles.label}>{label}</span>
      <div className={styles.pills}>
        <button
          className={`${styles.pill} ${selected === allLabel ? styles.active : ''}`}
          onClick={() => onChange(allLabel)}
        >
          {allLabel}
        </button>
        {options.map(opt => (
          <button
            key={opt}
            className={`${styles.pill} ${selected === opt ? styles.active : ''}`}
            onClick={() => onChange(opt)}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function FilterBar({
  carriers, categories,
  selectedCarrier, selectedCategory, selectedPrice,
  onCarrierChange, onCategoryChange, onPriceChange,
}) {
  return (
    <div className={styles.bar}>
      <PillGroup
        label="통신사"
        options={carriers}
        selected={selectedCarrier}
        onChange={onCarrierChange}
      />
      <PillGroup
        label="카테고리"
        options={categories}
        selected={selectedCategory}
        onChange={onCategoryChange}
      />
      <PillGroup
        label="요금"
        options={['무료', '유료']}
        selected={selectedPrice}
        onChange={onPriceChange}
      />
    </div>
  )
}
