import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Employee } from '../api'
import { errorMessage } from '../lib/format'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { ProgressBar } from '../components/ui/ProgressBar'
import { CardSkeletonGrid } from '../components/ui/Skeleton'
import { ThemePreference } from '../theme/ThemePreference'

export function TeamDirectoryPage() {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const payload = await api.employees()
        if (!cancelled) setEmployees(payload.employees)
      } catch (err) {
        if (!cancelled) setError(errorMessage(err, 'Could not load the team roster'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  if (loading) return <CardSkeletonGrid />
  if (error) return <ErrorState message={error} onRetry={() => setReloadKey((value) => value + 1)} />
  if (employees.length === 0) {
    return (
      <EmptyState
        title="No people on the roster"
        message="The planning engine did not return any employees. This page only shows people the scheduler can assign."
      />
    )
  }

  return (
    <div className="ax-card-grid">
      {employees.map((employee) => (
        <Card key={employee.employee_id} className="ax-stack">
          <div>
            <h2>{employee.employee_name}</h2>
            <p className="ax-hint">{employee.role} · {employee.experience} years · {employee.weekly_capacity_hours}h / week</p>
          </div>
          <ProgressBar value={employee.current_workload_percent} label="Workload" />
          <div>
            {employee.skills.map((skill) => <span className="ax-skill" key={skill}>{skill}</span>)}
          </div>
        </Card>
      ))}
    </div>
  )
}

export function NotificationsPage() {
  return (
    <EmptyState
      title="No notification service"
      message="AIPlanX does not have a notifications API. Alerts are not stored for this browser, so this inbox stays empty until that service exists."
    />
  )
}

export function SettingsPage() {
  const [health, setHealth] = useState('Checking…')

  useEffect(() => {
    let cancelled = false
    api.health()
      .then((payload) => {
        if (!cancelled) setHealth(payload.store ? `${payload.status} · store ${payload.store}` : payload.status)
      })
      .catch((err: unknown) => {
        if (!cancelled) setHealth(errorMessage(err, 'API unreachable'))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="ax-split">
      <Card>
        <ThemePreference />
      </Card>
      <Card className="ax-stack">
        <h2>API connection</h2>
        <p className="ax-hint">Live status from `GET /api/health`. Theme choice is stored in this browser only.</p>
        <p>{health}</p>
      </Card>
    </div>
  )
}

export function ProfilePage() {
  return (
    <EmptyState
      title="No signed-in profile"
      message="This workspace does not have accounts, sign-in, or a profile API. There is no user record to show."
      action={<Link to="/settings" className="ax-btn ax-btn-secondary">Open settings</Link>}
    />
  )
}

export function NotFoundPage() {
  return (
    <EmptyState
      title="Page not found"
      message="That address is not part of AIPlanX."
      action={<Link to="/projects" className="ax-btn ax-btn-primary">Back to projects</Link>}
    />
  )
}
