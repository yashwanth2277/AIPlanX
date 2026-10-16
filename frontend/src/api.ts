const API = ''

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API}${path}`, { ...options, headers })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(formatDetail(data.detail) || response.statusText)
  }
  return data as T
}

function formatDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)))
      .join('; ')
  }
  return ''
}

export type SessionSummary = {
  name: string
  project_id: number | null
  project_name: string
  task_count: number
  updated_at: string
}

export type Overview = {
  session_name: string
  project: {
    name: string
    summary: string
    total_estimated_hours: number
    status_label: string
    risks: string[]
  }
  progress: {
    overall_percent: number
    total_tasks: number
    completed: number
    in_progress: number
    pending: number
    blocked: number
    at_risk: number
  }
  health: {
    score: number
    label: string
    schedule: number
    delivery: number
    resources: number
  }
  chart: { week: string; planned: number; actual: number }[]
  priority_tasks: {
    id: string
    task_id: number
    title: string
    owner: string
    initials: string
    color: string
    status: string
    progress: number
    due: string
    priority: string
  }[]
  activities: { title: string; detail: string; time: string; color: string }[]
  team_size: number
  completion_week: number | null
}

export type TaskRow = {
  task_id: number
  title: string
  description: string
  required_skills: string[]
  estimated_hours: number
  priority: string
  dependencies: number[]
  status: string
  status_label: string
  progress_percent: number
  actual_hours_spent: number
  owner: string
  employee_id: string | null
  initials: string
  color: string
  start_week: number | null
  completion_week: number | null
  due: string
  delays: { delay_hours: number; reason: string }[]
}

export type Employee = {
  employee_id: string
  employee_name: string
  role: string
  skills: string[]
  experience: number
  current_workload_percent: number
  weekly_capacity_hours: number
}

export type ScheduledTask = {
  task_id: number
  task_title: string
  employee_id: string
  employee_name: string
  total_estimated_hours: number
  start_week: number
  completion_week: number
  weekly_allocations: { week: number; allocated_hours: number }[]
}

export type ManagementReportPayload = {
  management_report: {
    project_name: string
    progress: {
      total_tasks: number
      pending_tasks: number
      in_progress_tasks: number
      blocked_tasks: number
      completed_tasks: number
    }
    task_delays: { task_id: number; task_title: string; delay_hours: number; reason: string }[]
    revised_completion_week: number | null
    recommendations: string[]
  }
  insights: {
    unavailable?: boolean
    reason?: string
    executive_summary?: string
    delay_explanations?: string[]
    identified_risks?: string[]
    recovery_recommendations?: string[]
  } | null
  planning_report: {
    risk_analysis?: { overall_risk_level: string; risks: { title: string; severity: string; mitigation: string }[] }
    recommendations?: { summary: string; recommendations: { title: string; description: string; priority: string }[] }
    schedule?: { total_duration_days: number; critical_path: number[] }
  } | null
}

export type PlanJob = {
  id: string
  status: string
  error: string | null
  project_id: number | null
  session_name: string | null
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  sessions: () => request<{ sessions: SessionSummary[] }>('/api/sessions'),
  overview: (name: string) => request<Overview>(`/api/sessions/${name}/overview`),
  tasks: (name: string) => request<{ tasks: TaskRow[] }>(`/api/sessions/${name}/tasks`),
  schedule: (name: string) => request<{ scheduled_tasks: ScheduledTask[]; unscheduled_tasks: unknown[] }>(`/api/sessions/${name}/schedule`),
  employees: () => request<{ employees: Employee[] }>('/api/employees'),
  report: (name: string) => request<ManagementReportPayload>(`/api/sessions/${name}/report`),
  updateProgress: (
    name: string,
    taskId: number,
    body: { status: string; progress_percent: number; actual_hours_spent?: number },
  ) =>
    request(`/api/sessions/${name}/tasks/${taskId}/progress`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  recordDelay: (name: string, taskId: number, body: { delay_hours: number; reason: string }) =>
    request(`/api/sessions/${name}/tasks/${taskId}/delays`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  analyzeDelay: (
    name: string,
    taskId: number,
    body: { delay_weeks: number; delay_hours?: number; delay_reason?: string },
  ) =>
    request(`/api/sessions/${name}/tasks/${taskId}/analyze-delay`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  reassign: (name: string, taskId: number, body: { employee_id: string; reason: string }) =>
    request(`/api/sessions/${name}/tasks/${taskId}/reassign`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  askAssistant: (sessionName: string, question: string) =>
    request<{ answer: string }>('/api/assistant/ask', {
      method: 'POST',
      body: JSON.stringify({ session_name: sessionName, question }),
    }),
  startPlan: (description: string, sessionName?: string) =>
    request<{ job_id: string; status: string }>('/api/projects/plan', {
      method: 'POST',
      body: JSON.stringify({
        description,
        session_name: sessionName || null,
        create_session: true,
      }),
    }),
  planJob: (jobId: string) => request<PlanJob>(`/api/projects/jobs/${jobId}`),
}
