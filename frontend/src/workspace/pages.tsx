import { useEffect, useId, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, type Overview, type TaskActivity, type TaskRow } from '../api'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Input, TextArea } from '../components/ui/Input'
import { ProgressBar, ProgressRing } from '../components/ui/ProgressBar'
import { Select } from '../components/ui/Select'
import { StatusBadge } from '../components/ui/StatusBadge'
import { DataTable, Td, Th, Tr } from '../components/ui/Table'
import { errorMessage, formatWhen } from '../lib/format'
import { workspaceBase } from '../navigation'
import { useTheme } from '../theme/useTheme'
import { useWorkspace } from './useWorkspace'

function useSection(segment: string): string {
  const { pathname } = useLocation()
  const base = workspaceBase(pathname)
  return base ? `${base}/${segment}` : '/projects'
}

function usePlotTheme() {
  const { resolved } = useTheme()
  if (resolved === 'light') {
    return {
      grid: '#e1e7f2',
      tick: '#4d5b78',
      planned: '#6844e8',
      actual: '#0d7354',
      tip: '#ffffff',
      tipLine: '#e1e7f2',
      tipText: '#12192d',
    }
  }
  return {
    grid: 'rgba(160,182,230,0.25)',
    tick: '#a9b6d0',
    planned: '#b69cff',
    actual: '#5dceab',
    tip: '#0e1730',
    tipLine: 'rgba(160,182,230,0.3)',
    tipText: '#e8eefc',
  }
}

