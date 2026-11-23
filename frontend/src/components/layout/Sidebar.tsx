import { NavLink } from 'react-router-dom'
import {
  ArrowLeft, Bell, Bot, ChartNoAxesGantt, FileBarChart, FolderKanban,
  History, LayoutDashboard, ListChecks, PanelLeftClose, PanelLeftOpen,
  Settings, Sparkles, UserRound, Users, Workflow,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '../../lib/cn'
import { workspaceBase } from '../../navigation'
import { useShell } from './useShell'
import { useLocation } from 'react-router-dom'

const globalNav: { to: string; label: string; icon: LucideIcon; end?: boolean }[] = [
  { to: '/projects', label: 'Projects', icon: FolderKanban, end: true },
  { to: '/team', label: 'Team Management', icon: Users, end: true },
  { to: '/notifications', label: 'Notifications', icon: Bell, end: true },
]

const footerNav: { to: string; label: string; icon: LucideIcon }[] = [
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/profile', label: 'Profile', icon: UserRound },
]

const projectNav: { segment: string; label: string; icon: LucideIcon }[] = [
  { segment: 'overview', label: 'Overview', icon: LayoutDashboard },
  { segment: 'studio', label: 'AI Planning Studio', icon: Sparkles },
  { segment: 'team', label: 'Team', icon: Users },
  { segment: 'tasks', label: 'Tasks & Assignments', icon: ListChecks },
  { segment: 'timeline', label: 'Progress & Timeline', icon: ChartNoAxesGantt },
  { segment: 'reports', label: 'Reports & Analysis', icon: FileBarChart },
  { segment: 'assistant', label: 'AI Assistant', icon: Bot },
  { segment: 'activity', label: 'Activity History', icon: History },
]

export function Sidebar() {
  const { collapsed, toggleCollapsed, mobileOpen, setMobileOpen, chrome } = useShell()
  const { pathname } = useLocation()
  const base = workspaceBase(pathname)

  return (
    <aside className={cn('ax-sidebar', mobileOpen && 'is-open')}>
      <div className="ax-brand-row">
        <NavLink to="/projects" className="ax-brand" onClick={() => setMobileOpen(false)}>
          <span className="ax-brand-mark"><Workflow size={18} /></span>
          <span className="ax-brand-name">
            <strong>AIPlanX</strong>
            <span>Workspace</span>
          </span>
        </NavLink>
        <button type="button" className="ax-collapse-toggle" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={toggleCollapsed}>
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>
      <div className="ax-sidebar-scroll">
        {base && (
          <>
            <div className="ax-project-chip">
              <NavLink to="/projects" className="ax-back" onClick={() => setMobileOpen(false)} title="All projects">
                <ArrowLeft size={14} />
                <span>All projects</span>
              </NavLink>
              <p>{chrome.projectName || 'Project'}</p>
            </div>
            <p className="ax-nav-label">Project</p>
            <nav className="ax-nav" aria-label="Project">
              {projectNav.map(({ segment, label, icon: Icon }) => (
                <NavLink
                  key={segment}
                  to={`${base}/${segment}`}
                  title={label}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) => cn('ax-nav-item', isActive && 'is-active')}
                >
                  <Icon size={18} />
                  <span className="ax-collapse-label">{label}</span>
                </NavLink>
              ))}
            </nav>
          </>
        )}
        <p className="ax-nav-label">{base ? 'Global' : 'Workspace'}</p>
        <nav className="ax-nav" aria-label="Global">
          {globalNav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              title={label}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => cn('ax-nav-item', isActive && 'is-active')}
            >
              <Icon size={18} />
              <span className="ax-collapse-label">{label}</span>
            </NavLink>
          ))}
        </nav>
        <p className="ax-nav-label">Account</p>
        <nav className="ax-nav" aria-label="Account">
          {footerNav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              title={label}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => cn('ax-nav-item', isActive && 'is-active')}
            >
              <Icon size={18} />
              <span className="ax-collapse-label">{label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  )
}
