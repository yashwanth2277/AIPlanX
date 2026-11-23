import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { FolderPlus, RefreshCw } from 'lucide-react'
import { api, type Overview, type ProjectListItem, type SessionSummary } from '../api'
import { buildProjectCards, sessionsToSummarize, type CatalogStatus, type ProjectCardModel } from '../lib/project-catalog'
import { errorMessage, formatDate, timestamp } from '../lib/format'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { Input } from '../components/ui/Input'
import { ProgressBar } from '../components/ui/ProgressBar'
import { Select } from '../components/ui/Select'
import { CardSkeletonGrid } from '../components/ui/Skeleton'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Tabs } from '../components/ui/Tabs'
import { NewProjectDialog } from './NewProjectDialog'

type StatusFilter = 'all' | CatalogStatus
type SortKey = 'updated' | 'newest' | 'oldest' | 'name'

const filters: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All Projects' },
  { value: 'active', label: 'Active' },
  { value: 'planning', label: 'Planning' },
  { value: 'completed', label: 'Completed' },
  { value: 'on_hold', label: 'On Hold' },
]

export function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [overviews, setOverviews] = useState<Record<string, Overview>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<StatusFilter>('all')
  const [sort, setSort] = useState<SortKey>('updated')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const [projectPayload, sessionPayload] = await Promise.all([api.projects(), api.sessions()])
        if (cancelled) return
        const names = sessionsToSummarize(projectPayload.projects, sessionPayload.sessions)
        const nextOverviews: Record<string, Overview> = {}
        await Promise.all(names.map(async (name) => {
          try {
            nextOverviews[name] = await api.overview(name)
          } catch {
            /* A missing overview still leaves the saved project visible. */
          }
        }))
        if (cancelled) return
        setProjects(projectPayload.projects)
        setSessions(sessionPayload.sessions)
        setOverviews(nextOverviews)
      } catch (err) {
        if (!cancelled) setError(errorMessage(err, 'Could not load projects'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  const cards = useMemo(
    () => buildProjectCards(projects, sessions, overviews),
    [projects, sessions, overviews],
  )

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase()
    const filtered = cards.filter((card) => {
      if (status !== 'all' && card.status !== status) return false
      if (!query) return true
      return card.name.toLowerCase().includes(query)
    })
    return filtered.sort((left, right) => {
      if (sort === 'name') return left.name.localeCompare(right.name)
      if (sort === 'newest') return timestamp(right.createdAt) - timestamp(left.createdAt)
      if (sort === 'oldest') return timestamp(left.createdAt) - timestamp(right.createdAt)
      return timestamp(right.updatedAt) - timestamp(left.updatedAt)
    })
  }, [cards, search, status, sort])

  return (
    <>
      <div className="ax-toolbar">
        <div className="ax-grow">
          <Input
            label="Search"
            value={search}
            placeholder="Search by project name"
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <Select label="Sort" value={sort} onChange={(event) => setSort(event.target.value as SortKey)}>
          <option value="updated">Recently Updated</option>
          <option value="newest">Newest First</option>
          <option value="oldest">Oldest First</option>
          <option value="name">Name A–Z</option>
        </Select>
        <Button variant="secondary" onClick={() => setReloadKey((value) => value + 1)} disabled={loading}>
          <RefreshCw size={16} /> Refresh
        </Button>
        <Button onClick={() => setDialogOpen(true)}>
          <FolderPlus size={16} /> New project
        </Button>
      </div>
      <Tabs label="Project status" value={status} onChange={setStatus} options={filters} />
      {loading && <CardSkeletonGrid />}
      {!loading && error && <ErrorState message={error} onRetry={() => setReloadKey((value) => value + 1)} />}
      {!loading && !error && cards.length === 0 && (
        <EmptyState
          title="No projects yet"
          message="Saved plans will appear here after a planning job stores a project. Name-only project creation is not available from the API."
          action={<Button onClick={() => setDialogOpen(true)}>New project</Button>}
        />
      )}
      {!loading && !error && cards.length > 0 && visible.length === 0 && (
        <EmptyState
          title="No matching projects"
          message="Nothing matches this name, status, and sort together. Clear the search or choose All Projects."
          action={<Button variant="secondary" onClick={() => { setSearch(''); setStatus('all') }}>Clear filters</Button>}
        />
      )}
      {!loading && !error && visible.length > 0 && (
        <>
          <p className="ax-count">{visible.length} {visible.length === 1 ? 'project' : 'projects'}</p>
          <div className="ax-card-grid">
            {visible.map((card) => <ProjectCard key={card.key} card={card} />)}
          </div>
        </>
      )}
      <NewProjectDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </>
  )
}

function ProjectCard({ card }: { card: ProjectCardModel }) {
  return (
    <Card hover className="ax-stack">
      <div className="ax-card-top">
        <h2>{card.name}</h2>
        <StatusBadge label={card.statusLabel} />
      </div>
      {card.progress == null ? (
        <p className="ax-hint">Progress is unavailable until this project has a management session.</p>
      ) : (
        <ProgressBar value={card.progress} />
      )}
      <p className="ax-meta">Updated {formatDate(card.updatedAt)}</p>
      <Link to={card.href} className="ax-btn ax-btn-primary ax-btn-sm">Open project</Link>
    </Card>
  )
}
