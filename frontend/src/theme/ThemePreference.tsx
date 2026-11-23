import { useTheme, type ThemeChoice } from './useTheme'

const options: { value: ThemeChoice; label: string; detail: string }[] = [
  { value: 'light', label: 'Light', detail: 'White surfaces and royal blue accents.' },
  { value: 'dark', label: 'Dark', detail: 'Midnight navy surfaces.' },
  { value: 'system', label: 'Match system', detail: 'Follow this device until you choose a theme.' },
]

export function ThemePreference() {
  const { choice, setChoice } = useTheme()
  return (
    <fieldset className="ax-stack">
      <legend className="ax-kicker">Theme</legend>
      {options.map((option) => (
        <label className="ax-choice" key={option.value}>
          <input
            type="radio"
            name="theme"
            value={option.value}
            checked={choice === option.value}
            onChange={() => setChoice(option.value)}
          />
          <span>
            <strong>{option.label}</strong>
            <span className="ax-hint" style={{ display: 'block' }}>{option.detail}</span>
          </span>
        </label>
      ))}
    </fieldset>
  )
}
