import { useCallback, useMemo, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Plus, X } from 'lucide-react'
import { api, type TaskRow, type TeamMember } from '../api'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Dialog } from '../components/ui/Dialog'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { errorMessage } from '../lib/format'

type AddTeamMemberDialogProps = {
  open: boolean
  projectId: number
  onClose: () => void
  onAdded: (member: TeamMember) => void
  tasks?: TaskRow[]
  sessionName?: string
}

export function AddTeamMemberDialog({
  open,
  projectId,
  onClose,
  onAdded,
  tasks,
  sessionName,
}: AddTeamMemberDialogProps) {
  const [memberType, setMemberType] = useState<'employee' | 'intern'>('employee')
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [skills, setSkills] = useState<string[]>([])
  const [skillInput, setSkillInput] = useState('')
  const [allocationDays, setAllocationDays] = useState('30')
  const [selectedTaskIds, setSelectedTaskIds] = useState<number[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const reset = useCallback(() => {
    setName('')
    setRole('')
    setMemberType('employee')
    setSkills([])
    setSkillInput('')
    setAllocationDays('30')
    setSelectedTaskIds([])
    setError('')
  }, [])

  const close = useCallback(() => {
    if (loading) return
    reset()
    onClose()
  }, [loading, onClose, reset])

  function addSkillFromInput() {
    const trimmed = skillInput.trim().replace(/^,+|,+$/g, '')
    if (!trimmed) return
    const parts = trimmed
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean)

    const next = [...skills]
    for (const part of parts) {
      if (!next.includes(part)) {
        next.push(part)
      }
    }
    setSkills(next)
    setSkillInput('')
    if (error) setError('')
  }

  function handleSkillKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addSkillFromInput()
    } else if (e.key === 'Backspace' && !skillInput && skills.length > 0) {
      setSkills((prev) => prev.slice(0, -1))
    }
  }

  function removeSkill(skillToRemove: string) {
    setSkills((prev) => prev.filter((s) => s !== skillToRemove))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    const trimmedName = name.trim()
    const trimmedRole = role.trim()

    // Include any pending text in the skill input
    const currentSkills = [...skills]
    const pending = skillInput.trim().replace(/^,+|,+$/g, '')
    if (pending) {
      const parts = pending
        .split(',')
        .map((p) => p.trim())
        .filter(Boolean)
      for (const part of parts) {
        if (!currentSkills.includes(part)) {
          currentSkills.push(part)
        }
      }
    }

    if (!trimmedName) {
      setError('Member name is required')
      return
    }
    if (!trimmedRole) {
      setError('Member role is required')
      return
    }
    if (currentSkills.length === 0) {
      setError('At least one skill is required. Enter a skill and press Enter or Add.')
      return
    }

    const parsedDays = parseInt(allocationDays, 10)
    if (isNaN(parsedDays) || parsedDays <= 0) {
      setError('Allocation duration must be at least 1 day')
      return
    }

    if (loading) return
    setLoading(true)
    setError('')

    try {
      const member = await api.addTeamMember(projectId, {
        name: trimmedName,
        role: trimmedRole,
        member_type: memberType,
        skills: currentSkills,
        allocation_days: parsedDays,
      })

      // If tasks were selected and sessionName exists, assign them
      if (sessionName && selectedTaskIds.length > 0) {
        for (const taskId of selectedTaskIds) {
          try {
            await api.addCollaborator(sessionName, taskId, {
              employee_id: `TM${member.id}`,
              reason: 'Assigned during team member onboarding',
            })
          } catch (taskErr) {
            console.warn(`Could not assign task ${taskId} to member ${member.id}:`, taskErr)
          }
        }
      }

      reset()
      onAdded(member)
      onClose()
    } catch (err) {
      setError(errorMessage(err, 'Failed to add team member'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open={open}
      title="Add Team Member"
      description="Allocate an employee or intern to this project. This is scoped to the current project."
      onClose={close}
      closeDisabled={loading}
    >
      <form className="ax-stack" onSubmit={submit}>
        <Select
          label="Member type"
          value={memberType}
          disabled={loading}
          onChange={(event) =>
            setMemberType(event.target.value as 'employee' | 'intern')
          }
        >
          <option value="employee">Employee</option>
          <option value="intern">Intern</option>
        </Select>

        <Input
          label="Name"
          value={name}
          autoFocus
          required
          maxLength={200}
          placeholder="e.g. Maya Chen"
          disabled={loading}
          onChange={(event) => {
            setName(event.target.value)
            if (error) setError('')
          }}
        />

        <Input
          label="Role"
          value={role}
          required
          maxLength={200}
          placeholder="e.g. Backend Developer, ML Engineer, UI Designer"
          disabled={loading}
          onChange={(event) => {
            setRole(event.target.value)
            if (error) setError('')
          }}
        />

        <div className="ax-field">
          <span>Skills</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              className="ax-control"
              value={skillInput}
              disabled={loading}
              placeholder="e.g. Python, FastAPI, Docker (press Enter or comma)"
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={handleSkillKeyDown}
            />
            <Button
              type="button"
              variant="secondary"
              onClick={addSkillFromInput}
              disabled={loading || !skillInput.trim()}
              title="Add skill"
            >
              <Plus size={16} /> Add
            </Button>
          </div>
          {skills.length > 0 && (
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '6px',
                marginTop: '8px',
              }}
            >
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="ax-skill"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    margin: 0,
                  }}
                >
                  {skill}
                  <button
                    type="button"
                    onClick={() => removeSkill(skill)}
                    disabled={loading}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: 'inherit',
                      padding: 0,
                      display: 'flex',
                      alignItems: 'center',
                    }}
                    title={`Remove ${skill}`}
                  >
                    <X size={13} />
                  </button>
                </span>
              ))}
            </div>
          )}
          <small className="ax-hint">
            Type any skill and press Enter or click Add. Added skills will appear as chips.
          </small>
        </div>

        <Input
          label="Allocation duration (days)"
          type="number"
          min={1}
          max={3650}
          value={allocationDays}
          required
          disabled={loading}
          placeholder="30"
          onChange={(event) => {
            setAllocationDays(event.target.value)
            if (error) setError('')
          }}
        />

        {tasks && tasks.length > 0 && (
          <div className="ax-field">
            <span>Assign Tasks (Optional)</span>
            <small className="ax-hint" style={{ marginBottom: 6 }}>
              Select existing project tasks to assign to this member upon creation.
            </small>
            <div
              style={{
                maxHeight: '160px',
                overflowY: 'auto',
                border: '1px solid var(--ax-border, #333)',
                borderRadius: '6px',
                padding: '8px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                background: 'var(--ax-surface-raised, rgba(255, 255, 255, 0.02))',
              }}
            >
              {tasks.map((task) => {
                const isChecked = selectedTaskIds.includes(task.task_id)
                return (
                  <label
                    key={task.task_id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                      padding: '4px 6px',
                      borderRadius: '4px',
                      background: isChecked ? 'var(--ax-hover, rgba(255,255,255,0.06))' : 'transparent',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      disabled={loading}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedTaskIds((prev) => [...prev, task.task_id])
                        } else {
                          setSelectedTaskIds((prev) => prev.filter((id) => id !== task.task_id))
                        }
                      }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <strong style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {task.title}
                      </strong>
                      <span className="ax-hint" style={{ fontSize: '0.75rem' }}>
                        {task.estimated_hours}h · Current: {task.owner}
                        {task.required_skills?.length ? ` · Skills: ${task.required_skills.join(', ')}` : ''}
                      </span>
                    </div>
                  </label>
                )
              })}
            </div>
          </div>
        )}

        {error && <Banner onDismiss={() => setError('')}>{error}</Banner>}

        <div className="ax-dialog-actions">
          <Button variant="secondary" onClick={close} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading || !name.trim() || !role.trim()}>
            {loading ? 'Adding...' : 'Add Team Member'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

type EditTeamMemberDialogProps = {
  member: TeamMember | null
  projectId: number
  onClose: () => void
  onUpdated: (member: TeamMember) => void
  tasks?: TaskRow[]
  sessionName?: string
}

export function EditTeamMemberDialog({
  member,
  projectId,
  onClose,
  onUpdated,
  tasks,
  sessionName,
}: EditTeamMemberDialogProps) {
  if (!member) return null

  return (
    <EditTeamMemberForm
      key={member.id}
      member={member}
      projectId={projectId}
      tasks={tasks}
      sessionName={sessionName}
      onClose={onClose}
      onUpdated={onUpdated}
    />
  )
}

function EditTeamMemberForm({
  member,
  projectId,
  tasks,
  sessionName,
  onClose,
  onUpdated,
}: {
  member: TeamMember
  projectId: number
  tasks?: TaskRow[]
  sessionName?: string
  onClose: () => void
  onUpdated: (member: TeamMember) => void
}) {
  const [memberType, setMemberType] = useState<'employee' | 'intern'>(member.member_type === 'intern' ? 'intern' : 'employee')
  const [name, setName] = useState(member.name || '')
  const [role, setRole] = useState(member.role || '')
  const [skills, setSkills] = useState<string[]>(member.skills ? [...member.skills] : [])
  const [skillInput, setSkillInput] = useState('')
  const [allocationDays, setAllocationDays] = useState(String(member.allocation_days || 30))

  const initialTaskIds = useMemo(() => {
    if (!tasks) return []
    const targetId = `TM${member.id}`
    const rawId = String(member.id)
    return tasks
      .filter((t) => {
        if (t.employee_id === targetId || t.employee_id === rawId) return true
        if (t.collaborators?.some((c) => c.employee_id === targetId || c.employee_id === rawId)) return true
        return false
      })
      .map((t) => t.task_id)
  }, [member.id, tasks])

  const [selectedTaskIds, setSelectedTaskIds] = useState<number[]>(initialTaskIds)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function addSkillFromInput() {
    const trimmed = skillInput.trim().replace(/^,+|,+$/g, '')
    if (!trimmed) return
    const parts = trimmed
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean)

    const next = [...skills]
    for (const part of parts) {
      if (!next.includes(part)) {
        next.push(part)
      }
    }
    setSkills(next)
    setSkillInput('')
    if (error) setError('')
  }

  function handleSkillKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addSkillFromInput()
    } else if (e.key === 'Backspace' && !skillInput && skills.length > 0) {
      setSkills((prev) => prev.slice(0, -1))
    }
  }

  function removeSkill(skillToRemove: string) {
    setSkills((prev) => prev.filter((s) => s !== skillToRemove))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!member) return

    const trimmedName = name.trim()
    const trimmedRole = role.trim()

    const currentSkills = [...skills]
    const pending = skillInput.trim().replace(/^,+|,+$/g, '')
    if (pending) {
      const parts = pending
        .split(',')
        .map((p) => p.trim())
        .filter(Boolean)
      for (const part of parts) {
        if (!currentSkills.includes(part)) {
          currentSkills.push(part)
        }
      }
    }

    if (!trimmedName) {
      setError('Member name is required')
      return
    }
    if (!trimmedRole) {
      setError('Member role is required')
      return
    }
    if (currentSkills.length === 0) {
      setError('At least one skill is required. Enter a skill and press Enter or Add.')
      return
    }

    const parsedDays = parseInt(allocationDays, 10)
    if (isNaN(parsedDays) || parsedDays <= 0) {
      setError('Allocation duration must be at least 1 day')
      return
    }

    if (loading) return
    setLoading(true)
    setError('')

    try {
      const updated = await api.updateTeamMember(projectId, member.id, {
        name: trimmedName,
        role: trimmedRole,
        member_type: memberType,
        skills: currentSkills,
        allocation_days: parsedDays,
      })

      // Apply task assignment diffs if session exists
      if (sessionName) {
        const targetId = `TM${member.id}`
        const toAdd = selectedTaskIds.filter((id) => !initialTaskIds.includes(id))
        const toRemove = initialTaskIds.filter((id) => !selectedTaskIds.includes(id))

        for (const taskId of toAdd) {
          try {
            await api.addCollaborator(sessionName, taskId, {
              employee_id: targetId,
              reason: 'Assigned via member edit',
            })
          } catch (taskErr) {
            console.warn(`Could not add collaborator to task ${taskId}:`, taskErr)
          }
        }

        for (const taskId of toRemove) {
          try {
            await api.removeCollaborator(sessionName, taskId, targetId)
          } catch (taskErr) {
            console.warn(`Could not remove collaborator from task ${taskId}:`, taskErr)
          }
        }
      }

      onUpdated(updated)
      onClose()
    } catch (err) {
      setError(errorMessage(err, 'Failed to update team member'))
    } finally {
      setLoading(false)
    }
  }

  if (!member) return null

  return (
    <Dialog
      open={Boolean(member)}
      title="Edit Team Member"
      description={`Update details and task assignments for ${member.name}.`}
      onClose={onClose}
      closeDisabled={loading}
    >
      <form className="ax-stack" onSubmit={submit}>
        <Select
          label="Member type"
          value={memberType}
          disabled={loading}
          onChange={(event) =>
            setMemberType(event.target.value as 'employee' | 'intern')
          }
        >
          <option value="employee">Employee</option>
          <option value="intern">Intern</option>
        </Select>

        <Input
          label="Name"
          value={name}
          required
          maxLength={200}
          placeholder="e.g. Maya Chen"
          disabled={loading}
          onChange={(event) => {
            setName(event.target.value)
            if (error) setError('')
          }}
        />

        <Input
          label="Role"
          value={role}
          required
          maxLength={200}
          placeholder="e.g. Backend Developer, ML Engineer, UI Designer"
          disabled={loading}
          onChange={(event) => {
            setRole(event.target.value)
            if (error) setError('')
          }}
        />

        <div className="ax-field">
          <span>Skills</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              className="ax-control"
              value={skillInput}
              disabled={loading}
              placeholder="e.g. Python, FastAPI, Docker (press Enter or comma)"
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={handleSkillKeyDown}
            />
            <Button
              type="button"
              variant="secondary"
              onClick={addSkillFromInput}
              disabled={loading || !skillInput.trim()}
              title="Add skill"
            >
              <Plus size={16} /> Add
            </Button>
          </div>
          {skills.length > 0 && (
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '6px',
                marginTop: '8px',
              }}
            >
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="ax-skill"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    margin: 0,
                  }}
                >
                  {skill}
                  <button
                    type="button"
                    onClick={() => removeSkill(skill)}
                    disabled={loading}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: 'inherit',
                      padding: 0,
                      display: 'flex',
                      alignItems: 'center',
                    }}
                    title={`Remove ${skill}`}
                  >
                    <X size={13} />
                  </button>
                </span>
              ))}
            </div>
          )}
          <small className="ax-hint">
            Type any skill and press Enter or click Add. Added skills will appear as chips.
          </small>
        </div>

        <Input
          label="Allocation duration (days)"
          type="number"
          min={1}
          max={3650}
          value={allocationDays}
          required
          disabled={loading}
          placeholder="30"
          onChange={(event) => {
            setAllocationDays(event.target.value)
            if (error) setError('')
          }}
        />

        {tasks && tasks.length > 0 && (
          <div className="ax-field">
            <span>Assigned Tasks</span>
            <small className="ax-hint" style={{ marginBottom: 6 }}>
              Check tasks to assign to this member, or uncheck to remove them.
            </small>
            <div
              style={{
                maxHeight: '160px',
                overflowY: 'auto',
                border: '1px solid var(--ax-border, #333)',
                borderRadius: '6px',
                padding: '8px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                background: 'var(--ax-surface-raised, rgba(255, 255, 255, 0.02))',
              }}
            >
              {tasks.map((task) => {
                const isChecked = selectedTaskIds.includes(task.task_id)
                return (
                  <label
                    key={task.task_id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                      padding: '4px 6px',
                      borderRadius: '4px',
                      background: isChecked ? 'var(--ax-hover, rgba(255,255,255,0.06))' : 'transparent',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      disabled={loading}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedTaskIds((prev) => [...prev, task.task_id])
                        } else {
                          setSelectedTaskIds((prev) => prev.filter((id) => id !== task.task_id))
                        }
                      }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <strong style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {task.title}
                      </strong>
                      <span className="ax-hint" style={{ fontSize: '0.75rem' }}>
                        {task.estimated_hours}h · Current: {task.owner}
                        {task.required_skills?.length ? ` · Skills: ${task.required_skills.join(', ')}` : ''}
                      </span>
                    </div>
                  </label>
                )
              })}
            </div>
          </div>
        )}

        {error && <Banner onDismiss={() => setError('')}>{error}</Banner>}

        <div className="ax-dialog-actions">
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading || !name.trim() || !role.trim()}>
            {loading ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

type DeleteTeamMemberDialogProps = {
  member: TeamMember | null
  projectId: number
  onClose: () => void
  onDeleted: (memberId: number) => void
}

export function DeleteTeamMemberDialog({
  member,
  projectId,
  onClose,
  onDeleted,
}: DeleteTeamMemberDialogProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (!member) return null

  async function handleDelete() {
    if (loading || !member) return
    setLoading(true)
    setError('')
    try {
      await api.deleteTeamMember(projectId, member.id)
      onDeleted(member.id)
      onClose()
    } catch (err) {
      setError(errorMessage(err, 'Failed to remove team member'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open
      title="Remove team member"
      description={`Are you sure you want to remove "${member.name}" (${member.role}) from this project team? This will not affect the global planning roster.`}
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
            {loading ? 'Removing...' : 'Remove member'}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
