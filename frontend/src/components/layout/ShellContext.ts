import { createContext } from 'react'

export type Chrome = {
  projectName: string | null
  sessionLabel: string | null
}

export type ShellContextValue = {
  collapsed: boolean
  toggleCollapsed: () => void
  mobileOpen: boolean
  setMobileOpen: (open: boolean) => void
  chrome: Chrome
  setChrome: (chrome: Chrome) => void
}

export const ShellContext = createContext<ShellContextValue | null>(null)
