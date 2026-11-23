import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { useShell } from './useShell'

export function AppShell() {
  const { collapsed, mobileOpen, setMobileOpen } = useShell()
  const location = useLocation()

  return (
    <div className="ax-shell" data-collapsed={collapsed ? 'true' : 'false'}>
      <a className="ax-skip" href="#main">Skip to content</a>
      {mobileOpen && <button type="button" className="ax-overlay" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      <Sidebar />
      <div className="ax-main">
        <TopBar />
        <main id="main" className="ax-content">
          <div key={location.pathname} className="ax-page-enter">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
