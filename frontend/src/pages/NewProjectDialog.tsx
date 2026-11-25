import { useCallback, useState, type FormEvent } from 'react'
import { api } from '../api'
import { errorMessage } from '../lib/format'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Dialog } from '../components/ui/Dialog'
import { Input } from '../components/ui/Input'

type NewProjectDialogProps = {
  open: boolean
  onClose: () => void
  onCreated?: () => void
}

export function NewProjectDialog({ open, onClose, onCreated }: NewProjectDialogProps) {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const close = useCallback(() => {
    if (loading) return
    setName('')
    setError('')
    onClose()
  }, [loading, onClose])

  async function submit(event: FormEvent) {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setError('Project name is required')
      return
    }
    if (loading) return

    setLoading(true)
    setError('')
    try {
      await api.createProject({ name: trimmed })
      setName('')
      onCreated?.()
      onClose()
    } catch (err) {
      setError(errorMessage(err, 'Failed to create project'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open={open}
      title="New project"
      description="Start with a name. Planning stays a separate step."
      onClose={close}
      closeDisabled={loading}
    >
      <form className="ax-stack" onSubmit={submit}>
        <Input
          label="Project name"
          value={name}
          autoFocus
          required
          maxLength={120}
          placeholder="Campus platform"
          disabled={loading}
          onChange={(event) => {
            setName(event.target.value)
            if (error) setError('')
          }}
        />
        {error && (
          <Banner onDismiss={() => setError('')}>
            {error}
          </Banner>
        )}
        <div className="ax-dialog-actions">
          <Button variant="secondary" onClick={close} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading || !name.trim()}>
            {loading ? 'Creating...' : 'Create project'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
