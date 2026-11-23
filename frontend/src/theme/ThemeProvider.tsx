import { useLayoutEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from 'react'
import { ThemeContext, type ThemeChoice } from './ThemeContext'

const STORAGE_KEY = 'aiplanx-theme'

function readChoice(): ThemeChoice {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark' || saved === 'system') return saved
  } catch {
    /* storage unavailable */
  }
  return 'system'
}

function subscribe(onStoreChange: () => void) {
  const media = window.matchMedia('(prefers-color-scheme: light)')
  media.addEventListener('change', onStoreChange)
  return () => media.removeEventListener('change', onStoreChange)
}

function systemTheme(): import('./ThemeContext').ResolvedTheme {
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoiceState] = useState<ThemeChoice>(readChoice)
  const system = useSyncExternalStore(subscribe, systemTheme, () => 'dark' as const)
  const resolved = choice === 'system' ? system : choice

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = resolved
  }, [resolved])

  const value = useMemo(() => ({
    choice,
    resolved,
    setChoice: (next: ThemeChoice) => {
      setChoiceState(next)
      try {
        localStorage.setItem(STORAGE_KEY, next)
      } catch {
        /* storage unavailable */
      }
    },
  }), [choice, resolved])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
