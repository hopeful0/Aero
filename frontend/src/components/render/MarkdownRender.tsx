import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import rehypeRaw from 'rehype-raw'
import DOMPurify from 'dompurify'
import 'katex/dist/katex.min.css'
import type { Root, Literal } from 'hast'
import { visit } from 'unist-util-visit'
import CodeBlock from './CodeBlock'
import MermaidBlock from './MermaidBlock'

interface MarkdownRenderProps {
  content: string
  className?: string
}

function rehypeSanitizeRaw() {
  return (tree: Root) => {
    visit(tree, (node) => {
      if (node.type === 'raw') {
        const raw = node as unknown as Literal
        if (typeof raw.value === 'string') {
          raw.value = DOMPurify.sanitize(raw.value, {
            ADD_ATTR: ['target', 'rel'],
          })
        }
      }
    })
    return tree
  }
}

interface CodeComponentProps {
  className?: string
  children?: React.ReactNode
}

function extractText(children: React.ReactNode): string {
  if (typeof children === 'string') return children
  if (Array.isArray(children)) return children.map(extractText).join('')
  return ''
}

export default function MarkdownRender({
  content,
  className,
}: MarkdownRenderProps) {
  const rehypePlugins = useMemo(
    () => [rehypeKatex, rehypeSanitizeRaw, rehypeRaw],
    [],
  )

  const components = useMemo(
    () => ({
      pre: ({ children }: { children?: React.ReactNode }) => (
        <>{children}</>
      ),
      code: ({ className: cls, children }: CodeComponentProps) => {
        const match = /language-(\w+)/.exec(cls ?? '')
        if (match) {
          const lang = match[1]
          const text = extractText(children)
          if (lang === 'mermaid') {
            return <MermaidBlock chart={text} />
          }
          return <CodeBlock code={text} lang={lang} />
        }
        return <code className="inline-code">{children}</code>
      },
      table: ({ children }: { children?: React.ReactNode }) => (
        <div className="md-table-wrap">
          <table>{children}</table>
        </div>
      ),
    }),
    [],
  )

  return (
    <div className={`markdown ${className ?? ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={rehypePlugins}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
