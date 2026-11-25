import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { FolderPlus, Pencil, RefreshCw, Trash2 } from 'lucide-react'
import { api, type Overview, type ProjectListItem, type SessionSummary } from '../api'
import { buildProjectCards, sessionsToSummarize, type CatalogStatus, type ProjectCardModel } from '../lib/project-catalog'
import { errorMessage, formatDate, timestamp } from '../lib/format'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Dialog } from '../components/ui/Dialog'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { Input, TextArea } from '../components/ui/Input'
import { ProgressBar } from '../components/ui/ProgressBar'
import { Select } from '../components/ui/Select'
import { CardSkeletonGrid } from '../components/ui/Skeleton'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Tabs } from '../components/ui/Tabs'
import { useToast } from '../components/ui/useToast'
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
  const toast = useToast()
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [overviews, setOverviews] = useState<Record<string, Overview>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<StatusFilter>('all')
  const [sort, setSort] = useState<SortKey>('updated')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingCard, setEditingCard] = useState<ProjectCardModel | null>(null)
  const [deletingCard, setDeletingCard] = useState<ProjectCardModel | null>(null)
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
          message="Get started by creating your first project, or run a planning job in the Planning Studio."
          action={<Button onClick={() => setDialogOpen(true)}><FolderPlus size={16} /> New project</Button>}
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
            {visible.map((card) => (
              <ProjectCard
                key={card.key}
                card={card}
                onEdit={setEditingCard}
                onDelete={setDeletingCard}
              />
            ))}
          </div>
        </>
      )}
      <NewProjectDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={() => {
          setReloadKey((v) => v + 1)
          toast({ title: 'Project created', tone: 'success' })
        }}
      />
      {editingCard && (
        <EditProjectDialog
          key={editingCard.key}
          card={editingCard}
          onClose={() => setEditingCard(null)}
          onSaved={() => {
            setReloadKey((v) => v + 1)
            toast({ title: 'Project updated', tone: 'success' })
          }}
        />
      )}
      {deletingCard && (
        <DeleteProjectDialog
          key={deletingCard.key}
          card={deletingCard}
          onClose={() => setDeletingCard(null)}
          onDeleted={() => {
            setReloadKey((v) => v + 1)
            toast({ title: 'Project deleted', tone: 'success' })
          }}
        />
      )}
    </>
  )
}

function ProjectCard({
  card,
  onEdit,
  onDelete,
}: {
  card: ProjectCardModel
  onEdit: (card: ProjectCardModel) => void
  onDelete: (card: ProjectCardModel) => void
}) {
  return (
    <Card hover className="ax-stack">
      <div className="ax-card-top">
        <h2>{card.name}</h2>
        <StatusBadge label={card.statusLabel} />
      </div>
      {(card.description || card.summary) && (
        <p className="ax-meta" style={{ margin: 0, color: 'var(--ax-muted)' }}>
          {card.description || card.summary}
        </p>
      )}
      {card.progress == null ? (
        <p className="ax-hint">Progress is unavailable until this project has a management session.</p>
      ) : (
        <ProgressBar value={card.progress} />
      )}
      <div className="ax-meta">
        <span>Created {formatDate(card.createdAt)}</span>
        {card.updatedAt !== card.createdAt && (
          <span> · Updated {formatDate(card.updatedAt)}</span>
        )}
      </div>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: 'auto', flexWrap: 'wrap' }}>
        <Link to={card.href} className="ax-btn ax-btn-primary ax-btn-sm">
          Open project
        </Link>
        {card.projectId != null && (
          <>
            <Button variant="secondary" size="sm" onClick={() => onEdit(card)}>
              <Pencil size={14} /> Edit
            </Button>
            <Button variant="danger" size="sm" onClick={() => onDelete(card)}>
              <Trash2 size={14} /> Delete
            </Button>
          </>
        )}
      </div>
    </Card>
  )
}

function EditProjectDialog({
  card,
  onClose,
  onSaved,
}: {
  card: ProjectCardModel
  onClose: () => void
  onSaved: () => void
}) {
  const [name, setName] = useState(card.name)
  const [description, setDescription] = useState(card.description || card.summary || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (card.projectId == null) return null

  async function submit(event: FormEvent) {
    event.preventDefault()
    const trimmedName = name.trim()
    if (!trimmedName) {
      setError('Project name is required')
      return
    }
    if (loading || card.projectId == null) return

    setLoading(true)
    setError('')
    try {
      await api.updateProject(card.projectId, {
        name: trimmedName,
        description: description.trim(),
      })
      onSaved()
      onClose()
    } catch (err) {
      setError(errorMessage(err, 'Failed to update project'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open
      title="Edit project"
      description="Update the project name or description."
      onClose={onClose}
      closeDisabled={loading}
    >
      <form className="ax-stack" onSubmit={submit}>
        <Input
          label="Project name"
          value={name}
          required
          maxLength={120}
          disabled={loading}
          onChange={(e) => {
            setName(e.target.value)
            if (error) setError('')
          }}
        />
        <TextArea
          label="Description"
          value={description}
          rows={3}
          maxLength={2000}
          disabled={loading}
          placeholder="Brief overview of project goals"
          onChange={(e) => setDescription(e.target.value)}
        />
        {error && <Banner onDismiss={() => setError('')}>{error}</Banner>}
        <div className="ax-dialog-actions">
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading || !name.trim()}>
            {loading ? 'Saving...' : 'Save changes'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

function DeleteProjectDialog({
  card,
  onClose,
  onDeleted,
}: {
  card: ProjectCardModel
  onClose: () => void
  onDeleted: () => void
}) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (card.projectId == null) return null

  async function handleDelete() {
    if (loading || card.projectId == null) return
    setLoading(true)
    setError('')
    try {
      await api.deleteProject(card.projectId)
      onDeleted()
      onClose()
    } catch (err) {
      setError(errorMessage(err, 'Failed to delete project'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open
      title="Delete project"
      description={`Are you sure you want to delete "${card.name}"? This action cannot be undone.`}
      onClose={onClose}
      closeDisabled={loading}
    >
      <div className="ax-stack">
        {error && <Banner onDismiss={() => setError('')}>{error}</Banner>}
        <div className="ax-dialog-actions">
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete} disabled={loading}>
            {loading ? 'Deleting...' : 'Delete project'}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
