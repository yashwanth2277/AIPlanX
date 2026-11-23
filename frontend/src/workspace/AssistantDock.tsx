import { useState, type FormEvent } from 'react'
import { ArrowUpRight, Bot, Sparkles, X } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { IconButton } from '../components/ui/IconButton'
import { Input } from '../components/ui/Input'
import { useWorkspace } from './useWorkspace'

const prompts = ['Summarize project status', 'Which tasks need attention?', 'Suggest next priorities']

export function AssistantDock() {
  const {
    sessionName,
    chat,
    question,
    asking,
    assistantOpen,
    setAssistantOpen,
    setQuestion,
    submitQuestion,
  } = useWorkspace()
  const [open, setOpen] = useState(assistantOpen)
  const visible = open || assistantOpen

  function ask(event?: FormEvent) {
    setOpen(true)
    void submitQuestion(event)
  }

  if (!visible) {
    return (
      <button type="button" className="ax-assistant-fab" aria-label="Open AI assistant" onClick={() => setOpen(true)}>
        <Bot size={22} />
      </button>
    )
  }

  return (
    <section className="ax-assistant-panel" aria-label="AI assistant">
      <div className="ax-assistant-head">
        <Bot size={18} />
        <div style={{ flex: 1 }}>
          <strong>AI Project Assistant</strong>
          <p className="ax-hint">{sessionName ? `Session ${sessionName}` : 'No session'}</p>
        </div>
        <IconButton aria-label="Close assistant" onClick={() => { setOpen(false); setAssistantOpen(false) }}>
          <X size={16} />
        </IconButton>
      </div>
      <div className="ax-chat">
        {chat.length === 0 && (
          <>
            <p className="ax-hint">Answers use this session and do not change saved project state.</p>
            <div className="ax-suggest">
              {prompts.map((text) => (
                <button key={text} type="button" onClick={() => setQuestion(text)}>
                  {text} <Sparkles size={14} />
                </button>
              ))}
            </div>
          </>
        )}
        {chat.map((turn, index) => (
          <p className={turn.role === 'user' ? 'ax-chat-user' : 'ax-chat-bot'} key={`${turn.role}-${index}`}>{turn.text}</p>
        ))}
        {asking && <p className="ax-chat-bot">Thinking with live project context…</p>}
      </div>
      <form className="ax-assistant-form" onSubmit={ask}>
        <Input value={question} placeholder="Ask about this session" onChange={(event) => setQuestion(event.target.value)} disabled={!sessionName} />
        <Button type="submit" aria-label="Send question" disabled={asking || !sessionName || !question.trim()}>
          <ArrowUpRight size={16} />
        </Button>
      </form>
      <p className="ax-assistant-note">Suggestions only. You stay in control.</p>
    </section>
  )
}
