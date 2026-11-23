import { useContext } from 'react'
import { ThemeContext, type ThemeContextValue, type ThemeChoice, type ResolvedTheme } from './ThemeContext'

export type { ThemeChoice, ResolvedTheme, ThemeContextValue }

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext)
  if (!value) throw new Error('useTheme must be used within ThemeProvider')
  return value
}
