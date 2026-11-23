import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { NotFoundPage, NotificationsPage, ProfilePage, SettingsPage, TeamDirectoryPage } from './pages/GlobalPages'
import { ProjectsPage } from './pages/ProjectsPage'
import { WorkspaceProvider } from './workspace/WorkspaceProvider'
import {
  ActivityPage,
  AssistantPage,
  OverviewPage,
  ReportsPage,
  StudioPage,
  TasksPage,
  TeamPage,
  TimelinePage,
} from './workspace/pages'

function WorkspaceRoutes() {
  return (
    <>
      <Route index element={<Navigate to="overview" replace />} />
      <Route path="overview" element={<OverviewPage />} />
      <Route path="studio" element={<StudioPage />} />
      <Route path="team" element={<TeamPage />} />
      <Route path="tasks" element={<TasksPage />} />
      <Route path="timeline" element={<TimelinePage />} />
      <Route path="reports" element={<ReportsPage />} />
      <Route path="assistant" element={<AssistantPage />} />
      <Route path="activity" element={<ActivityPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/projects" replace />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:projectId" element={<WorkspaceProvider />}>
          {WorkspaceRoutes()}
        </Route>
        <Route path="sessions/:sessionName" element={<WorkspaceProvider />}>
          {WorkspaceRoutes()}
        </Route>
        <Route path="team" element={<TeamDirectoryPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
