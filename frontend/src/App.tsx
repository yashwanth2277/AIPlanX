
import { useCallback, useEffect, useMemo, useState, type CSSProperties, type FormEvent } from 'react'
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell,
  Bot, CalendarDays, Check, ChevronDown, CircleHelp, Clock3,
  FileBarChart, FolderKanban, LayoutDashboard, Menu,
  MoreHorizontal, Plus, Search, Settings2, ShieldAlert,
  Sparkles, Users, Workflow, X, Zap,
} from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import './App.css'
import {
  api,
  type Employee,
  type ManagementReportPayload,
  type Overview,
  type PlanJob,
  type ScheduledTask,
  type SessionSummary,
  type TaskRow,
} from './api'

const navigation = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'AI Planning Studio', icon: Sparkles },
  { label: 'Tasks & Timeline', icon: FolderKanban },
  { label: 'Team & Resources', icon: Users },
  { label: 'Reports & Analytics', icon: FileBarChart },
  { label: 'AI Assistant', icon: Bot },
]

const activityIcons = {
  green: Check,
  blue: Activity,
  violet: Users,
  orange: ShieldAlert,
} as const

type ChatTurn = { role: 'user' | 'bot'; text: string }

function App() {
  const [activePage, setActivePage] = useState('Overview')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [sessionName, setSessionName] = useState('')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [tasks, setTasks] = useState<TaskRow[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [schedule, setSchedule] = useState<ScheduledTask[]>([])
  const [report, setReport] = useState<ManagementReportPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)
  const [progressPercent, setProgressPercent] = useState(0)
  const [taskStatus, setTaskStatus] = useState('in_progress')
  const [actualHours, setActualHours] = useState('')
  const [delayHours, setDelayHours] = useState('4')
  const [delayReason, setDelayReason] = useState('')
  const [delayWeeks, setDelayWeeks] = useState('1')
  const [reassignId, setReassignId] = useState('')
  const [reassignReason, setReassignReason] = useState('Capacity adjustment')
  const [planDescription, setPlanDescription] = useState('')
  const [planSessionName, setPlanSessionName] = useState('')
  const [planJob, setPlanJob] = useState<PlanJob | null>(null)
  const [planning, setPlanning] = useState(false)
  const [chat, setChat] = useState<ChatTurn[]>([])
  const [asking, setAsking] = useState(false)
  const [health, setHealth] = useState('unknown')

  const loadWorkspace = useCallback(async (preferred?: string) => {
    setLoading(true)
    setError('')
    try {
      const [sessionPayload, employeePayload, healthPayload] = await Promise.all([
        api.sessions(),
        api.employees(),
        api.health().catch(() => ({ status: 'offline' })),
      ])
      setHealth(healthPayload.status)
      setEmployees(employeePayload.employees)
      const list = sessionPayload.sessions
      setSessions(list)
      const nextName = preferred && list.some((item) => item.name === preferred)
        ? preferred
        : list[0]?.name || ''
      setSessionName(nextName)
      if (!nextName) {
        setOverview(null)
        setTasks([])
        setSchedule([])
        setReport(null)
        return
      }
      const [overviewPayload, taskPayload, schedulePayload, reportPayload] = await Promise.all([
        api.overview(nextName),
        api.tasks(nextName),
        api.schedule(nextName),
        api.report(nextName),
      ])
      setOverview(overviewPayload)
      setTasks(taskPayload.tasks)
      setSchedule(schedulePayload.scheduled_tasks)
      setReport(reportPayload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workspace')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // Load workspace data on mount. loadWorkspace is an async function whose
    // setState calls happen in microtasks, not synchronously in the effect body.
    // The set-state-in-effect lint rule is suppressed only here because the
    // async pattern is intentional and safe.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadWorkspace()
  // loadWorkspace is stable (empty-dep useCallback) so it is safe to include.
  }, [loadWorkspace])

  const selectedTask = useMemo(
    () => tasks.find((task) => task.task_id === selectedTaskId) || null,
    [tasks, selectedTaskId],
  )

  // Sync form fields when the selected task changes.
  // Performed as a stable callback so task-selection events can call it
  // directly without needing a side-effect to copy state.
  const syncTaskForm = useCallback(
    (task: TaskRow | null, employeeList: Employee[]) => {
      if (!task) return
      setTaskStatus(task.status)
      setProgressPercent(task.progress_percent)
      setActualHours(String(task.actual_hours_spent || ''))
      setReassignId(task.employee_id || employeeList[0]?.employee_id || '')
    },
    [],
  )

  useEffect(() => {
    if (!planJob || (planJob.status !== 'queued' && planJob.status !== 'running')) return
    const timer = window.setInterval(async () => {
      try {
        const next = await api.planJob(planJob.id)
        setPlanJob(next)
        if (next.status === 'completed' && next.session_name) {
          setPlanning(false)
          await loadWorkspace(next.session_name)
          setActivePage('Overview')
        }
        if (next.status === 'failed') setPlanning(false)
      } catch (err) {
        setPlanning(false)
        setActionError(err instanceof Error ? err.message : 'Failed to poll planning job')
      }
    }, 1500)
    return () => window.clearInterval(timer)
  }, [planJob, loadWorkspace])

  const filteredTasks = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    if (!query) return tasks
    return tasks.filter((task) =>
      `${task.title} ${task.owner} ${task.status_label}`.toLowerCase().includes(query),
    )
  }, [tasks, searchQuery])

  async function switchSession(name: string) {
    setSessionName(name)
    setLoading(true)
    setError('')
    try {
      const [overviewPayload, taskPayload, schedulePayload, reportPayload] = await Promise.all([
        api.overview(name),
        api.tasks(name),
        api.schedule(name),
        api.report(name),
      ])
      setOverview(overviewPayload)
      setTasks(taskPayload.tasks)
      setSchedule(schedulePayload.scheduled_tasks)
      setReport(reportPayload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session')
    } finally {
      setLoading(false)
    }
  }

  async function refreshSession() {
    if (!sessionName) return
    await switchSession(sessionName)
  }

  async function submitQuestion(event?: FormEvent) {
    event?.preventDefault()
    const text = question.trim()
    if (!text || !sessionName) return
    setAssistantOpen(true)
    setAsking(true)
    setActionError('')
    setChat((current) => [...current, { role: 'user', text }])
    setQuestion('')
    try {
      const result = await api.askAssistant(sessionName, text)
      setChat((current) => [...current, { role: 'bot', text: result.answer }])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Assistant is unavailable'
      setActionError(message)
      setChat((current) => [...current, { role: 'bot', text: message }])
    } finally {
      setAsking(false)
    }
  }

  async function startPlan(event: FormEvent) {
    event.preventDefault()
    setActionError('')
    setPlanning(true)
    try {
      const started = await api.startPlan(planDescription, planSessionName || undefined)
      const job = await api.planJob(started.job_id)
      setPlanJob(job)
    } catch (err) {
      setPlanning(false)
      setActionError(err instanceof Error ? err.message : 'Planning failed to start')
    }
  }

  async function saveProgress(event: FormEvent) {
    event.preventDefault()
    if (!sessionName || !selectedTask) return
    setActionError('')
    try {
      await api.updateProgress(sessionName, selectedTask.task_id, {
        status: taskStatus,
        progress_percent: Number(progressPercent),
        actual_hours_spent: actualHours === '' ? undefined : Number(actualHours),
      })
      await refreshSession()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not update progress')
    }
  }

  async function saveDelay(event: FormEvent) {
    event.preventDefault()
    if (!sessionName || !selectedTask) return
    setActionError('')
    try {
      await api.recordDelay(sessionName, selectedTask.task_id, {
        delay_hours: Number(delayHours),
        reason: delayReason,
      })
      setDelayReason('')
      await refreshSession()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not record delay')
    }
  }

  async function runDelayAnalysis(event: FormEvent) {
    event.preventDefault()
    if (!sessionName || !selectedTask) return
    setActionError('')
    try {
      await api.analyzeDelay(sessionName, selectedTask.task_id, {
        delay_weeks: Number(delayWeeks),
        delay_hours: delayHours ? Number(delayHours) : undefined,
        delay_reason: delayReason || undefined,
      })
      await refreshSession()
      setActivePage('Reports & Analytics')
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not analyze delay')
    }
  }

  async function saveReassign(event: FormEvent) {
    event.preventDefault()
    if (!sessionName || !selectedTask) return
    setActionError('')
    try {
      await api.reassign(sessionName, selectedTask.task_id, {
        employee_id: reassignId,
        reason: reassignReason,
      })
      await refreshSession()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not reassign task')
    }
  }

  const currentSession = sessions.find((item) => item.name === sessionName)
  const pageSubtitle = overview
    ? activePage === 'Overview'
      ? `Live workspace for ${overview.project.name}.`
      : `Working in session ${sessionName}.`
    : 'Connect the API and create or resume a management session.'

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button className="mobile-overlay" aria-label="Close menu" onClick={() => setSidebarOpen(false)} />
      )}

      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <a className="brand" href="#" onClick={(event) => { event.preventDefault(); setActivePage('Overview') }}>
          <span className="brand-mark"><Workflow size={23} /></span>
          <span className="brand-name">AIPlan<span>X</span><small>INTELLIGENT WORKSPACE</small></span>
        </a>

        <label className="workspace-picker">
          <div className="workspace-icon">{(currentSession?.project_name || 'A').slice(0, 1)}</div>
          <div className="workspace-info">
            <strong>{currentSession?.project_name || 'No session'}</strong>
            <span>{sessionName || 'Create a plan first'}</span>
          </div>
          <select
            className="session-select"
            aria-label="Select session"
            value={sessionName}
            onChange={(event) => void switchSession(event.target.value)}
            disabled={!sessions.length}
          >
            {sessions.length === 0 && <option value="">No sessions</option>}
            {sessions.map((item) => (
              <option key={item.name} value={item.name}>
                {item.name} · {item.task_count} tasks
              </option>
            ))}
          </select>
          <ChevronDown size={16} />
        </label>

        <div className="nav-label">WORKSPACE</div>
        <nav className="sidebar-nav">
          {navigation.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={`nav-item ${activePage === label ? 'active' : ''}`}
              onClick={() => {
                setActivePage(label)
                setSidebarOpen(false)
                if (label === 'AI Assistant') setAssistantOpen(true)
              }}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
              {label === 'Tasks & Timeline' && <span className="nav-count">{overview?.progress.total_tasks ?? 0}</span>}
              {label === 'AI Assistant' && <span className="nav-new">AI</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-tip">
            <div className="tip-icon"><Zap size={17} /></div>
            <strong>Make smarter decisions</strong>
            <p>Ask about live task status, delays, and team load without changing saved state.</p>
            <button onClick={() => { setActivePage('AI Assistant'); setAssistantOpen(true) }}>
              Ask AI Assistant <ArrowRight size={14} />
            </button>
          </div>
          <button className="nav-item secondary-nav" onClick={() => setActivePage('Settings')}>
            <Settings2 size={18} /> Settings
          </button>
          <button className="nav-item secondary-nav" onClick={() => setActivePage('Help & Support')}>
            <CircleHelp size={18} /> Help & Support
          </button>
          <div className="profile">
            <div className="profile-avatar">YK</div>
            <div className="profile-info"><strong>Project Admin</strong><span>Administrator</span></div>
            <MoreHorizontal size={19} />
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open menu" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button>
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-separator">/</span><strong>{activePage}</strong></div>
          <div className="topbar-actions">
            <button className="search-trigger" onClick={() => setSearchOpen(!searchOpen)}><Search size={16} /><span>Search anything...</span><kbd>⌘ K</kbd></button>
            <button className="icon-button notification-button" aria-label="Notifications"><Bell size={18} /><i /></button>
            <div className="topbar-divider" />
            <div className="topbar-avatar">YK</div>
          </div>
        </header>

        {searchOpen && (
          <div className="search-panel">
            <Search size={18} />
            <input
              autoFocus
              value={searchQuery}
              placeholder="Search tasks, owners, status..."
              onChange={(event) => setSearchQuery(event.target.value)}
              onKeyDown={(event) => { if (event.key === 'Escape') setSearchOpen(false) }}
            />
            <button onClick={() => setSearchOpen(false)}><X size={17} /></button>
          </div>
        )}

        <div className="page-content">
          <div className="welcome-row">
            <div>
              <div className="eyebrow">
                <span className="live-dot" /> PROJECT WORKSPACE
                {overview && <><span className="eyebrow-divider">/</span> {overview.project.status_label.toUpperCase()}</>}
              </div>
              <h1>
                {activePage === 'Overview' ? 'Good afternoon' : activePage}
                <span className="heading-period">{activePage === 'Overview' ? ', Yashwanth.' : ''}</span>
              </h1>
              <p className="page-subtitle">{pageSubtitle}</p>
            </div>
            <button className="primary-button" onClick={() => setActivePage('AI Planning Studio')}>
              <Plus size={17} /> New project <span className="button-shortcut">⌘ N</span>
            </button>
          </div>

          {error && <div className="inline-error">{error}</div>}
          {actionError && <div className="inline-error">{actionError}</div>}
          {loading && <div className="page-state">Loading live project data…</div>}

          {!loading && activePage === 'Overview' && overview && (
            <OverviewPage overview={overview} onOpenTasks={() => setActivePage('Tasks & Timeline')} onOpenReports={() => setActivePage('Reports & Analytics')} />
          )}
          {!loading && activePage === 'Overview' && !overview && !error && (
            <div className="page-state">No management session yet. Use AI Planning Studio to generate a plan, or wait for demo data to import.</div>
          )}
          {activePage === 'AI Planning Studio' && (
            <PlanningStudio
              description={planDescription}
              sessionName={planSessionName}
              job={planJob}
              planning={planning}
              onDescription={setPlanDescription}
              onSessionName={setPlanSessionName}
              onSubmit={startPlan}
            />
          )}
          {activePage === 'Tasks & Timeline' && (
            <TasksPage
              tasks={filteredTasks}
              selectedTask={selectedTask}
              employees={employees}
              progressPercent={progressPercent}
              taskStatus={taskStatus}
              actualHours={actualHours}
              delayHours={delayHours}
              delayReason={delayReason}
              delayWeeks={delayWeeks}
              reassignId={reassignId}
              reassignReason={reassignReason}
              onSelect={(task) => { setSelectedTaskId(task.task_id); syncTaskForm(task, employees) }}
              onProgressPercent={setProgressPercent}
              onTaskStatus={setTaskStatus}
              onActualHours={setActualHours}
              onDelayHours={setDelayHours}
              onDelayReason={setDelayReason}
              onDelayWeeks={setDelayWeeks}
              onReassignId={setReassignId}
              onReassignReason={setReassignReason}
              onSaveProgress={saveProgress}
              onSaveDelay={saveDelay}
              onAnalyze={runDelayAnalysis}
              onReassign={saveReassign}
            />
          )}
          {activePage === 'Team & Resources' && (
            <TeamPage employees={employees} schedule={schedule} />
          )}
          {activePage === 'Reports & Analytics' && (
            <ReportsPage report={report} />
          )}
          {activePage === 'AI Assistant' && (
            <div className="page-state">
              The assistant uses the current session context and does not change saved project state. Open the chat panel to ask a question.
            </div>
          )}
          {activePage === 'Settings' && (
            <div className="page-state">
              API status: {health}. Store-backed sessions stay in SQLite by default (`AIPlanX_STORE=sqlite`). CLI workflows still use JSON files unless you switch the backend.
            </div>
          )}
          {activePage === 'Help & Support' && (
            <div className="page-state">
              Plan a project, resume a session, update task progress, record delays, reassign work, and ask the assistant about live state. Assistant answers are recommendations only.
            </div>
          )}
        </div>
      </main>

      {assistantOpen && (
        <div className="assistant-panel">
          <div className="assistant-header">
            <div className="assistant-brand">
              <span><Bot size={20} /></span>
              <div><strong>AI Project Assistant</strong><small><i /> {sessionName ? `Session ${sessionName}` : 'No session'}</small></div>
            </div>
            <button className="icon-button subtle" aria-label="Close assistant" onClick={() => setAssistantOpen(false)}><X size={19} /></button>
          </div>
          <div className="assistant-messages">
            {chat.length === 0 && (
              <>
                <div className="assistant-welcome-icon"><Sparkles size={23} /></div>
                <h3>Hey! Let's make progress.</h3>
                <p>I'm your AIPlanX assistant. Ask me about this session's tasks, team, schedule, or risks.</p>
                <div className="suggested-questions">
                  {['Summarize project status', 'Which tasks need attention?', 'Suggest next priorities'].map((text) => (
                    <button key={text} onClick={() => setQuestion(text)}>{text}<ArrowRight size={13} /></button>
                  ))}
                </div>
              </>
            )}
            {chat.map((turn, index) => (
              <div className={`assistant-turn ${turn.role}`} key={`${turn.role}-${index}`}>{turn.text}</div>
            ))}
            {asking && <div className="assistant-turn bot">Thinking with live project context…</div>}
          </div>
          <form className="assistant-input" onSubmit={submitQuestion}>
            <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask anything about your project..." />
            <button type="submit" aria-label="Send question" disabled={asking || !sessionName}><ArrowUpRight size={18} /></button>
          </form>
          <div className="assistant-disclaimer">AI-generated suggestions · You stay in control</div>
        </div>
      )}
      {!assistantOpen && (
        <button className="floating-assistant" aria-label="Open AI assistant" onClick={() => setAssistantOpen(true)}>
          <Bot size={22} /><span className="assistant-sparkle"><Sparkles size={12} /></span>
        </button>
      )}
    </div>
  )
}

