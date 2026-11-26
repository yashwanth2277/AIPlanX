import { useState, useRef, useEffect, type FormEvent } from 'react'
import { Bot, Maximize2, Minimize2, RotateCcw, Sparkles, X } from 'lucide-react'
import { IconButton } from '../components/ui/IconButton'
import { MarkdownRenderer } from '../components/ui/MarkdownRenderer'
import { ChatInput } from '../components/ui/ChatInput'
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
    clearChat,
  } = useWorkspace()

  const [expanded, setExpanded] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll to bottom on new messages or thinking state
  useEffect(() => {
    if (assistantOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [chat, asking, assistantOpen])

  function ask(event?: FormEvent) {
    void submitQuestion(event)
  }

  function handlePromptClick(promptText: string) {
    setQuestion(promptText)
  }

  if (!assistantOpen) {
    return (
      <button
        type="button"
        className="ax-assistant-fab"
        aria-label="Open AI project assistant"
        onClick={() => setAssistantOpen(true)}
      >
        <Bot size={24} />
      </button>
    )
  }

  return (
    <section
      className={`ax-assistant-panel ${expanded ? 'is-expanded' : ''}`}
      aria-label="AI project assistant"
    >
      {/* Header */}
      <div className="ax-assistant-head">
        <div className="flex items-center gap-2.5">
          <div className="ax-assistant-avatar-badge">
            <Bot size={17} />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <strong className="text-sm font-semibold text-[var(--ax-ink)]">AI Project Assistant</strong>
              <span className="ax-status-pill text-[0.65rem] px-1.5 py-0.2 rounded-full bg-[var(--ax-success-soft)] text-[var(--ax-success)] font-medium">
                Active
              </span>
            </div>
            <p className="ax-hint text-xs">
              {sessionName ? `Session: ${sessionName}` : 'No active session'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {chat.length > 0 && (
            <IconButton
              aria-label="Clear chat history"
              title="Clear conversation"
              onClick={clearChat}
              className="text-[var(--ax-muted)] hover:text-[var(--ax-danger)]"
            >
              <RotateCcw size={15} />
            </IconButton>
          )}
          <IconButton
            aria-label={expanded ? 'Narrow dialog' : 'Expand dialog'}
            title={expanded ? 'Narrow dialog' : 'Expand dialog'}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </IconButton>
          <IconButton
            aria-label="Close assistant"
            title="Close dialog"
            onClick={() => setAssistantOpen(false)}
          >
            <X size={16} />
          </IconButton>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="ax-chat-messages-container">
        {chat.length === 0 ? (
          <div className="ax-assistant-empty-state">
            <div className="ax-assistant-welcome-icon">
              <Sparkles size={24} className="text-[var(--ax-accent)]" />
            </div>
            <h3 className="text-sm font-semibold text-[var(--ax-ink)] mb-1">
              How can I help with your project?
            </h3>
            <p className="text-xs text-[var(--ax-muted)] max-w-sm mb-4 leading-relaxed">
              I can analyze your live project tasks, team availability, delays, and schedule, and offer actionable recommendations.
            </p>
            <div className="ax-suggest-chips">
              <p className="text-[0.7rem] uppercase tracking-wider text-[var(--ax-muted)] font-medium mb-1.5">
                Suggested questions:
              </p>
              <div className="flex flex-col gap-2 w-full">
                {prompts.map((text) => (
                  <button
                    key={text}
                    type="button"
                    className="ax-suggest-btn"
                    onClick={() => handlePromptClick(text)}
                  >
                    <span>{text}</span>
                    <Sparkles size={13} className="text-[var(--ax-accent)] opacity-80" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3.5">
            {chat.map((turn, index) => (
              <div
                key={`${turn.role}-${index}`}
                className={turn.role === 'user' ? 'ax-message-row-user' : 'ax-message-row-bot'}
              >
                {turn.role === 'bot' && (
                  <div className="ax-message-avatar">
                    <Bot size={15} />
                  </div>
                )}
                <div className={turn.role === 'user' ? 'ax-message-bubble-user' : 'ax-message-bubble-bot'}>
                  {turn.role === 'bot' ? (
                    <MarkdownRenderer content={turn.text} />
                  ) : (
                    <div className="whitespace-pre-wrap text-xs leading-relaxed">{turn.text}</div>
                  )}
                </div>
              </div>
            ))}

            {asking && (
              <div className="ax-message-row-bot">
                <div className="ax-message-avatar animate-pulse">
                  <Bot size={15} />
                </div>
                <div className="ax-message-bubble-bot flex items-center gap-2 py-3 px-4">
                  <span className="ax-thinking-dot" />
                  <span className="text-xs text-[var(--ax-muted)] italic">
                    Thinking with live project context…
                  </span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Quick Prompts Bar (when chat is already active) */}
      {chat.length > 0 && (
        <div className="ax-quick-prompts-bar">
          {prompts.map((text) => (
            <button
              key={text}
              type="button"
              className="ax-quick-chip"
              onClick={() => handlePromptClick(text)}
              disabled={asking}
            >
              {text}
            </button>
          ))}
        </div>
      )}

      {/* Input Footer */}
      <div className="ax-assistant-footer">
        <ChatInput
          value={question}
          onChange={setQuestion}
          onSubmit={ask}
          disabled={!sessionName}
          loading={asking}
          placeholder={sessionName ? 'Ask about tasks, delays, team, or status…' : 'No active session'}
        />
        <p className="ax-assistant-note">
          Suggestions only. Answers reflect current state and never modify files.
        </p>
      </div>
    </section>
  )
}
