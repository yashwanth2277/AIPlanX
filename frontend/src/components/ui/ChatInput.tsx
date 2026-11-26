import { useEffect, useRef, type KeyboardEvent, type FormEvent } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { Button } from './Button'

interface ChatInputProps {
  value: string
  onChange: (val: string) => void
  onSubmit: (e?: FormEvent) => void
  disabled?: boolean
  loading?: boolean
  placeholder?: string
}

const MIN_HEIGHT = 40
const MAX_HEIGHT = 140

export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  loading = false,
  placeholder = 'Ask about this session…',
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea height to fit content up to MAX_HEIGHT
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    const scrollH = el.scrollHeight
    const newHeight = Math.min(Math.max(scrollH, MIN_HEIGHT), MAX_HEIGHT)
    el.style.height = `${newHeight}px`
  }, [value])

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!disabled && !loading && value.trim()) {
        onSubmit()
      }
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!disabled && !loading && value.trim()) {
      onSubmit(e)
    }
  }

  return (
    <form className="ax-chat-input-form" onSubmit={handleSubmit}>
      <div className="ax-chat-input-box">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || loading}
          rows={1}
          className="ax-chat-textarea"
          aria-label="Ask assistant message input"
        />
        <Button
          type="submit"
          aria-label="Send question"
          disabled={disabled || loading || !value.trim()}
          className="ax-chat-send-btn"
        >
          <ArrowUpRight size={18} />
        </Button>
      </div>
      <div className="ax-chat-input-hint">
        <span>Press <strong>Enter</strong> to send, <strong>Shift+Enter</strong> for newline</span>
      </div>
    </form>
  )
}
