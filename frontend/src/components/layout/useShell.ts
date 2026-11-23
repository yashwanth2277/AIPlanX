import { useContext } from 'react'
import { ShellContext, type ShellContextValue } from './ShellContext'

export type { ShellContextValue }

export function useShell(): ShellContextValue {
  const value = useContext(ShellContext)
  if (!value) throw new Error('useShell must be used within ShellProvider')
  return value
}
