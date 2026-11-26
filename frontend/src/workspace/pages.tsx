import { useEffect, useId, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Bot, ChevronDown, ChevronRight, Pencil, Trash2, UserPlus } from 'lucide-react'
import { api, type Overview, type TaskActivity, type TaskRow, type TeamMember } from '../api'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Input, TextArea } from '../components/ui/Input'
import { ProgressBar, ProgressRing } from '../components/ui/ProgressBar'
import { Select } from '../components/ui/Select'
import { StatusBadge } from '../components/ui/StatusBadge'
import { DataTable, Td, Th, Tr } from '../components/ui/Table'
import { useToast } from '../components/ui/useToast'
import { MarkdownRenderer } from '../components/ui/MarkdownRenderer'
import { ChatInput } from '../components/ui/ChatInput'
import { cn } from '../lib/cn'
import { errorMessage, formatWhen } from '../lib/format'
import { workspaceBase } from '../navigation'
import { useTheme } from '../theme/useTheme'
import { AddTeamMemberDialog, DeleteTeamMemberDialog, EditTeamMemberDialog } from './TeamMemberDialogs'
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
                  <Td>
                    <div>{task.owner}</div>
                    {task.collaborators && task.collaborators.length > 1 && (
                      <span className="ax-hint" style={{ fontSize: '0.75rem' }}>
                        {task.collaborators.length} collaborators
                      </span>
                    )}
                  </Td>
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

const SKILL_ALIASES: Record<string, string> = {
  postgres: 'postgresql',
  postgresql: 'postgresql',
  js: 'javascript',
  javascript: 'javascript',
  py: 'python',
  python: 'python',
  'react.js': 'react',
  reactjs: 'react',
  react: 'react',
  'node.js': 'nodejs',
  nodejs: 'nodejs',
}

function normalizeSkill(skill: string): string {
  const s = skill.trim().toLowerCase()
  return SKILL_ALIASES[s] || s
}

function calculateSkillMatch(candidateSkills: string[], requiredSkills: string[]): { qualifies: boolean; percent: number } {
  const req = requiredSkills.map(normalizeSkill).filter(Boolean)
  if (req.length === 0) return { qualifies: true, percent: 100 }
  const cand = new Set(candidateSkills.map(normalizeSkill).filter(Boolean))
  const matched = req.filter((s) => cand.has(s)).length
  const ratio = matched / req.length
  return { qualifies: ratio >= 0.5, percent: Math.round(ratio * 100) }
}

