import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  api,
  type Employee,
  type ManagementReportPayload,
  type Overview,
  type PlanJob,
  type ProjectListItem,
  type ScheduledTask,
  type SessionSummary,
  type TaskRow,
} from '../api'
import { Banner } from '../components/ui/Banner'
import { ErrorState } from '../components/ui/ErrorState'
import { PageSkeleton } from '../components/ui/Skeleton'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/useToast'
import { errorMessage, isValidSessionName, timestamp } from '../lib/format'
import { useShell } from '../components/layout/useShell'
import { WorkspaceContext } from './WorkspaceContext'
import { AssistantDock } from './AssistantDock'

type ChatTurn = { role: 'user' | 'bot'; text: string }

function latestSession(list: SessionSummary[]): SessionSummary | undefined {
  return [...list].sort((left, right) => timestamp(right.updated_at) - timestamp(left.updated_at))[0]
}

function getChatStorageKey(sessionName: string, projectId: number | null, scopeKey: string): string {
  if (sessionName) return `aiplanx_chat_session_${sessionName}`
  if (projectId != null) return `aiplanx_chat_project_${projectId}`
  return `aiplanx_chat_${scopeKey}`
}

function loadStoredChat(key: string): ChatTurn[] {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) {
      return parsed.filter(
        (t): t is ChatTurn =>
          t && (t.role === 'user' || t.role === 'bot') && typeof t.text === 'string'
      )
    }
  } catch {
    // ignore
  }
  return []
}

function saveStoredChat(key: string, chat: ChatTurn[]) {
  try {
    if (chat.length === 0) {
      localStorage.removeItem(key)
    } else {
      localStorage.setItem(key, JSON.stringify(chat.slice(-50)))
    }
  } catch {
    // ignore
  }
}