function OverviewPage({
  overview,
  onOpenTasks,
  onOpenReports,
}: {
  overview: Overview
  onOpenTasks: () => void
  onOpenReports: () => void
}) {
  const percent = Math.max(0, Math.min(100, overview.progress.overall_percent))
  const health = Math.max(0, Math.min(100, overview.health.score))
  return (
    <>
      <section className="project-banner">
        <div className="project-banner-content">
          <div className="project-kicker">
            <span className="project-icon"><FolderKanban size={15} /></span>
            ACTIVE PROJECT
            <span className="project-status"><span /> {overview.project.status_label}</span>
          </div>
          <h2>{overview.project.name}</h2>
          <p>{overview.project.summary}</p>
          <div className="project-meta">
            <span><CalendarDays size={14} /> Session {overview.session_name}</span>
            <span><Users size={14} /> {overview.team_size} team members</span>
            <span><Clock3 size={14} /> {overview.project.total_estimated_hours} estimated hours</span>
          </div>
        </div>
        <div className="project-completion">
          <div className="completion-ring" style={{ '--ring': `${percent}%` } as CSSProperties}>
            <div><strong>{Math.round(percent)}<span>%</span></strong><small>COMPLETE</small></div>
          </div>
          <span className="completion-caption">Project progress</span>
        </div>
        <div className="banner-decoration banner-decoration-one" />
        <div className="banner-decoration banner-decoration-two" />
      </section>

      <section className="metrics-grid">
        <MetricCard title="Total tasks" value={String(overview.progress.total_tasks)} detail="Across this project" icon={FolderKanban} tone="violet" trend={`${overview.progress.pending} pending`} />
        <MetricCard title="Completed" value={String(overview.progress.completed)} detail="Tasks delivered" icon={Check} tone="green" trend={`${overview.progress.in_progress} in progress`} />
        <MetricCard title="In progress" value={String(overview.progress.in_progress)} detail="Currently active" icon={Activity} tone="blue" trend={`${overview.progress.blocked} blocked`} />
        <MetricCard title="At risk" value={String(overview.progress.at_risk)} detail="Needs attention" icon={ShieldAlert} tone="orange" trend={`${overview.progress.blocked} blocked`} />
      </section>

      <section className="dashboard-grid">
        <div className="panel progress-panel">
          <div className="panel-header">
            <div><h3>Project progress</h3><p>Planned vs. actual completion</p></div>
            <button className="select-button">Schedule weeks <ChevronDown size={14} /></button>
          </div>
          <div className="chart-legend">
            <span><i className="legend-planned" /> Planned</span>
            <span><i className="legend-actual" /> Actual</span>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={overview.chart} margin={{ top: 10, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="plannedFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#8b7aff" stopOpacity={0.2} /><stop offset="100%" stopColor="#8b7aff" stopOpacity={0} /></linearGradient>
                  <linearGradient id="actualFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#39c6a5" stopOpacity={0.18} /><stop offset="100%" stopColor="#39c6a5" stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid stroke="#242938" strokeDasharray="3 5" vertical={false} />
                <XAxis dataKey="week" axisLine={false} tickLine={false} tick={{ fill: '#737d94', fontSize: 11 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#737d94', fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
                <Tooltip contentStyle={{ background: '#151a27', border: '1px solid #30384a', borderRadius: 10, color: '#e8edf7', fontSize: 12 }} />
                <Area type="monotone" dataKey="planned" name="Planned" stroke="#8b7aff" strokeWidth={2} fill="url(#plannedFill)" />
                <Area type="monotone" dataKey="actual" name="Actual" stroke="#39c6a5" strokeWidth={2.5} fill="url(#actualFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-footer">
            <span>Session <strong>{overview.session_name}</strong></span>
            <span>Target completion <strong>{overview.completion_week ? `Week ${overview.completion_week}` : 'Unscheduled'}</strong></span>
          </div>
        </div>

        <div className="panel health-panel">
          <div className="panel-header"><div><h3>Project health</h3><p>Current project indicators</p></div></div>
          <div className="health-score">
            <div className="health-score-ring" style={{ '--ring': `${health}%` } as CSSProperties}>
              <div><strong>{overview.health.score}</strong><small>/ 100</small></div>
            </div>
            <div>
              <strong className="health-label">{overview.health.label}</strong>
              <span className="health-description">Project health score</span>
            </div>
          </div>
          <div className="health-indicator"><span><i className="indicator-dot green-dot" /> Schedule</span><div className="indicator-track"><i style={{ width: `${overview.health.schedule}%` }} /></div><strong>{overview.health.schedule}%</strong></div>
          <div className="health-indicator"><span><i className="indicator-dot violet-dot" /> Delivery</span><div className="indicator-track violet-track"><i style={{ width: `${overview.health.delivery}%` }} /></div><strong>{overview.health.delivery}%</strong></div>
          <div className="health-indicator"><span><i className="indicator-dot orange-dot" /> Resources</span><div className="indicator-track orange-track"><i style={{ width: `${overview.health.resources}%` }} /></div><strong>{overview.health.resources}%</strong></div>
          <button className="text-link" onClick={onOpenReports}>View health report <ArrowRight size={14} /></button>
        </div>
      </section>

      <section className="bottom-grid">
        <div className="panel tasks-panel">
          <div className="panel-header">
            <div><h3>Priority tasks</h3><p>Keep an eye on what’s next</p></div>
            <button className="text-link" onClick={onOpenTasks}>View all <ArrowRight size={14} /></button>
          </div>
          <TaskTable tasks={overview.priority_tasks.map((task) => ({
            task_id: task.task_id,
            title: task.title,
            owner: task.owner,
            initials: task.initials,
            color: task.color,
            status_label: task.status,
            progress_percent: task.progress,
            due: task.due,
            priority: task.priority,
            id: task.id,
          }))} />
        </div>

        <div className="panel activity-panel">
          <div className="panel-header"><div><h3>Recent activity</h3><p>Latest project updates</p></div></div>
          <div className="activity-list">
            {overview.activities.length === 0 && <div className="page-state">No activity recorded yet.</div>}
            {overview.activities.map((activity, index) => {
              const Icon = activityIcons[activity.color as keyof typeof activityIcons] || Activity
              return (
                <div className="activity-item" key={`${activity.title}-${index}`}>
                  <div className={`activity-icon activity-${activity.color}`}><Icon size={15} /></div>
                  <div className="activity-copy">
                    <strong>{activity.title}</strong>
                    <span>{activity.detail}</span>
                    <small>{activity.time}</small>
                  </div>
                  {index === 0 && <span className="activity-new" />}
                </div>
              )
            })}
          </div>
          <button className="text-link activity-link" onClick={onOpenReports}>View activity log <ArrowRight size={14} /></button>
        </div>
      </section>
      <footer className="dashboard-footer">
        <span>© 2026 AIPlanX <span className="footer-separator">·</span> Intelligent project management</span>
        <span><span className="system-dot" /> All systems operational</span>
      </footer>
    </>
  )
}

function PlanningStudio({
  description,
  sessionName,
  job,
  planning,
  onDescription,
  onSessionName,
  onSubmit,
}: {
  description: string
  sessionName: string
  job: PlanJob | null
  planning: boolean
  onDescription: (value: string) => void
  onSessionName: (value: string) => void
  onSubmit: (event: FormEvent) => void
}) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h3>Generate a project plan</h3>
          <p>This runs the planning workflow, stores the report in SQLite, and can create a management session.</p>
        </div>
      </div>
      <form className="studio-form" onSubmit={onSubmit}>
        <label className="field">
          <span>Project description</span>
          <textarea value={description} onChange={(event) => onDescription(event.target.value)} minLength={10} required placeholder="Describe the project, constraints, and desired outcomes." />
        </label>
        <label className="field">
          <span>Session name (optional)</span>
          <input value={sessionName} onChange={(event) => onSessionName(event.target.value)} placeholder="campus-platform" />
        </label>
        <button className="primary-button" type="submit" disabled={planning}>
          <Sparkles size={16} /> {planning ? 'Planning…' : 'Start planning job'}
        </button>
        {job && (
          <div className="job-status">
            Job {job.id.slice(0, 8)} · {job.status}
            {job.error ? ` · ${job.error}` : ''}
            {job.session_name ? ` · session ${job.session_name}` : ''}
          </div>
        )}
      </form>
    </div>
  )
}

function TasksPage({
  tasks,
  selectedTask,
  employees,
  progressPercent,
  taskStatus,
  actualHours,
  delayHours,
  delayReason,
  delayWeeks,
  reassignId,
  reassignReason,
  onSelect,
  onProgressPercent,
  onTaskStatus,
  onActualHours,
  onDelayHours,
  onDelayReason,
  onDelayWeeks,
  onReassignId,
  onReassignReason,
  onSaveProgress,
  onSaveDelay,
  onAnalyze,
  onReassign,
}: {
  tasks: TaskRow[]
  selectedTask: TaskRow | null
  employees: Employee[]
  progressPercent: number
  taskStatus: string
  actualHours: string
  delayHours: string
  delayReason: string
  delayWeeks: string
  reassignId: string
  reassignReason: string
  onSelect: (task: TaskRow) => void
  onProgressPercent: (value: number) => void
  onTaskStatus: (value: string) => void
  onActualHours: (value: string) => void
  onDelayHours: (value: string) => void
  onDelayReason: (value: string) => void
  onDelayWeeks: (value: string) => void
  onReassignId: (value: string) => void
  onReassignReason: (value: string) => void
  onSaveProgress: (event: FormEvent) => void
  onSaveDelay: (event: FormEvent) => void
  onAnalyze: (event: FormEvent) => void
  onReassign: (event: FormEvent) => void
}) {
  return (
    <div className="bottom-grid">
      <div className="panel tasks-panel">
        <div className="panel-header"><div><h3>Schedule</h3><p>Select a task to update progress, delay, or assignment</p></div></div>
        <div className="task-table-wrap">
          <table className="task-table">
            <thead><tr><th>TASK</th><th>ASSIGNEE</th><th>STATUS</th><th>PROGRESS</th><th>DUE</th></tr></thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.task_id} onClick={() => onSelect(task)} style={{ cursor: 'pointer' }}>
                  <td>
                    <div className="task-name"><span className="task-id">{String(task.task_id).padStart(2, '0')}</span><strong>{task.title}</strong></div>
                    <span className={`priority priority-${task.priority.toLowerCase()}`}>{task.priority} priority</span>
                  </td>
                  <td><div className="assignee"><span className={`assignee-avatar avatar-${task.color}`}>{task.initials}</span>{task.owner}</div></td>
                  <td><span className={`status-pill status-${task.status_label.toLowerCase().replace(' ', '-')}`}><i />{task.status_label}</span></td>
                  <td><div className="task-progress"><div><i style={{ width: `${task.progress_percent}%` }} /></div><span>{Math.round(task.progress_percent)}%</span></div></td>
                  <td className="due-date">{task.due}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="panel selected-task">
        {!selectedTask && <div className="page-state">Select a task to manage it.</div>}
        {selectedTask && (
          <>
            <div className="panel-header"><div><h3>{selectedTask.title}</h3><p>{selectedTask.description}</p></div></div>
            <form className="task-form" onSubmit={onSaveProgress}>
              <div className="form-row">
                <label className="field">
                  <span>Status</span>
                  <select value={taskStatus} onChange={(event) => onTaskStatus(event.target.value)}>
                    <option value="pending">Pending</option>
                    <option value="in_progress">In progress</option>
                    <option value="blocked">Blocked</option>
                    <option value="completed">Completed</option>
                  </select>
                </label>
                <label className="field">
                  <span>Progress %</span>
                  <input type="number" min={0} max={100} value={progressPercent} onChange={(event) => onProgressPercent(Number(event.target.value))} />
                </label>
                <label className="field">
                  <span>Hours spent</span>
                  <input type="number" min={0} value={actualHours} onChange={(event) => onActualHours(event.target.value)} />
                </label>
              </div>
              <button className="primary-button" type="submit">Save progress</button>
            </form>
            <form className="stack-form" onSubmit={onSaveDelay}>
              <div className="form-row">
                <label className="field">
                  <span>Delay hours</span>
                  <input type="number" min={0.1} step="0.5" value={delayHours} onChange={(event) => onDelayHours(event.target.value)} />
                </label>
                <label className="field">
                  <span>Reason</span>
                  <input value={delayReason} onChange={(event) => onDelayReason(event.target.value)} placeholder="Blocked on review" required />
                </label>
              </div>
              <button className="secondary-button" type="submit">Record delay</button>
            </form>
            <form className="stack-form" onSubmit={onAnalyze}>
              <label className="field">
                <span>Analyze delay (weeks)</span>
                <input type="number" min={1} max={52} value={delayWeeks} onChange={(event) => onDelayWeeks(event.target.value)} />
              </label>
              <button className="secondary-button" type="submit">Analyze schedule impact</button>
            </form>
            <form className="stack-form" onSubmit={onReassign}>
              <label className="field">
                <span>Reassign to</span>
                <select value={reassignId} onChange={(event) => onReassignId(event.target.value)}>
                  {employees.map((employee) => (
                    <option key={employee.employee_id} value={employee.employee_id}>
                      {employee.employee_name} · {employee.role}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Reason</span>
                <input value={reassignReason} onChange={(event) => onReassignReason(event.target.value)} required />
              </label>
              <button className="secondary-button" type="submit">Reassign task</button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

function TeamPage({ employees, schedule }: { employees: Employee[]; schedule: ScheduledTask[] }) {
  return (
    <>
      <div className="employee-grid">
        {employees.map((employee) => (
          <div className="panel" key={employee.employee_id}>
            <div className="panel-header">
              <div>
                <h3>{employee.employee_name}</h3>
                <p>{employee.role} · {employee.experience} yrs · {employee.weekly_capacity_hours}h/week</p>
              </div>
            </div>
            <div className="metric-trend trend-violet">Workload {employee.current_workload_percent}%</div>
            <div style={{ marginTop: 12 }}>
              {employee.skills.map((skill) => <span className="skill-chip" key={skill}>{skill}</span>)}
            </div>
          </div>
        ))}
      </div>
      <div className="panel" style={{ marginTop: 16 }}>
        <div className="panel-header"><div><h3>Work schedule</h3><p>Allocated weeks from the current session</p></div></div>
        <div className="task-table-wrap">
          <table className="task-table">
            <thead><tr><th>TASK</th><th>OWNER</th><th>HOURS</th><th>WEEKS</th></tr></thead>
            <tbody>
              {schedule.map((item) => (
                <tr key={item.task_id}>
                  <td><strong>{item.task_title}</strong></td>
                  <td>{item.employee_name}</td>
                  <td>{item.total_estimated_hours}</td>
                  <td>W{item.start_week}–W{item.completion_week}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}

function ReportsPage({ report }: { report: ManagementReportPayload | null }) {
  if (!report) return <div className="page-state">No management report is available for this session.</div>
  const management = report.management_report
  const insights = report.insights
  const risks = report.planning_report?.risk_analysis?.risks || []
  return (
    <div className="report-grid">
      <div className="panel">
        <div className="panel-header"><div><h3>{management.project_name}</h3><p>Live management report</p></div></div>
        <p className="page-subtitle">
          {management.progress.completed_tasks} completed · {management.progress.in_progress_tasks} in progress · {management.progress.blocked_tasks} blocked
        </p>
        <ul className="list-block">
          {management.recommendations.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </div>
      <div className="panel">
        <div className="panel-header"><div><h3>Delays</h3><p>Revised completion week {management.revised_completion_week ?? 'unchanged'}</p></div></div>
        <ul className="list-block">
          {management.task_delays.length === 0 && <li>No delays recorded.</li>}
          {management.task_delays.map((item) => (
            <li key={`${item.task_id}-${item.reason}`}>{item.task_title}: {item.delay_hours}h · {item.reason}</li>
          ))}
        </ul>
      </div>
      <div className="panel">
        <div className="panel-header"><div><h3>AI insights</h3><p>Generated from current management state</p></div></div>
        {insights?.unavailable ? (
          <p className="page-subtitle">{insights.reason}</p>
        ) : (
          <>
            <p className="page-subtitle">{insights?.executive_summary}</p>
            <ul className="list-block">
              {(insights?.recovery_recommendations || []).map((item) => <li key={item}>{item}</li>)}
            </ul>
          </>
        )}
      </div>
      <div className="panel">
        <div className="panel-header"><div><h3>Planning risks</h3><p>{report.planning_report?.risk_analysis?.overall_risk_level || 'Unknown'}</p></div></div>
        <ul className="list-block">
          {risks.map((risk) => <li key={risk.title}>{risk.severity}: {risk.title} — {risk.mitigation}</li>)}
        </ul>
      </div>
    </div>
  )
}

function TaskTable({
  tasks,
}: {
  tasks: {
    id?: string
    task_id: number
    title: string
    owner: string
    initials: string
    color: string
    status_label: string
    progress_percent: number
    due: string
    priority: string
  }[]
}) {
  return (
    <div className="task-table-wrap">
      <table className="task-table">
        <thead><tr><th>TASK</th><th>ASSIGNEE</th><th>STATUS</th><th>PROGRESS</th><th>DUE DATE</th></tr></thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.task_id}>
              <td>
                <div className="task-name"><span className="task-id">{task.id || String(task.task_id).padStart(2, '0')}</span><strong>{task.title}</strong></div>
                <span className={`priority priority-${task.priority.toLowerCase()}`}>{task.priority} priority</span>
              </td>
              <td><div className="assignee"><span className={`assignee-avatar avatar-${task.color}`}>{task.initials}</span>{task.owner}</div></td>
              <td><span className={`status-pill status-${task.status_label.toLowerCase().replace(' ', '-')}`}><i />{task.status_label}</span></td>
              <td><div className="task-progress"><div><i style={{ width: `${task.progress_percent}%` }} /></div><span>{Math.round(task.progress_percent)}%</span></div></td>
              <td className="due-date">{task.due}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MetricCard({
  title, value, detail, icon: Icon, tone, trend,
}: {
  title: string
  value: string
  detail: string
  icon: typeof FolderKanban
  tone: string
  trend: string
}) {
  return (
    <div className="metric-card">
      <div className="metric-top"><span>{title}</span><span className={`metric-icon metric-${tone}`}><Icon size={18} /></span></div>
      <div className="metric-value">{value}<span className="metric-detail">{detail}</span></div>
      <div className={`metric-trend trend-${tone}`}>{tone === 'orange' ? <ArrowDownRight size={14} /> : <ArrowUpRight size={14} />}{trend}</div>
    </div>
  )
}

export default App
