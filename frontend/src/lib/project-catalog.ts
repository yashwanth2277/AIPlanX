import type { Overview, ProjectListItem, SessionSummary } from '../api'
import { timestamp } from './format'

export type CatalogStatus = 'active' | 'planning' | 'completed' | 'on_hold'

export type ProjectCardModel = {
  key: string
  projectId: number | null
  sessionName: string | null
  name: string
  summary: string
  description: string
  createdAt: string
  updatedAt: string
  hasReport: boolean
  sessionCount: number
  taskCount: number | null
  progress: number | null
  status: CatalogStatus
  statusLabel: string
  href: string
}

type SessionGroups = {
  linked: Map<number, SessionSummary[]>
  unlinked: Map<number, SessionSummary[]>
  orphans: SessionSummary[]
}

function byUpdatedDesc(left: SessionSummary, right: SessionSummary): number {
  return timestamp(right.updated_at) - timestamp(left.updated_at)
}

function groupSessions(projects: ProjectListItem[], sessions: SessionSummary[]): SessionGroups {
  const ids = new Set(projects.map((project) => project.id))
  const linked = new Map<number, SessionSummary[]>()
  const unlinked = new Map<number, SessionSummary[]>()
  const orphans: SessionSummary[] = []

  for (const session of sessions) {
    if (session.project_id == null) {
      orphans.push(session)
      continue
    }
    const target = ids.has(session.project_id) ? linked : unlinked
    const list = target.get(session.project_id) ?? []
    list.push(session)
    target.set(session.project_id, list)
  }

  for (const list of linked.values()) list.sort(byUpdatedDesc)
  for (const list of unlinked.values()) list.sort(byUpdatedDesc)
  orphans.sort(byUpdatedDesc)
  return { linked, unlinked, orphans }
}

export function sessionsToSummarize(projects: ProjectListItem[], sessions: SessionSummary[]): string[] {
  const { linked, unlinked, orphans } = groupSessions(projects, sessions)
  const names = [
    ...[...linked.values()].map((list) => list[0].name),
    ...[...unlinked.values()].map((list) => list[0].name),
    ...orphans.map((session) => session.name),
  ]
  return [...new Set(names)]
}

function deriveStatus(hasSession: boolean, overview?: Overview): { status: CatalogStatus; label: string } {
  if (!hasSession || !overview) {
    return { status: hasSession ? 'active' : 'planning', label: hasSession ? 'Active' : 'Planning' }
  }
  const { progress, project } = overview
  if (progress.total_tasks > 0 && progress.completed === progress.total_tasks) {
    return { status: 'completed', label: 'Completed' }
  }
  if (project.status_label === 'Needs attention' || project.status_label === 'Delayed') {
    return { status: 'on_hold', label: project.status_label }
  }
  return { status: 'active', label: project.status_label }
}

function cardFromSessions(
  key: string,
  sessions: SessionSummary[],
  project: ProjectListItem | null,
  overviews: Record<string, Overview>,
): ProjectCardModel {
  const primary = sessions[0]
  const overview = overviews[primary.name]
  const derived = deriveStatus(true, overview)
  return {
    key,
    projectId: project?.id ?? primary.project_id,
    sessionName: primary.name,
    name: project?.name || primary.project_name || primary.name,
    summary: project?.summary || overview?.project.summary || '',
    description: project?.description || '',
    createdAt: project?.created_at || primary.updated_at,
    updatedAt: project?.updated_at || primary.updated_at,
    hasReport: project?.has_report ?? false,
    sessionCount: sessions.length,
    taskCount: primary.task_count,
    progress: overview ? overview.progress.overall_percent : null,
    status: derived.status,
    statusLabel: derived.label,
    href: project
      ? `/projects/${project.id}/overview`
      : `/sessions/${encodeURIComponent(primary.name)}/overview`,
  }
}

export function buildProjectCards(
  projects: ProjectListItem[],
  sessions: SessionSummary[],
  overviews: Record<string, Overview>,
): ProjectCardModel[] {
  const { linked, unlinked, orphans } = groupSessions(projects, sessions)
  const cards = projects.map((project) => {
    const group = linked.get(project.id) ?? []
    if (group.length === 0) {
      return {
        key: `project-${project.id}`,
        projectId: project.id,
        sessionName: null,
        name: project.name || `Project ${project.id}`,
        summary: project.summary,
        description: project.description || '',
        createdAt: project.created_at,
        updatedAt: project.updated_at || project.created_at,
        hasReport: project.has_report,
        sessionCount: 0,
        taskCount: null,
        progress: null,
        status: 'planning' as const,
        statusLabel: 'Planning',
        href: `/projects/${project.id}/overview`,
      }
    }
    return cardFromSessions(`project-${project.id}`, group, project, overviews)
  })

  for (const [projectId, group] of unlinked) {
    cards.push(cardFromSessions(`unlinked-${projectId}`, group, null, overviews))
  }
  for (const session of orphans) {
    cards.push(cardFromSessions(`session-${session.name}`, [session], null, overviews))
  }
  return cards
}
