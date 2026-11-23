type TabsProps<T extends string> = {
  label: string
  value: T
  onChange: (value: T) => void
  options: { value: T; label: string; title?: string }[]
}

export function Tabs<T extends string>({ label, value, onChange, options }: TabsProps<T>) {
  return (
    <div className="ax-tabs" role="tablist" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="tab"
          aria-selected={value === option.value}
          className={value === option.value ? 'ax-tab is-active' : 'ax-tab'}
          title={option.title}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
