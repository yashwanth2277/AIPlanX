import { useState, type FormEvent } from 'react'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Dialog } from '../components/ui/Dialog'
import { Input } from '../components/ui/Input'

export function NewProjectDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState('')
  const [notice, setNotice] = useState(false)

  function close() {
    setName('')
    setNotice(false)
    onClose()
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    setNotice(true)
  }

  return (
    <Dialog
      open={open}
      title="New project"
      description="Start with a name. Planning stays a separate step."
      onClose={close}
    >
      <form className="ax-stack" onSubmit={submit}>
        <Input
          label="Project name"
          value={name}
          autoFocus
          required
          maxLength={120}
          placeholder="Campus platform"
          onChange={(event) => {
            setName(event.target.value)
            setNotice(false)
          }}
        />
        {notice && (
          <Banner>
            <strong>A name is not enough to create a project yet.</strong>
            <p>
              The API has no endpoint that stores a project from a name alone. Projects are created
              only when AI planning runs with a description (`POST /api/projects/plan`). This dialog
              will not start that job. Open an existing project and use AI Planning Studio when you
              are ready to generate a plan.
            </p>
          </Banner>
        )}
        <div className="ax-dialog-actions">
          <Button variant="secondary" onClick={close}>Close</Button>
          <Button type="submit" disabled={!name.trim()}>Continue</Button>
        </div>
      </form>
    </Dialog>
  )
}
