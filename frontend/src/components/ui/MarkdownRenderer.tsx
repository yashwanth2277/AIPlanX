import { useState, type ReactNode } from 'react'
import { Check, Copy } from 'lucide-react'

interface MarkdownRendererProps {
  content: string
  className?: string
}

function CodeBlock({ code, language }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }).catch(() => {})
  }

  return (
    <div className="ax-code-block my-2 overflow-hidden rounded-lg border border-[var(--ax-line)] bg-[var(--ax-input)] text-left">
      <div className="flex items-center justify-between border-b border-[var(--ax-line)] bg-[var(--ax-surface-raised)] px-3 py-1.5 text-[0.72rem] text-[var(--ax-muted)] font-mono">
        <span>{language || 'code'}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-[var(--ax-ink)] transition-colors cursor-pointer"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check size={12} className="text-[var(--ax-success)]" />
              <span>Copied</span>
            </>
          ) : (
            <>
              <Copy size={12} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-3 overflow-x-auto text-[0.8rem] font-mono leading-relaxed text-[var(--ax-ink)]">
        <code>{code}</code>
      </pre>
    </div>
  )
}

function TableBlock({ lines }: { lines: string[] }) {
  if (lines.length < 2) return null

  // Parse header
  const headerCells = lines[0]
    .split('|')
    .slice(1, -1)
    .map((c) => c.trim())

  // Parse alignment
  const alignCells = lines[1]
    .split('|')
    .slice(1, -1)
    .map((c) => c.trim())

  const alignments = alignCells.map((align) => {
    const left = align.startsWith(':')
    const right = align.endsWith(':')
    if (left && right) return 'center'
    if (right) return 'right'
    return 'left'
  })

  // Parse rows
  const rows = lines.slice(2).map((row) =>
    row
      .split('|')
      .slice(1, -1)
      .map((c) => c.trim())
  )

  return (
    <div className="ax-table-wrap my-3 overflow-x-auto rounded-lg border border-[var(--ax-line)] text-left">
      <table className="w-full text-xs divide-y divide-[var(--ax-line)]">
        <thead className="bg-[var(--ax-surface-raised)] font-semibold text-[var(--ax-ink)]">
          <tr>
            {headerCells.map((header, idx) => (
              <th
                key={idx}
                className="px-3 py-2"
                style={{ textAlign: (alignments[idx] || 'left') as 'left' | 'center' | 'right' }}
              >
                {renderInline(header)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--ax-line)]">
          {rows.map((row, rIdx) => (
            <tr key={rIdx} className="hover:bg-[var(--ax-accent-soft)] transition-colors">
              {row.map((cell, cIdx) => (
                <td
                  key={cIdx}
                  className="px-3 py-2 text-[var(--ax-ink)]"
                  style={{ textAlign: (alignments[cIdx] || 'left') as 'left' | 'center' | 'right' }}
                >
                  {renderInline(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function renderInline(text: string): ReactNode[] {
  // Normalize HTML breaks
  const parts: ReactNode[] = []
  
  // Tokenize string for inline markdown patterns:
  // 1. Inline code: `code`
  // 2. Bold italic: ***text*** or ___text___
  // 3. Bold: **text** or __text__
  // 4. Italic: *text* or _text_
  // 5. Links: [label](url)
  // 6. Break: <br> or <br/> or <br />
  const inlineRegex = /(`[^`]+`|\*\*\*[^*]+\*\*\*|___[^_]+___|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|\[[^\]]+\]\([^)]+\)|<br\s*\/?>)/g

  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = inlineRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }

    const token = match[0]

    if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code
          key={`code-${match.index}`}
          className="rounded px-1.5 py-0.5 font-mono text-[0.8em] bg-[var(--ax-input)] text-[var(--ax-accent)] border border-[var(--ax-line)]"
        >
          {token.slice(1, -1)}
        </code>
      )
    } else if (
      (token.startsWith('***') && token.endsWith('***')) ||
      (token.startsWith('___') && token.endsWith('___'))
    ) {
      parts.push(
        <strong key={`bi-${match.index}`} className="font-bold">
          <em>{renderInline(token.slice(3, -3))}</em>
        </strong>
      )
    } else if (
      (token.startsWith('**') && token.endsWith('**')) ||
      (token.startsWith('__') && token.endsWith('__'))
    ) {
      parts.push(
        <strong key={`b-${match.index}`} className="font-bold text-[var(--ax-ink)]">
          {renderInline(token.slice(2, -2))}
        </strong>
      )
    } else if (
      (token.startsWith('*') && token.endsWith('*')) ||
      (token.startsWith('_') && token.endsWith('_'))
    ) {
      parts.push(
        <em key={`i-${match.index}`} className="italic">
          {renderInline(token.slice(1, -1))}
        </em>
      )
    } else if (token.startsWith('[') && token.includes('](') && token.endsWith(')')) {
      const closeBracket = token.indexOf('](')
      const label = token.slice(1, closeBracket)
      const url = token.slice(closeBracket + 2, -1)
      const isSafe = /^https?:\/\//i.test(url) || url.startsWith('/')
      if (isSafe) {
        parts.push(
          <a
            key={`a-${match.index}`}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--ax-accent)] underline hover:opacity-80 transition-opacity"
          >
            {label}
          </a>
        )
      } else {
        parts.push(label)
      }
    } else if (/^<br\s*\/?>$/i.test(token)) {
      parts.push(<br key={`br-${match.index}`} />)
    } else {
      parts.push(token)
    }

    lastIndex = match.index + token.length
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts
}

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  if (!content) return null

  const normalized = content.replace(/\r\n/g, '\n')
  const lines = normalized.split('\n')
  const blocks: ReactNode[] = []

  let inCodeBlock = false
  let codeLanguage = ''
  let codeLines: string[] = []

  let inTable = false
  let tableLines: string[] = []

  let inList = false
  let listType: 'ul' | 'ol' = 'ul'
  let listItems: string[] = []

  let inBlockquote = false
  let blockquoteLines: string[] = []

  let paragraphLines: string[] = []

  const flushParagraph = () => {
    if (paragraphLines.length > 0) {
      const text = paragraphLines.join('\n').trim()
      if (text) {
        blocks.push(
          <p key={`p-${blocks.length}`} className="my-2 leading-relaxed text-[var(--ax-ink)]">
            {renderInline(text)}
          </p>
        )
      }
      paragraphLines = []
    }
  }

  const flushList = () => {
    if (listItems.length > 0) {
      if (listType === 'ol') {
        blocks.push(
          <ol key={`ol-${blocks.length}`} className="my-2 list-decimal pl-5 space-y-1 text-[var(--ax-ink)] text-left">
            {listItems.map((item, idx) => (
              <li key={idx} className="leading-relaxed">
                {renderInline(item)}
              </li>
            ))}
          </ol>
        )
      } else {
        blocks.push(
          <ul key={`ul-${blocks.length}`} className="my-2 list-disc pl-5 space-y-1 text-[var(--ax-ink)] text-left">
            {listItems.map((item, idx) => (
              <li key={idx} className="leading-relaxed">
                {renderInline(item)}
              </li>
            ))}
          </ul>
        )
      }
      listItems = []
      inList = false
    }
  }

  const flushBlockquote = () => {
    if (blockquoteLines.length > 0) {
      const text = blockquoteLines.join('\n').trim()
      blocks.push(
        <blockquote
          key={`quote-${blocks.length}`}
          className="my-2.5 border-l-3 border-[var(--ax-accent)] bg-[var(--ax-surface-raised)] pl-3 py-1.5 rounded-r text-xs italic text-[var(--ax-muted)] text-left"
        >
          {renderInline(text)}
        </blockquote>
      )
      blockquoteLines = []
      inBlockquote = false
    }
  }

  const flushTable = () => {
    if (tableLines.length >= 2) {
      blocks.push(<TableBlock key={`table-${blocks.length}`} lines={tableLines} />)
    } else if (tableLines.length > 0) {
      paragraphLines.push(...tableLines)
      flushParagraph()
    }
    tableLines = []
    inTable = false
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    // 1. Fenced Code Block delimiter
    if (trimmed.startsWith('```') || trimmed.startsWith('~~~')) {
      if (inCodeBlock) {
        blocks.push(
          <CodeBlock
            key={`code-${blocks.length}`}
            code={codeLines.join('\n')}
            language={codeLanguage}
          />
        )
        codeLines = []
        inCodeBlock = false
      } else {
        flushParagraph()
        flushList()
        flushBlockquote()
        flushTable()
        inCodeBlock = true
        codeLanguage = trimmed.slice(3).trim()
      }
      continue
    }

    if (inCodeBlock) {
      codeLines.push(line)
      continue
    }

    // 2. Table row detection
    const isTableRow = trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.includes('|')
    if (isTableRow) {
      flushParagraph()
      flushList()
      flushBlockquote()
      inTable = true
      tableLines.push(trimmed)
      continue
    } else if (inTable) {
      flushTable()
    }

    // 3. Blank line / paragraph separator
    if (!trimmed) {
      flushParagraph()
      flushList()
      flushBlockquote()
      continue
    }

    // 4. Headings
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/)
    if (headingMatch) {
      flushParagraph()
      flushList()
      flushBlockquote()
      const level = headingMatch[1].length
      const title = headingMatch[2]

      switch (level) {
        case 1:
          blocks.push(
            <h1 key={`h1-${blocks.length}`} className="mt-3.5 mb-1.5 text-base font-bold text-[var(--ax-ink)] text-left">
              {renderInline(title)}
            </h1>
          )
          break
        case 2:
          blocks.push(
            <h2 key={`h2-${blocks.length}`} className="mt-3 mb-1 text-[0.92rem] font-bold text-[var(--ax-ink)] text-left">
              {renderInline(title)}
            </h2>
          )
          break
        case 3:
          blocks.push(
            <h3 key={`h3-${blocks.length}`} className="mt-2.5 mb-1 text-[0.84rem] font-semibold text-[var(--ax-accent)] text-left">
              {renderInline(title)}
            </h3>
          )
          break
        default:
          blocks.push(
            <h4 key={`h4-${blocks.length}`} className="mt-2 mb-0.5 text-xs font-semibold text-[var(--ax-muted)] uppercase tracking-wider text-left">
              {renderInline(title)}
            </h4>
          )
          break
      }
      continue
    }

    // 5. Blockquote
    if (trimmed.startsWith('>')) {
      flushParagraph()
      flushList()
      inBlockquote = true
      blockquoteLines.push(trimmed.replace(/^>\s?/, ''))
      continue
    } else if (inBlockquote) {
      flushBlockquote()
    }

    // 6. Horizontal Rule
    if (/^(\*\*\*|---|___)$/.test(trimmed)) {
      flushParagraph()
      flushList()
      blocks.push(<hr key={`hr-${blocks.length}`} className="my-3 border-t border-[var(--ax-line)]" />)
      continue
    }

    // 7. Unordered list
    const ulMatch = line.match(/^(\s*)[-*+]\s+(.+)$/)
    if (ulMatch) {
      flushParagraph()
      if (!inList || listType !== 'ul') {
        flushList()
        inList = true
        listType = 'ul'
      }
      listItems.push(ulMatch[2])
      continue
    }

    // 8. Ordered list
    const olMatch = line.match(/^(\s*)\d+\.\s+(.+)$/)
    if (olMatch) {
      flushParagraph()
      if (!inList || listType !== 'ol') {
        flushList()
        inList = true
        listType = 'ol'
      }
      listItems.push(olMatch[2])
      continue
    }

    // If previously in a list and this line doesn't match a bullet, flush it
    if (inList) {
      flushList()
    }

    // Normal paragraph text line
    paragraphLines.push(line)
  }

  // Flush remaining blocks
  if (inCodeBlock && codeLines.length > 0) {
    blocks.push(
      <CodeBlock
        key={`code-${blocks.length}`}
        code={codeLines.join('\n')}
        language={codeLanguage}
      />
    )
  }
  flushTable()
  flushBlockquote()
  flushList()
  flushParagraph()

  return <div className={`ax-markdown text-xs ${className}`}>{blocks}</div>
}