export function WorkspaceProvider({ children }: { children?: ReactNode }) {
  const params = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { setChrome } = useShell()
  const toast = useToast()
  const projectId = params.projectId && /^\d+$/.test(params.projectId) ? Number(params.projectId) : null
  const routeSession = params.sessionName || ''
  const scopeKey = routeSession ? `session:${routeSession}` : `project:${params.projectId ?? ''}`

  const [scopeSeen, setScopeSeen] = useState(scopeKey)
  const [preferredName, setPreferredName] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const [project, setProject] = useState<ProjectListItem | null>(null)
  const [linkedSessions, setLinkedSessions] = useState<SessionSummary[]>([])
  const [sessionName, setSessionName] = useState('')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [tasks, setTasks] = useState<TaskRow[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [schedule, setSchedule] = useState<ScheduledTask[]>([])
  const [report, setReport] = useState<ManagementReportPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [planDescription, setPlanDescription] = useState('')
  const [planSessionName, setPlanSessionName] = useState('')
  const [planJob, setPlanJob] = useState<PlanJob | null>(null)
  const [planning, setPlanning] = useState(false)
  const currentChatKey = getChatStorageKey(sessionName, projectId, scopeKey)
  const [activeChatKey, setActiveChatKey] = useState(() => getChatStorageKey('', projectId, scopeKey))
  const [chat, setChat] = useState<ChatTurn[]>(() => loadStoredChat(getChatStorageKey('', projectId, scopeKey)))
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(() => {
    try {
      return localStorage.getItem('aiplanx_assistant_open') === 'true'
    } catch {
      return false
    }
  })
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)
  const [progressPercent, setProgressPercent] = useState(0)
  const [taskStatus, setTaskStatus] = useState('in_progress')
  const [actualHours, setActualHours] = useState('')
  const [delayHours, setDelayHours] = useState('4')
  const [delayReason, setDelayReason] = useState('')
  const [delayWeeks, setDelayWeeks] = useState('1')
  const [reassignId, setReassignId] = useState('')
  const [reassignReason, setReassignReason] = useState('Capacity adjustment')

  if (scopeSeen !== scopeKey) {
    setScopeSeen(scopeKey)
    setPreferredName(null)
    setPlanDescription('')
    setPlanSessionName('')
    setPlanJob(null)
    setPlanning(false)
    setQuestion('')
    setActionError('')
    setSelectedTaskId(null)
  }

  if (currentChatKey !== activeChatKey) {
    setActiveChatKey(currentChatKey)
    setChat(loadStoredChat(currentChatKey))
  }

  useEffect(() => {
    if (activeChatKey) {
      saveStoredChat(activeChatKey, chat)
    }
  }, [chat, activeChatKey])

  const updateAssistantOpen = useCallback((open: boolean) => {
    setAssistantOpen(open)
    try {
      localStorage.setItem('aiplanx_assistant_open', String(open))
    } catch {
      // ignore
    }
  }, [])

  const clearChat = useCallback(() => {
    setChat([])
    if (activeChatKey) {
      try {
        localStorage.removeItem(activeChatKey)
      } catch {
        // ignore
      }
    }
  }, [activeChatKey])

  const clearSessionData = useCallback(() => {
    setSessionName('')
    setOverview(null)
    setTasks([])
    setSchedule([])
    setReport(null)
    setSelectedTaskId(null)
  }, [])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      if (params.projectId && projectId == null) {
        setError('That project address is not valid.')
        setLoading(false)
        return
      }
      try {
        let savedProject: ProjectListItem | null = null
        let sessionPayload: { sessions: SessionSummary[] }
        let employeePayload: { employees: Employee[] }

        if (projectId != null) {
          const [projectDetail, sessionsRes, employeesRes] = await Promise.all([
            api.getProject(projectId),
            api.sessions(),
            api.employees(projectId),
          ])
          if (cancelled) return
          savedProject = projectDetail
          sessionPayload = sessionsRes
          employeePayload = employeesRes
        } else {
          const [sessionsRes, employeesRes] = await Promise.all([
            api.sessions(),
            api.employees(),
          ])
          if (cancelled) return
          sessionPayload = sessionsRes
          employeePayload = employeesRes
          savedProject = null
        }
        setEmployees(employeePayload.employees)
        setProject(savedProject)

        let nextName = ''
        let related: SessionSummary[] = []
        if (routeSession) {
          const match = sessionPayload.sessions.find((item) => item.name === routeSession)
          if (!match) {
            clearSessionData()
            setLinkedSessions([])
            setError(`Session "${routeSession}" was not found.`)
            return
          }
          related = match.project_id == null
            ? [match]
            : sessionPayload.sessions.filter((item) => item.project_id === match.project_id)
          if (match.project_id != null) {
            try {
              savedProject = await api.getProject(match.project_id)
              const matchEmps = await api.employees(match.project_id)
              if (!cancelled) setEmployees(matchEmps.employees)
            } catch {
              savedProject = null
            }
          }
          setProject(savedProject)
          nextName = match.name
        } else if (projectId != null) {
          related = sessionPayload.sessions.filter((item) => item.project_id === projectId)
          if (!savedProject && related.length === 0) {
            clearSessionData()
            setLinkedSessions([])
            setError('That project was not found.')
            return
          }
          const preferred = related.find((item) => item.name === preferredName)
          nextName = preferred?.name || latestSession(related)?.name || ''
        }
        setLinkedSessions(related)
        if (!nextName) {
          clearSessionData()
          return
        }
        const [overviewPayload, taskPayload, schedulePayload, reportPayload] = await Promise.all([
          api.overview(nextName),
          api.tasks(nextName),
          api.schedule(nextName),
          api.report(nextName),
        ])
        if (cancelled) return
        setSessionName(nextName)
        setOverview(overviewPayload)
        setTasks(taskPayload.tasks)
        setSchedule(schedulePayload.scheduled_tasks ?? [])
        setReport(reportPayload)
        setSelectedTaskId(null)
      } catch (err) {
        if (!cancelled) {
          clearSessionData()
          setError(errorMessage(err, 'Failed to load this project'))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [scopeKey, preferredName, reloadToken, projectId, routeSession, params.projectId, clearSessionData])

  useEffect(() => {
    const projectName = overview?.project.name
      || project?.name
      || linkedSessions.find((item) => item.name === sessionName)?.project_name
      || null
    setChrome({ projectName, sessionLabel: sessionName || null })
  }, [overview, project, linkedSessions, sessionName, setChrome])

  useEffect(() => () => setChrome({ projectName: null, sessionLabel: null }), [setChrome])

  useEffect(() => {
    if (!planJob || (planJob.status !== 'queued' && planJob.status !== 'running')) return
    let cancelled = false
    const timer = window.setInterval(async () => {
      try {
        const next = await api.planJob(planJob.id)
        if (cancelled) return
        setPlanJob(next)
        if (next.status === 'completed') {
          setPlanning(false)
          if (next.session_name) setPreferredName(next.session_name)
          setReloadToken((value) => value + 1)
          if (next.project_id != null && next.project_id !== projectId) {
            navigate(`/projects/${next.project_id}/overview`)
          } else if (next.project_id == null && next.session_name && next.session_name !== routeSession) {
            navigate(`/sessions/${encodeURIComponent(next.session_name)}/overview`)
          }
          toast({ title: 'Plan ready', message: 'The workspace is opening the saved project.', tone: 'success' })
        }
        if (next.status === 'failed') {
          setPlanning(false)
          setActionError(next.error || 'Planning failed')
        }
      } catch (err) {
        if (cancelled) return
        setPlanning(false)
        setActionError(errorMessage(err, 'Failed to poll planning job'))
      }
    }, 1500)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [planJob, projectId, routeSession, navigate, toast])

  const selectedTask = useMemo(
    () => tasks.find((task) => task.task_id === selectedTaskId) ?? null,
    [tasks, selectedTaskId],
  )

  const selectTask = useCallback((task: TaskRow) => {
    setSelectedTaskId(task.task_id)
    setTaskStatus(task.status)
    setProgressPercent(task.progress_percent)
    setActualHours(String(task.actual_hours_spent || ''))
    setReassignId(task.employee_id || employees[0]?.employee_id || '')
  }, [employees])

  const reload = useCallback(() => setReloadToken((value) => value + 1), [])

  async function refreshSession() {
    if (!sessionName) return
    const [overviewPayload, taskPayload, schedulePayload, reportPayload, employeesPayload] = await Promise.all([
      api.overview(sessionName),
      api.tasks(sessionName),
      api.schedule(sessionName),
      api.report(sessionName),
      api.employees(projectId ?? undefined),
    ])
    setOverview(overviewPayload)
    setTasks(taskPayload.tasks)
    setSchedule(schedulePayload.scheduled_tasks ?? [])
    setReport(reportPayload)
    setEmployees(employeesPayload.employees)
  }

  async function startPlan(event: FormEvent) {
    event.preventDefault()
    setActionError('')
    if (planSessionName && !isValidSessionName(planSessionName)) {
      setActionError('Session names use 1–64 letters, numbers, underscores, or hyphens.')
      return
    }
    setPlanning(true)
    try {
      const started = await api.startPlan(planDescription, planSessionName || undefined)
      setPlanJob(await api.planJob(started.job_id))
    } catch (err) {
      setPlanning(false)
      setActionError(errorMessage(err, 'Planning failed to start'))
    }
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
      const result = await api.askAssistant(sessionName, text, chat)
      setChat((current) => [...current, { role: 'bot', text: result.answer }])
    } catch (err) {
      const message = errorMessage(err, 'Assistant is unavailable')
      setActionError(message)
      setChat((current) => [...current, { role: 'bot', text: message }])
    } finally {
      setAsking(false)
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
      toast({ title: 'Progress saved', tone: 'success' })
    } catch (err) {
      setActionError(errorMessage(err, 'Could not update progress'))
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
      toast({ title: 'Delay recorded', tone: 'success' })
    } catch (err) {
      setActionError(errorMessage(err, 'Could not record delay'))
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
      toast({ title: 'Schedule analyzed', tone: 'success' })
      const base = location.pathname.replace(/\/[^/]+$/, '')
      navigate(`${base}/reports`)
    } catch (err) {
      setActionError(errorMessage(err, 'Could not analyze delay'))
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
      toast({ title: 'Task reassigned', tone: 'success' })
    } catch (err) {
      setActionError(errorMessage(err, 'Could not reassign task'))
    }
  }

  async function addCollaborator(employeeId: string, reason = 'Collaborator added') {
    if (!sessionName || !selectedTask || !employeeId) return
    setActionError('')
    try {
      await api.addCollaborator(sessionName, selectedTask.task_id, {
        employee_id: employeeId,
        reason,
      })
      await refreshSession()
      toast({ title: 'Collaborator added', tone: 'success' })
    } catch (err) {
      setActionError(errorMessage(err, 'Could not add collaborator'))
      throw err
    }
  }

  async function removeCollaborator(employeeId: string) {
    if (!sessionName || !selectedTask || !employeeId) return
    setActionError('')
    try {
      await api.removeCollaborator(sessionName, selectedTask.task_id, employeeId)
      await refreshSession()
      toast({ title: 'Collaborator removed', tone: 'success' })
    } catch (err) {
      setActionError(errorMessage(err, 'Could not remove collaborator'))
      throw err
    }
  }

  const onAssistant = location.pathname.endsWith('/assistant')
  const value = {
    projectId,
    project,
    sessionName,
    sessions: linkedSessions,
    overview,
    tasks,
    employees,
    schedule,
    report,
    planDescription,
    planSessionName,
    planJob,
    planning,
    chat,
    question,
    asking,
    assistantOpen,
    selectedTask,
    progressPercent,
    taskStatus,
    actualHours,
    delayHours,
    delayReason,
    delayWeeks,
    reassignId,
    reassignReason,
    setPlanDescription,
    setPlanSessionName,
    setQuestion,
    setAssistantOpen: updateAssistantOpen,
    clearChat,
    selectTask,
    setProgressPercent,
    setTaskStatus,
    setActualHours,
    setDelayHours,
    setDelayReason,
    setDelayWeeks,
    setReassignId,
    setReassignReason,
    switchSession: setPreferredName,
    reload,
    startPlan,
    submitQuestion,
    saveProgress,
    saveDelay,
    runDelayAnalysis,
    saveReassign,
    addCollaborator,
    removeCollaborator,
    actionError,
    setActionError,
  }

  return (
    <WorkspaceContext.Provider value={value}>
      {loading ? <PageSkeleton /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <>
          {!routeSession && linkedSessions.length > 1 && (
            <div className="ax-toolbar">
              <Select
                label="Management session"
                value={sessionName}
                onChange={(event) => setPreferredName(event.target.value)}
              >
                {linkedSessions.map((item) => (
                  <option key={item.name} value={item.name}>{item.name} · {item.task_count} tasks</option>
                ))}
              </Select>
            </div>
          )}
          <p className="ax-count">
            {sessionName ? `Session ${sessionName}` : 'No management session is linked to this project yet.'}
          </p>
          {actionError && <Banner onDismiss={() => setActionError('')}>{actionError}</Banner>}
          {children ?? <Outlet />}
          {!onAssistant && <AssistantDock />}
        </>
      )}
    </WorkspaceContext.Provider>
  )
}