function TaskEditor() {
  const {
    selectedTask, employees, progressPercent, taskStatus, actualHours, delayHours, delayReason, delayWeeks,
    reassignId, reassignReason, setProgressPercent, setTaskStatus, setActualHours, setDelayHours, setDelayReason,
    setDelayWeeks, setReassignId, setReassignReason, saveProgress, saveDelay, runDelayAnalysis, saveReassign,
    addCollaborator, removeCollaborator, actionError, setActionError,
  } = useWorkspace()

  const [collabId, setCollabId] = useState('')
  const [collabReason, setCollabReason] = useState('Collaborator added')
  const [addingCollab, setAddingCollab] = useState(false)
  const [removingId, setRemovingId] = useState<string | null>(null)

  if (!selectedTask) return <Card><p className="ax-hint">Select a task to update progress, record a delay, or reassign it.</p></Card>

  const collaborators = selectedTask.collaborators && selectedTask.collaborators.length > 0
    ? selectedTask.collaborators
    : selectedTask.employee_id
      ? [{ employee_id: selectedTask.employee_id, employee_name: selectedTask.owner }]
      : []

  const assignedEmpIds = new Set(
    collaborators.flatMap((c) => [
      c.employee_id,
      c.employee_id.replace(/^TM/, ''),
      c.employee_name.toLowerCase(),
    ])
  )
  const availableForCollab = employees.filter(
    (e) =>
      !assignedEmpIds.has(e.employee_id) &&
      !assignedEmpIds.has(e.employee_id.replace(/^TM/, '')) &&
      !assignedEmpIds.has(e.employee_name.toLowerCase())
  )

  const handleAddCollaborator = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!collabId) return
    setAddingCollab(true)
    try {
      await addCollaborator(collabId, collabReason)
      setCollabId('')
    } catch {
      // Handled in WorkspaceProvider
    } finally {
      setAddingCollab(false)
    }
  }

  return (
    <Card className="ax-stack">
      <div>
        <h2>{selectedTask.title}</h2>
        <p className="ax-hint">{selectedTask.description}</p>
        {selectedTask.required_skills && selectedTask.required_skills.length > 0 && (
          <p className="ax-hint" style={{ marginTop: 4 }}>
            <strong>Required skills:</strong> {selectedTask.required_skills.join(', ')}
          </p>
        )}
      </div>

      {actionError && (
        <div
          role="alert"
          style={{
            padding: '8px 12px',
            borderRadius: 6,
            background: 'var(--ax-danger-surface, rgba(239, 68, 68, 0.15))',
            color: 'var(--ax-danger-text, #f87171)',
            border: '1px solid var(--ax-danger-border, #dc2626)',
            fontSize: '0.875rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{actionError}</span>
          <button
            type="button"
            onClick={() => setActionError('')}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'inherit',
              cursor: 'pointer',
              fontWeight: 'bold',
              padding: '0 4px',
            }}
            title="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

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

      {/* Assignees & Collaborators Section */}
      <div className="ax-stack" style={{ gap: 8, paddingTop: 8, borderTop: '1px solid var(--ax-border, #333)' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>Assignees & Collaborators</h3>
        {collaborators.length === 0 ? (
          <p className="ax-hint">No team members currently assigned.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {collaborators.map((c) => {
              const empInfo = employees.find((e) => e.employee_id === c.employee_id)
              const isProjectTeam = c.employee_id.startsWith('TM')
              return (
                <div
                  key={c.employee_id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: 6,
                    background: 'var(--ax-surface-raised, rgba(255,255,255,0.05))',
                    border: '1px solid var(--ax-border, rgba(255,255,255,0.1))',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <strong>{c.employee_name}</strong>
                    {empInfo && <span className="ax-hint" style={{ fontSize: '0.85rem' }}>{empInfo.role}</span>}
                    <span className={cn('ax-badge', isProjectTeam ? 'ax-badge-accent' : 'ax-badge-neutral')}>
                      <i />
                      {isProjectTeam ? 'Project Team' : 'Planning Roster'}
                    </span>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={removingId === c.employee_id}
                    onClick={async () => {
                      setRemovingId(c.employee_id)
                      try {
                        await removeCollaborator(c.employee_id)
                      } catch {
                        // Handled
                      } finally {
                        setRemovingId(null)
                      }
                    }}
                    title="Remove collaborator"
                  >
                    {removingId === c.employee_id ? 'Removing…' : 'Remove'}
                  </Button>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Add Collaborator Form */}
      <form className="ax-stack" onSubmit={handleAddCollaborator} style={{ gap: 8 }}>
        <Select
          label="Add collaborator"
          value={collabId}
          onChange={(event) => setCollabId(event.target.value)}
          hint={
            selectedTask.required_skills?.length
              ? 'Qualified candidates match ≥ 50% of required skills'
              : undefined
          }
        >
          <option value="">Select team member to collaborate…</option>
          {availableForCollab.map((emp) => {
            const match = calculateSkillMatch(emp.skills, selectedTask.required_skills || [])
            const isProjectTeam = emp.employee_id.startsWith('TM')
            return (
              <option key={emp.employee_id} value={emp.employee_id}>
                {emp.employee_name} · {emp.role} {isProjectTeam ? '★ Project Team' : ''} ({match.percent}% skills{match.qualifies ? ' - Qualified' : ''})
              </option>
            )
          })}
        </Select>
        <Input
          label="Collaboration reason"
          value={collabReason}
          onChange={(event) => setCollabReason(event.target.value)}
          placeholder="Reason for adding collaborator"
        />
        <div>
          <Button type="submit" variant="secondary" disabled={!collabId || addingCollab}>
            {addingCollab ? 'Adding…' : 'Add collaborator'}
          </Button>
        </div>
      </form>

      {/* Reassign Task Form */}
      <form className="ax-stack" onSubmit={saveReassign} style={{ gap: 8, paddingTop: 8, borderTop: '1px solid var(--ax-border, #333)' }}>
        <Select
          label="Reassign primary owner"
          value={reassignId}
          onChange={(event) => setReassignId(event.target.value)}
        >
          {employees.length === 0 && <option value="">No employees available</option>}
          {employees.map((employee) => {
            const match = calculateSkillMatch(employee.skills, selectedTask.required_skills || [])
            const isProjectTeam = employee.employee_id.startsWith('TM')
            const isCurrent = employee.employee_id === selectedTask.employee_id
            return (
              <option key={employee.employee_id} value={employee.employee_id}>
                {employee.employee_name} · {employee.role} {isProjectTeam ? '★ Project Team' : ''} ({match.percent}% skills{match.qualifies ? ' - Qualified' : ''}){isCurrent ? ' [Current Assignee]' : ''}
              </option>
            )
          })}
        </Select>
        <Input
          label="Reassignment reason"
          value={reassignReason}
          required
          onChange={(event) => setReassignReason(event.target.value)}
        />
        <div>
          <Button
            type="submit"
            variant="secondary"
            disabled={!reassignId || reassignId === selectedTask.employee_id}
          >
            Reassign task
          </Button>
        </div>
      </form>
    </Card>
  )
}

export function TeamPage() {
  const { projectId, project, employees, schedule, sessionName, tasks, reload } = useWorkspace()
  const toast = useToast()

  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([])
  const [loadingMembers, setLoadingMembers] = useState(false)
  const [membersError, setMembersError] = useState('')
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null)
  const [deletingMember, setDeletingMember] = useState<TeamMember | null>(null)
  const [showRoster, setShowRoster] = useState(false)

  useEffect(() => {
    if (projectId == null) return
    let cancelled = false

    async function load() {
      setLoadingMembers(true)
      setMembersError('')
      try {
        const res = await api.listTeamMembers(projectId!)
        if (!cancelled) {
          setTeamMembers(res.members)
        }
      } catch (err) {
        if (!cancelled) {
          setMembersError(errorMessage(err, 'Failed to load project team members'))
        }
      } finally {
        if (!cancelled) {
          setLoadingMembers(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [projectId])

  const displayMembers = projectId == null ? [] : teamMembers

  function handleMemberAdded(newMember: TeamMember) {
    setTeamMembers((prev) => [...prev, newMember])
    reload()
    toast({ title: `${newMember.name} added to project team`, tone: 'success' })
  }

  function handleMemberUpdated(updatedMember: TeamMember) {
    setTeamMembers((prev) =>
      prev.map((m) => (m.id === updatedMember.id ? updatedMember : m))
    )
    reload()
    toast({ title: `${updatedMember.name} updated`, tone: 'success' })
  }

  function handleMemberDeleted(deletedId: number) {
    setTeamMembers((prev) => prev.filter((m) => m.id !== deletedId))
    reload()
    toast({ title: 'Team member removed', tone: 'success' })
  }

  return (
    <div className="ax-stack">
      {/* 1. Project-scoped Team Members (System B) */}
      <Card className="ax-stack">
        <div className="ax-spread">
          <div>
            <span className="ax-kicker">Project Workspace</span>
            <h2 style={{ marginTop: 4 }}>Project Team</h2>
            <p className="ax-hint">
              {project?.name
                ? `Team members allocated to ${project.name}.`
                : 'Team members allocated specifically to this project.'}
            </p>
          </div>
          {projectId != null && (
            <Button onClick={() => setAddDialogOpen(true)}>
              <UserPlus size={16} /> Add Team Member
            </Button>
          )}
        </div>

        {membersError && (
          <Banner onDismiss={() => setMembersError('')}>
            {membersError}
          </Banner>
        )}

        {loadingMembers ? (
          <p className="ax-spinner">
            <span className="ax-spinner-dot" /> Loading project team members…
          </p>
        ) : displayMembers.length === 0 ? (
          <EmptyState
            title="No project team members"
            message={
              projectId != null
                ? 'No team members have been allocated to this project yet. Add employees or interns to begin tracking project staff.'
                : 'Select a project to manage its team members.'
            }
            action={
              projectId != null ? (
                <Button onClick={() => setAddDialogOpen(true)}>
                  <UserPlus size={16} /> Add Team Member
                </Button>
              ) : undefined
            }
          />
        ) : (
          <div className="ax-card-grid" style={{ marginTop: 8 }}>
            {displayMembers.map((member) => {
              const memberTasks = schedule.filter(
                (s) =>
                  s.employee_name.toLowerCase() === member.name.toLowerCase() ||
                  s.employee_id === `TM${member.id}` ||
                  s.employee_id === String(member.id),
              )
              const totalHours = memberTasks.reduce((sum, t) => sum + t.total_estimated_hours, 0)
              return (
                <Card
                  key={member.id}
                  className="ax-stack"
                  style={{ background: 'var(--ax-surface-raised)' }}
                >
                  <div className="ax-spread">
                    <div>
                      <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>
                        {member.name}
                      </h3>
                      <p className="ax-hint" style={{ marginTop: 2 }}>
                        {member.role}
                        {member.allocation_days != null
                          ? ` · ${member.allocation_days} days allocated`
                          : ''}
                        {memberTasks.length > 0
                          ? ` · ${memberTasks.length} ${memberTasks.length === 1 ? 'task' : 'tasks'} (${totalHours}h)`
                          : ' · No tasks assigned'}
                      </p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        className={cn(
                          'ax-badge',
                          member.member_type === 'intern'
                            ? 'ax-badge-warning'
                            : 'ax-badge-accent',
                        )}
                      >
                        <i />
                        {member.member_type === 'intern' ? 'Intern' : 'Employee'}
                      </span>
                      <button
                        type="button"
                        className="ax-btn ax-btn-ghost ax-btn-sm"
                        title="Edit member"
                        onClick={() => setEditingMember(member)}
                        style={{
                          padding: '4px 6px',
                          display: 'inline-flex',
                          alignItems: 'center',
                        }}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        type="button"
                        className="ax-btn ax-btn-ghost ax-btn-sm"
                        title="Remove member"
                        onClick={() => setDeletingMember(member)}
                        style={{
                          color: 'var(--ax-danger)',
                          padding: '4px 6px',
                          display: 'inline-flex',
                          alignItems: 'center',
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  {memberTasks.length > 0 && (
                    <ProgressBar
                      value={Math.min(100, Math.round((totalHours / (member.weekly_capacity_hours || 40)) * 100))}
                      label="Assigned load"
                    />
                  )}

                  {member.skills && member.skills.length > 0 && (
                    <div
                      style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '4px',
                        marginTop: 4,
                      }}
                    >
                      {member.skills.map((skill) => (
                        <span className="ax-skill" key={skill} style={{ margin: 0 }}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              )
            })}
          </div>
        )}
      </Card>

      {/* 2. Planning Roster Section (System A - Global) */}
      <Card className="ax-stack">
        <div className="ax-spread">
          <div>
            <span className="ax-kicker">AI Scheduling</span>
            <h2 style={{ marginTop: 4 }}>Planning Roster</h2>
            <p className="ax-hint">
              Global employee pool used by AI planning and work scheduler ({employees.length} available).
            </p>
          </div>
          <Button variant="ghost" onClick={() => setShowRoster((v) => !v)}>
            {showRoster ? (
              <>
                <ChevronDown size={16} /> Hide roster
              </>
            ) : (
              <>
                <ChevronRight size={16} /> Show roster
              </>
            )}
          </Button>
        </div>

        {showRoster && (
          <div style={{ marginTop: 8 }}>
            {employees.length === 0 ? (
              <EmptyState
                title="No employees returned"
                message="The scheduler roster from /api/employees is empty."
              />
            ) : (
              <div className="ax-card-grid">
                {employees.map((employee) => (
                  <Card
                    key={employee.employee_id}
                    className="ax-stack"
                    style={{ background: 'var(--ax-surface-raised)' }}
                  >
                    <div>
                      <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
                        {employee.employee_name}
                      </h3>
                      <p className="ax-hint">
                        {employee.role} · {employee.experience} years ·{' '}
                        {employee.weekly_capacity_hours}h / week
                      </p>
                    </div>
                    <ProgressBar
                      value={employee.current_workload_percent}
                      label="Workload"
                    />
                    <div>
                      {employee.skills.map((skill) => (
                        <span className="ax-skill" key={skill}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      {/* 3. Work schedule (Session-based) */}
      <Card>
        <h2>Work schedule</h2>
        <p className="ax-hint">
          {sessionName
            ? `Allocated weeks for session ${sessionName}.`
            : 'A session is required before this project has a schedule.'}
        </p>
        {schedule.length === 0 ? (
          <p className="ax-hint">No scheduled tasks were returned.</p>
        ) : (
          <DataTable>
            <thead>
              <tr>
                <Th>Task</Th>
                <Th>Owner</Th>
                <Th>Hours</Th>
                <Th>Weeks</Th>
              </tr>
            </thead>
            <tbody>
              {schedule.map((item) => (
                <Tr key={`${item.task_id}-${item.employee_id}`}>
                  <Td>{item.task_title}</Td>
                  <Td>{item.employee_name}</Td>
                  <Td>{item.total_estimated_hours}</Td>
                  <Td>
                    W{item.start_week}–W{item.completion_week}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </Card>

      {/* Dialogs */}
      {projectId != null && (
        <AddTeamMemberDialog
          open={addDialogOpen}
          projectId={projectId}
          tasks={tasks}
          sessionName={sessionName}
          onClose={() => setAddDialogOpen(false)}
          onAdded={handleMemberAdded}
        />
      )}

      {projectId != null && editingMember != null && (
        <EditTeamMemberDialog
          member={editingMember}
          projectId={projectId}
          tasks={tasks}
          sessionName={sessionName}
          onClose={() => setEditingMember(null)}
          onUpdated={handleMemberUpdated}
        />
      )}

      {projectId != null && deletingMember != null && (
        <DeleteTeamMemberDialog
          member={deletingMember}
          projectId={projectId}
          onClose={() => setDeletingMember(null)}
          onDeleted={handleMemberDeleted}
        />
      )}
    </div>
  )
}

export function TimelinePage() {
  const { overview, schedule, sessionName, employees } = useWorkspace()
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
      <Card>
        <h2>Team allocations & commitments</h2>
        <p className="ax-hint">Task assignments and planned commitments across project members.</p>
        {employees.length === 0 ? (
          <p className="ax-hint">No team members available for this project.</p>
        ) : (
          <DataTable>
            <thead><tr><Th>Member</Th><Th>Role</Th><Th>Team</Th><Th>Tasks</Th><Th>Total hours</Th><Th>Weeks</Th></tr></thead>
            <tbody>
              {employees.map((emp) => {
                const empTasks = schedule.filter(
                  (s) =>
                    s.employee_id === emp.employee_id ||
                    s.employee_name.toLowerCase() === emp.employee_name.toLowerCase(),
                )
                const hours = empTasks.reduce((acc, t) => acc + t.total_estimated_hours, 0)
                const startWeeks = empTasks.map((t) => t.start_week)
                const endWeeks = empTasks.map((t) => t.completion_week)
                const weekRange = empTasks.length > 0
                  ? `W${Math.min(...startWeeks)}–W${Math.max(...endWeeks)}`
                  : '—'
                const isProjectTeam = emp.employee_id.startsWith('TM')
                return (
                  <Tr key={emp.employee_id}>
                    <Td><strong>{emp.employee_name}</strong></Td>
                    <Td>{emp.role}</Td>
                    <Td>
                      <span className={cn('ax-badge', isProjectTeam ? 'ax-badge-accent' : 'ax-badge-neutral')}>
                        <i />
                        {isProjectTeam ? 'Project Team' : 'Planning Roster'}
                      </span>
                    </Td>
                    <Td>{empTasks.length > 0 ? `${empTasks.length} assigned` : 'Unassigned'}</Td>
                    <Td>{hours > 0 ? `${hours}h` : '0h'}</Td>
                    <Td>{weekRange}</Td>
                  </Tr>
                )
              })}
            </tbody>
          </DataTable>
        )}
      </Card>
    </div>
  )
}

export function ReportsPage() {
  const { report, sessionName, employees, schedule } = useWorkspace()
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
        <h2>Team allocation</h2>
        <p className="ax-hint">{employees.length} team members available on this project</p>
        <ul className="ax-list">
          {employees.map((emp) => {
            const empTasks = schedule.filter(
              (s) =>
                s.employee_id === emp.employee_id ||
                s.employee_name.toLowerCase() === emp.employee_name.toLowerCase(),
            )
            const hours = empTasks.reduce((acc, t) => acc + t.total_estimated_hours, 0)
            const isProjectTeam = emp.employee_id.startsWith('TM')
            return (
              <li key={emp.employee_id}>
                <strong>{emp.employee_name}</strong> ({emp.role} · {isProjectTeam ? 'Project Team' : 'Planning Roster'}):{' '}
                {empTasks.length > 0 ? `${empTasks.length} tasks (${hours}h)` : 'Available (unassigned)'}
              </li>
            )
          })}
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
  const { sessionName, chat, question, asking, setQuestion, submitQuestion, clearChat } = useWorkspace()
  if (!sessionName) return <NoSession detail="The assistant answers from a live session and does not change saved project state." />
  return (
    <Card className="ax-stack">
      <div className="flex items-center justify-between">
        <div>
          <strong className="text-base font-semibold text-[var(--ax-ink)]">AI Project Assistant</strong>
          <p className="ax-hint">Answers use session {sessionName} and do not change saved project state.</p>
        </div>
        {chat.length > 0 && (
          <Button variant="ghost" onClick={clearChat} className="text-xs text-[var(--ax-muted)] hover:text-[var(--ax-danger)]">
            Clear conversation
          </Button>
        )}
      </div>

      {chat.length === 0 ? (
        <div className="ax-assistant-empty-state my-4">
          <p className="text-xs text-[var(--ax-muted)] mb-2.5">Suggested questions to get started:</p>
          <div className="flex flex-wrap gap-2">
            {prompts.map((text) => (
              <button
                key={text}
                type="button"
                className="ax-suggest-btn"
                onClick={() => setQuestion(text)}
              >
                <span>{text}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="ax-chat-messages-container my-2" style={{ maxHeight: '520px' }}>
          {chat.map((turn, index) => (
            <div
              key={`${turn.role}-${index}`}
              className={turn.role === 'user' ? 'ax-message-row-user' : 'ax-message-row-bot'}
            >
              {turn.role === 'bot' && (
                <div className="ax-message-avatar">
                  <Bot size={15} />
                </div>
              )}
              <div className={turn.role === 'user' ? 'ax-message-bubble-user' : 'ax-message-bubble-bot'}>
                {turn.role === 'bot' ? (
                  <MarkdownRenderer content={turn.text} />
                ) : (
                  <div className="whitespace-pre-wrap text-xs leading-relaxed">{turn.text}</div>
                )}
              </div>
            </div>
          ))}
          {asking && (
            <div className="ax-message-row-bot">
              <div className="ax-message-avatar animate-pulse">
                <Bot size={15} />
              </div>
              <div className="ax-message-bubble-bot flex items-center gap-2 py-3 px-4">
                <span className="ax-thinking-dot" />
                <span className="text-xs text-[var(--ax-muted)] italic">Thinking with live project context…</span>
              </div>
            </div>
          )}
        </div>
      )}

      {chat.length > 0 && (
        <div className="ax-quick-prompts-bar">
          {prompts.map((text) => (
            <button
              key={text}
              type="button"
              className="ax-quick-chip"
              onClick={() => setQuestion(text)}
              disabled={asking}
            >
              {text}
            </button>
          ))}
        </div>
      )}

      <ChatInput
        value={question}
        onChange={setQuestion}
        onSubmit={submitQuestion}
        disabled={!sessionName}
        loading={asking}
        placeholder="Ask about this session…"
      />
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
