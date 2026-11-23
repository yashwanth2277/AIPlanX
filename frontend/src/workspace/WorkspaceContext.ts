import { createContext, type FormEvent } from 'react'
import type {
  Employee,
  ManagementReportPayload,
  Overview,
  PlanJob,
  ProjectListItem,
  ScheduledTask,
  SessionSummary,
  TaskRow,
} from '../api'

type ChatTurn = { role: 'user' | 'bot'; text: string }

export type WorkspaceContextValue = {
  projectId: number | null
  project: ProjectListItem | null
  sessionName: string
  sessions: SessionSummary[]
  overview: Overview | null
  tasks: TaskRow[]
  employees: Employee[]
  schedule: ScheduledTask[]
  report: ManagementReportPayload | null
  planDescription: string
  planSessionName: string
  planJob: PlanJob | null
  planning: boolean
  chat: ChatTurn[]
  question: string
  asking: boolean
  assistantOpen: boolean
  selectedTask: TaskRow | null
  progressPercent: number
  taskStatus: string
  actualHours: string
  delayHours: string
  delayReason: string
  delayWeeks: string
  reassignId: string
  reassignReason: string
  setPlanDescription: (value: string) => void
  setPlanSessionName: (value: string) => void
  setQuestion: (value: string) => void
  setAssistantOpen: (open: boolean) => void
  selectTask: (task: TaskRow) => void
  setProgressPercent: (value: number) => void
  setTaskStatus: (value: string) => void
  setActualHours: (value: string) => void
  setDelayHours: (value: string) => void
  setDelayReason: (value: string) => void
  setDelayWeeks: (value: string) => void
  setReassignId: (value: string) => void
  setReassignReason: (value: string) => void
  switchSession: (name: string) => void
  reload: () => void
  startPlan: (event: FormEvent) => void
  submitQuestion: (event?: FormEvent) => void
  saveProgress: (event: FormEvent) => void
  saveDelay: (event: FormEvent) => void
  runDelayAnalysis: (event: FormEvent) => void
  saveReassign: (event: FormEvent) => void
}

export const WorkspaceContext = createContext<WorkspaceContextValue | null>(null)
