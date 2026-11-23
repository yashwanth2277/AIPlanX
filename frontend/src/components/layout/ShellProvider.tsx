import { useCallback, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { ShellContext, type Chrome } from './ShellContext'

const STORAGE_KEY = 'aiplanx-sidebar-collapsed'

export function ShellProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })
  const [mobileOpen, setMobileOpen] = useState(false)
  const [mobilePath, setMobilePath] = useState(location.pathname)
  const [chrome, setChromeState] = useState<Chrome>({ projectName: null, sessionLabel: null })

  if (mobilePath !== location.pathname) {
    setMobilePath(location.pathname)
    setMobileOpen(false)
  }

  const toggleCollapsed = useCallback(() => {
    setCollapsed((current) => {
      const next = !current
      try {
        localStorage.setItem(STORAGE_KEY, next ? '1' : '0')
      } catch {
        /* storage unavailable */
      }
      return next
    })
  }, [])

  const setChrome = useCallback((next: Chrome) => {
    setChromeState((current) => (
      current.projectName === next.projectName && current.sessionLabel === next.sessionLabel
        ? current
        : next
    ))
  }, [])

  return (
    <ShellContext.Provider value={{ collapsed, toggleCollapsed, mobileOpen, setMobileOpen, chrome, setChrome }}>
      {children}
    </ShellContext.Provider>
  )
}
