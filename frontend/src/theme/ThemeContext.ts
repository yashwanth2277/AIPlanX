import { createContext } from 'react'

export type ThemeChoice = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

export type ThemeContextValue = {
  choice: ThemeChoice
  resolved: ResolvedTheme
  setChoice: (choice: ThemeChoice) => void
}

export const ThemeContext = createContext<ThemeContextValue | null>(null)
