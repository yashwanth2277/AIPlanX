import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Bell, Check, Menu, Monitor, Moon, Sun, UserRound } from 'lucide-react'
import { pageMeta, workspaceBase } from '../../navigation'
import { useTheme, type ThemeChoice } from '../../theme/useTheme'
import { Dropdown } from '../ui/Dropdown'
import { IconButton } from '../ui/IconButton'
import { useShell } from './useShell'

const themeOptions: { value: ThemeChoice; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'Match system', icon: Monitor },
]

export function TopBar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const meta = pageMeta(pathname)
  const base = workspaceBase(pathname)
  const { chrome, setMobileOpen } = useShell()
  const { choice, setChoice } = useTheme()
  const [themeOpen, setThemeOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const section = base ? pathname.slice(base.length + 1) : ''

  return (
    <header className="ax-topbar">
      <div>
        {base && (
          <nav className="ax-crumbs" aria-label="Breadcrumb">
            <Link to="/projects">Projects</Link>
            <span>/</span>
            <span>{chrome.projectName || 'Project'}</span>
            {section && (
              <>
                <span>/</span>
                <span>{meta.title}</span>
              </>
            )}
          </nav>
        )}
        <h1>{meta.title}</h1>
        {meta.description && <p className="ax-lead">{meta.description}</p>}
      </div>
      <div className="ax-top-actions">
        <IconButton className="ax-mobile-only" aria-label="Open navigation" onClick={() => setMobileOpen(true)}>
          <Menu size={18} />
        </IconButton>
        <Dropdown
          open={themeOpen}
          onClose={() => setThemeOpen(false)}
          label="Theme"
          trigger={(
            <IconButton aria-label="Theme" onClick={() => setThemeOpen((open) => !open)}>
              {choice === 'light' ? <Sun size={18} /> : choice === 'dark' ? <Moon size={18} /> : <Monitor size={18} />}
            </IconButton>
          )}
        >
          {themeOptions.map((option) => {
            const Icon = option.icon
            return (
              <button
                key={option.value}
                type="button"
                role="menuitemradio"
                aria-checked={choice === option.value}
                className={choice === option.value ? 'ax-menu-item is-active' : 'ax-menu-item'}
                onClick={() => {
                  setChoice(option.value)
                  setThemeOpen(false)
                }}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><Icon size={15} /> {option.label}</span>
                {choice === option.value && <Check size={14} />}
              </button>
            )
          })}
        </Dropdown>
        <Link to="/notifications" className="ax-icon-btn" aria-label="Notifications" aria-current={pathname === '/notifications' ? 'page' : undefined}>
          <Bell size={18} />
        </Link>
        <Dropdown
          open={profileOpen}
          onClose={() => setProfileOpen(false)}
          label="Account"
          trigger={(
            <IconButton aria-label="Account menu" onClick={() => setProfileOpen((open) => !open)}>
              <UserRound size={18} />
            </IconButton>
          )}
        >
          <button type="button" role="menuitem" className="ax-menu-item" onClick={() => { setProfileOpen(false); navigate('/profile') }}>
            Profile
          </button>
          <button type="button" role="menuitem" className="ax-menu-item" onClick={() => { setProfileOpen(false); navigate('/settings') }}>
            Settings
          </button>
        </Dropdown>
      </div>
    </header>
  )
}