function ProgressChart({ overview }: { overview: Overview }) {
  const plot = usePlotTheme()
  const gradientId = useId().replace(/:/g, '')
  return (
    <div className="ax-chart">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={overview.chart} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <defs>
            <linearGradient id={`${gradientId}-planned`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={plot.planned} stopOpacity={0.28} />
              <stop offset="100%" stopColor={plot.planned} stopOpacity={0} />
            </linearGradient>
            <linearGradient id={`${gradientId}-actual`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={plot.actual} stopOpacity={0.28} />
              <stop offset="100%" stopColor={plot.actual} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={plot.grid} strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="week" axisLine={false} tickLine={false} tick={{ fill: plot.tick, fontSize: 11 }} />
          <YAxis axisLine={false} tickLine={false} tick={{ fill: plot.tick, fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
          <Tooltip contentStyle={{ background: plot.tip, border: `1px solid ${plot.tipLine}`, borderRadius: 10, color: plot.tipText, fontSize: 12 }} />
          <Area type="monotone" dataKey="planned" name="Planned" stroke={plot.planned} strokeWidth={2} fill={`url(#${gradientId}-planned)`} />
          <Area type="monotone" dataKey="actual" name="Actual" stroke={plot.actual} strokeWidth={2.5} fill={`url(#${gradientId}-actual)`} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function NoSession({ detail }: { detail: string }) {
  const studio = useSection('studio')
  return (
    <EmptyState
      title="No management session"
      message={detail}
      action={<Link to={studio} className="ax-btn ax-btn-primary">Open AI Planning Studio</Link>}
    />
  )
}

export function OverviewPage() {
  const { overview, sessionName } = useWorkspace()
  const tasksPath = useSection('tasks')
  const reportsPath = useSection('reports')
  const activityPath = useSection('activity')
  if (!sessionName || !overview) {
    return <NoSession detail="This project is saved, but progress, health, and tasks come from a management session. Generate a plan to open one." />
  }
  const progress = overview.progress
  return (
    <div className="ax-stack">
      <Card>
        <div className="ax-spread">
          <div>
            <StatusBadge label={overview.project.status_label} />
            <h2 style={{ marginTop: 8 }}>{overview.project.name}</h2>
            <p className="ax-clamp-2">{overview.project.summary}</p>
            <p className="ax-meta">
              <span>Session {overview.session_name}</span>
              <span>{overview.team_size} people on the plan</span>
              <span>{overview.project.total_estimated_hours} estimated hours</span>
              <span>{overview.completion_week ? `Target week ${overview.completion_week}` : 'No target week'}</span>
            </p>
          </div>
          <ProgressRing value={progress.overall_percent} label="Project progress" />
        </div>
      </Card>
      <div className="ax-metrics">
        <Card><span className="ax-kicker">Total tasks</span><div className="ax-metric-value">{progress.total_tasks}</div><p className="ax-hint">{progress.pending} pending</p></Card>
        <Card><span className="ax-kicker">Completed</span><div className="ax-metric-value">{progress.completed}</div><p className="ax-hint">{progress.in_progress} in progress</p></Card>
        <Card><span className="ax-kicker">Blocked</span><div className="ax-metric-value">{progress.blocked}</div><p className="ax-hint">{progress.at_risk} at risk</p></Card>
        <Card><span className="ax-kicker">Health</span><div className="ax-metric-value">{overview.health.score}</div><p className="ax-hint">{overview.health.label}</p></Card>
      </div>
      <div className="ax-split">
        <Card>
          <h2>Planned vs actual</h2>
          <p className="ax-hint">Completion by scheduled week for this session.</p>
          {overview.chart.length === 0 ? <p className="ax-hint">No weekly progress series is stored for this session.</p> : <ProgressChart overview={overview} />}
        </Card>
        <Card className="ax-stack">
          <h2>Project health</h2>
          <ProgressBar value={overview.health.schedule} label="Schedule" />
          <ProgressBar value={overview.health.delivery} label="Delivery" />
          <ProgressBar value={overview.health.resources} label="Resources" />
          <Link to={reportsPath} className="ax-btn ax-btn-ghost ax-btn-sm">View health report</Link>
        </Card>
      </div>
      <div className="ax-split">
        <Card>
          <div className="ax-spread">
            <h2>Priority tasks</h2>
            <Link to={tasksPath} className="ax-btn ax-btn-ghost ax-btn-sm">View all</Link>
          </div>
          {overview.priority_tasks.length === 0 ? <p className="ax-hint">No priority tasks returned.</p> : (
            <DataTable>
              <thead><tr><Th>Task</Th><Th>Assignee</Th><Th>Status</Th><Th>Progress</Th><Th>Due</Th></tr></thead>
              <tbody>
                {overview.priority_tasks.map((task) => (
                  <Tr key={task.task_id}>
                    <Td><strong>{task.title}</strong><p className="ax-hint">{task.priority} priority</p></Td>
                    <Td>{task.owner}</Td>
                    <Td><StatusBadge label={task.status} /></Td>
                    <Td>{Math.round(task.progress)}%</Td>
                    <Td>{task.due}</Td>
                  </Tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </Card>
        <Card>
          <div className="ax-spread">
            <h2>Recent activity</h2>
            <Link to={activityPath} className="ax-btn ax-btn-ghost ax-btn-sm">History</Link>
          </div>
          {overview.activities.length === 0 ? <p className="ax-hint">No activity recorded yet.</p> : (
            <div className="ax-stack" style={{ marginTop: 12 }}>
              {overview.activities.map((activity, index) => (
                <div key={`${activity.title}-${index}`}>
                  <strong>{activity.title}</strong>
                  <p className="ax-hint">{activity.detail}</p>
                  <p className="ax-hint">{activity.time}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

export function StudioPage() {
  const { planDescription, planSessionName, planJob, planning, setPlanDescription, setPlanSessionName, startPlan } = useWorkspace()
  return (
    <Card>
      <h2>Generate a project plan</h2>
      <p className="ax-hint">This runs the existing planning job, stores the report, and can open a management session. It is separate from naming a project.</p>
      <form className="ax-stack" style={{ marginTop: 14 }} onSubmit={startPlan}>
        <TextArea
          label="Project description"
          value={planDescription}
          minLength={10}
          required
          placeholder="Describe the project, constraints, and desired outcomes."
          onChange={(event) => setPlanDescription(event.target.value)}
        />
        <Input
          label="Session name (optional)"
          value={planSessionName}
          placeholder="campus-platform"
          hint="Leave blank to let the API name the session. Use letters, numbers, underscores, or hyphens."
          onChange={(event) => setPlanSessionName(event.target.value)}
        />
        <div>
          <Button type="submit" disabled={planning}>{planning ? 'Planning…' : 'Start planning job'}</Button>
        </div>
        {planJob && (
          <p className="ax-hint">
            Job {planJob.id.slice(0, 8)} · {planJob.status}
            {planJob.error ? ` · ${planJob.error}` : ''}
            {planJob.session_name ? ` · session ${planJob.session_name}` : ''}
            {planJob.project_id != null ? ` · project ${planJob.project_id}` : ''}
          </p>
        )}
      </form>
    </Card>
  )
}

export function TasksPage() {
  const workspace = useWorkspace()
  const [query, setQuery] = useState('')
  if (!workspace.sessionName) {
    return <NoSession detail="Task updates, delays, and reassignment need the session linked to this project." />
  }
  const needle = query.trim().toLowerCase()
  const tasks = needle
    ? workspace.tasks.filter((task) => `${task.title} ${task.owner} ${task.status_label}`.toLowerCase().includes(needle))
    : workspace.tasks
  return (
    <div className="ax-split">
      <Card>
        <Input label="Search tasks" value={query} placeholder="Title, owner, or status" onChange={(event) => setQuery(event.target.value)} />
        {tasks.length === 0 ? <p className="ax-hint">No tasks match.</p> : (
          <DataTable>
            <thead><tr><Th>Task</Th><Th>Assignee</Th><Th>Status</Th><Th>Progress</Th><Th>Due</Th></tr></thead>
            <tbody>
              {tasks.map((task) => (
                <Tr key={task.task_id} data-clickable selected={workspace.selectedTask?.task_id === task.task_id} onClick={() => workspace.selectTask(task)}>
                  <Td><strong>{task.title}</strong><p className="ax-hint">{task.priority} priority</p></Td>
                  <Td>{task.owner}</Td>
                  <Td><StatusBadge label={task.status_label} /></Td>
                  <Td>{Math.round(task.progress_percent)}%</Td>
                  <Td>{task.due}</Td>
                </Tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </Card>
      <TaskEditor />
    </div>
  )
}

function TaskEditor() {
  const {
    selectedTask, employees, progressPercent, taskStatus, actualHours, delayHours, delayReason, delayWeeks,
    reassignId, reassignReason, setProgressPercent, setTaskStatus, setActualHours, setDelayHours, setDelayReason,
    setDelayWeeks, setReassignId, setReassignReason, saveProgress, saveDelay, runDelayAnalysis, saveReassign,
  } = useWorkspace()
  if (!selectedTask) return <Card><p className="ax-hint">Select a task to update progress, record a delay, or reassign it.</p></Card>
  return (
    <Card className="ax-stack">
      <div>
        <h2>{selectedTask.title}</h2>
        <p className="ax-hint">{selectedTask.description}</p>
      </div>
      <form className="ax-stack" onSubmit={saveProgress}>
        <div className="ax-form-grid">
          <Select label="Status" value={taskStatus} onChange={(event) => setTaskStatus(event.target.value)}>
            <option value="pending">Pending</option>
            <option value="in_progress">In progress</option>
            <option value="blocked">Blocked</option>
            <option value="completed">Completed</option>
          </Select>
          <Input label="Progress %" type="number" min={0} max={100} value={progressPercent} onChange={(event) => setProgressPercent(Number(event.target.value))} />
          <Input label="Hours spent" type="number" min={0} value={actualHours} onChange={(event) => setActualHours(event.target.value)} />
        </div>
        <div><Button type="submit">Save progress</Button></div>
      </form>
      <form className="ax-stack" onSubmit={saveDelay}>
        <div className="ax-form-grid">
          <Input label="Delay hours" type="number" min={0.1} step="0.5" value={delayHours} onChange={(event) => setDelayHours(event.target.value)} />
          <Input label="Reason" value={delayReason} required placeholder="Blocked on review" onChange={(event) => setDelayReason(event.target.value)} />
        </div>
        <div><Button type="submit" variant="secondary">Record delay</Button></div>
      </form>
      <form className="ax-stack" onSubmit={runDelayAnalysis}>
        <Input label="Analyze delay (weeks)" type="number" min={1} max={52} value={delayWeeks} onChange={(event) => setDelayWeeks(event.target.value)} />
        <div><Button type="submit" variant="secondary">Analyze schedule impact</Button></div>
      </form>
      <form className="ax-stack" onSubmit={saveReassign}>
        <Select label="Reassign to" value={reassignId} onChange={(event) => setReassignId(event.target.value)}>
          {employees.length === 0 && <option value="">No employees returned</option>}
          {employees.map((employee) => (
            <option key={employee.employee_id} value={employee.employee_id}>{employee.employee_name} · {employee.role}</option>
          ))}
        </Select>
        <Input label="Reason" value={reassignReason} required onChange={(event) => setReassignReason(event.target.value)} />
        <div><Button type="submit" variant="secondary" disabled={!reassignId}>Reassign task</Button></div>
      </form>
    </Card>
  )
}

export function TeamPage() {
  const { employees, schedule, sessionName } = useWorkspace()
  return (
    <div className="ax-stack">
      {employees.length === 0 ? (
        <EmptyState title="No employees returned" message="The scheduler roster from /api/employees is empty." />
      ) : (
        <div className="ax-card-grid">
          {employees.map((employee) => (
            <Card key={employee.employee_id} className="ax-stack">
              <div>
                <h2>{employee.employee_name}</h2>
                <p className="ax-hint">{employee.role} · {employee.experience} years · {employee.weekly_capacity_hours}h / week</p>
              </div>
              <ProgressBar value={employee.current_workload_percent} label="Workload" />
              <div>{employee.skills.map((skill) => <span className="ax-skill" key={skill}>{skill}</span>)}</div>
            </Card>
          ))}
        </div>
      )}
      <Card>
        <h2>Work schedule</h2>
        <p className="ax-hint">{sessionName ? `Allocated weeks for session ${sessionName}.` : 'A session is required before this project has a schedule.'}</p>
        {schedule.length === 0 ? <p className="ax-hint">No scheduled tasks were returned.</p> : (
          <DataTable>
            <thead><tr><Th>Task</Th><Th>Owner</Th><Th>Hours</Th><Th>Weeks</Th></tr></thead>
            <tbody>
              {schedule.map((item) => (
                <Tr key={`${item.task_id}-${item.employee_id}`}>
                  <Td>{item.task_title}</Td>
                  <Td>{item.employee_name}</Td>
                  <Td>{item.total_estimated_hours}</Td>
                  <Td>W{item.start_week}–W{item.completion_week}</Td>
                </Tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </Card>
    </div>
  )
}

export function TimelinePage() {
  const { overview, schedule, sessionName } = useWorkspace()
  if (!sessionName || !overview) {
    return <NoSession detail="Planned and actual progress is stored on the management session, not on the project id alone." />
  }
  return (
    <div className="ax-stack">
      <Card>
        <h2>Progress</h2>
        <ProgressBar value={overview.progress.overall_percent} label="Overall" />
        {overview.chart.length === 0 ? <p className="ax-hint">No weekly series is stored.</p> : <ProgressChart overview={overview} />}
      </Card>
      <Card>
        <h2>Scheduled weeks</h2>
        {schedule.length === 0 ? <p className="ax-hint">No scheduled tasks were returned for this session.</p> : (
          <DataTable>
            <thead><tr><Th>Task</Th><Th>Owner</Th><Th>Start</Th><Th>Completion</Th><Th>Weekly hours</Th></tr></thead>
            <tbody>
              {schedule.map((item) => (
                <Tr key={`${item.task_id}-${item.employee_id}`}>
                  <Td>{item.task_title}</Td>
                  <Td>{item.employee_name}</Td>
                  <Td>Week {item.start_week}</Td>
                  <Td>Week {item.completion_week}</Td>
                  <Td>{item.weekly_allocations.map((slot) => `W${slot.week}: ${slot.allocated_hours}h`).join(', ') || '—'}</Td>
                </Tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </Card>
    </div>
  )
}

export function ReportsPage() {
  const { report, sessionName } = useWorkspace()
  if (!sessionName) return <NoSession detail="Reports are generated from the management session." />
  if (!report) return <EmptyState title="No report" message="This session did not return a management report." />
  const management = report.management_report
  const insights = report.insights
  const risks = report.planning_report?.risk_analysis?.risks ?? []
  return (
    <div className="ax-card-grid">
      <Card className="ax-stack">
        <h2>{management.project_name}</h2>
        <p className="ax-hint">
          {management.progress.completed_tasks} completed · {management.progress.in_progress_tasks} in progress · {management.progress.blocked_tasks} blocked · {management.progress.pending_tasks} pending
        </p>
        <ul className="ax-list">
          {management.recommendations.length === 0 && <li>No recommendations returned.</li>}
          {management.recommendations.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </Card>
      <Card className="ax-stack">
        <h2>Delays</h2>
        <p className="ax-hint">Revised completion week {management.revised_completion_week ?? 'unchanged'}</p>
        <ul className="ax-list">
          {management.task_delays.length === 0 && <li>No delays recorded.</li>}
          {management.task_delays.map((item) => (
            <li key={`${item.task_id}-${item.reason}`}>{item.task_title}: {item.delay_hours}h · {item.reason}</li>
          ))}
        </ul>
      </Card>
      <Card className="ax-stack">
        <h2>AI insights</h2>
        {insights?.unavailable ? (
          <p className="ax-hint">{insights.reason || 'Insights are unavailable.'}</p>
        ) : (
          <>
            <p className="ax-hint">{insights?.executive_summary || 'No executive summary returned.'}</p>
            <ul className="ax-list">
              {(insights?.recovery_recommendations ?? []).map((item) => <li key={item}>{item}</li>)}
              {(insights?.identified_risks ?? []).map((item) => <li key={item}>{item}</li>)}
            </ul>
          </>
        )}
      </Card>
      <Card className="ax-stack">
        <h2>Planning risks</h2>
        <p className="ax-hint">{report.planning_report?.risk_analysis?.overall_risk_level || 'No risk level returned'}</p>
        <ul className="ax-list">
          {risks.length === 0 && <li>No planning risks returned.</li>}
          {risks.map((risk) => <li key={risk.title}>{risk.severity}: {risk.title} — {risk.mitigation}</li>)}
        </ul>
      </Card>
    </div>
  )
}

const prompts = ['Summarize project status', 'Which tasks need attention?', 'Suggest next priorities']

export function AssistantPage() {
  const { sessionName, chat, question, asking, setQuestion, submitQuestion } = useWorkspace()
  if (!sessionName) return <NoSession detail="The assistant answers from a live session and does not change saved project state." />
  return (
    <Card className="ax-stack">
      <p className="ax-hint">Answers use session {sessionName} and do not change saved project state.</p>
      {chat.length === 0 && (
        <div className="ax-suggest">
          {prompts.map((text) => (
            <button key={text} type="button" onClick={() => setQuestion(text)}>{text}</button>
          ))}
        </div>
      )}
      <div className="ax-chat">
        {chat.map((turn, index) => (
          <p className={turn.role === 'user' ? 'ax-chat-user' : 'ax-chat-bot'} key={`${turn.role}-${index}`}>{turn.text}</p>
        ))}
        {asking && <p className="ax-chat-bot">Thinking with live project context…</p>}
      </div>
      <form className="ax-assistant-form" onSubmit={submitQuestion}>
        <Input value={question} placeholder="Ask about this session" onChange={(event) => setQuestion(event.target.value)} />
        <Button type="submit" disabled={asking || !question.trim()}>Send</Button>
      </form>
    </Card>
  )
}

export function ActivityPage() {
  const { sessionName, tasks } = useWorkspace()
  const [rows, setRows] = useState<{ task: TaskRow; activities: TaskActivity[]; error: string }[]>([])
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState('')

  useEffect(() => {
    if (!sessionName) return
    let cancelled = false
    async function load() {
      setLoading(true)
      setFailed('')
      try {
        const next = await Promise.all(tasks.map(async (task) => {
          try {
            const payload = await api.taskActivity(sessionName, task.task_id)
            return { task, activities: payload.activities, error: '' }
          } catch (err) {
            return { task, activities: [], error: errorMessage(err, 'Could not load activity') }
          }
        }))
        if (!cancelled) setRows(next)
      } catch (err) {
        if (!cancelled) setFailed(errorMessage(err, 'Could not load activity'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [sessionName, tasks])

  if (!sessionName) return <NoSession detail="Activity history is the task updates recorded on the management session." />
  if (loading) return <p className="ax-spinner"><span className="ax-spinner-dot" /> Loading activity</p>
  if (failed) return <EmptyState title="Activity unavailable" message={failed} />
  const recorded = rows.filter((row) => row.activities.length > 0 || row.error)
  if (recorded.length === 0) return <EmptyState title="No activity yet" message="No task updates have been recorded for this session." />
  return (
    <div className="ax-stack">
      {recorded.map((row) => (
        <Card key={row.task.task_id} className="ax-stack">
          <h2>{row.task.title}</h2>
          {row.error && <p className="ax-hint">{row.error}</p>}
          {row.activities.map((activity, index) => (
            <div key={`${activity.recorded_at}-${index}`}>
              <strong>{activity.updated_by}</strong>
              <p className="ax-hint">{formatWhen(activity.recorded_at)} · {activity.status} · {activity.progress_percent}%</p>
              {activity.comment && <p>{activity.comment}</p>}
              {activity.completed_work && <p className="ax-hint">Done: {activity.completed_work}</p>}
              {activity.remaining_work && <p className="ax-hint">Remaining: {activity.remaining_work}</p>}
              {activity.blockers.length > 0 && <p className="ax-hint">Blockers: {activity.blockers.join(', ')}</p>}
            </div>
          ))}
        </Card>
      ))}
    </div>
  )
}
