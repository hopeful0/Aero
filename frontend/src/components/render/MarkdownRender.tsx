import { useEffect, useMemo, useRef } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import rehypeRaw from 'rehype-raw'
import DOMPurify from 'dompurify'
import 'katex/dist/katex.min.css'
import type { Element as HastElement, Literal, Root } from 'hast'
import CodeBlock from './CodeBlock'
import MermaidBlock from './MermaidBlock'
import type { VersionBlock } from '@/api/types'

interface MarkdownRenderProps {
  content: string
  className?: string
  // 后端权威 block 列表；按 block_index 顺序注入到渲染后的顶层 DOM 节点。
  blocks?: VersionBlock[]
}

// rehype-raw 会把 markdown 内联 HTML 解析成真正的 hast 元素节点，此时原来的 mdast raw
// 节点已消失。因此除了清理残留 raw 节点外，还必须在元素节点上做防御清洗：丢弃可执行脚本
// 类标签、删除 on* 与 javascript: 协议属性，防止 rehype-raw 放行原始 HTML 造成 XSS。
const DANGEROUS_TAGS = new Set([
  'script',
  'iframe',
  'object',
  'embed',
  'applet',
  'frame',
  'frameset',
  'base',
  'meta',
  'link',
  'form',
  'button',
  'select',
  'textarea',
  'param',
])

const isJavascriptProtocol = (value: unknown): boolean =>
  typeof value === 'string' && /^\s*(javascript|vbscript):/i.test(value)

function sanitizeNode(node: HastElement | Literal): HastElement | null {
  // 残留的 raw 节点（如注释）用 DOMPurify 兜底；hast 元素节点无 value 属性，用 in 收窄。
  if ('value' in node) {
    if (typeof node.value === 'string') {
      node.value = DOMPurify.sanitize(node.value, {
        ADD_ATTR: ['target', 'rel'],
      })
    }
    return node as unknown as HastElement
  }
  if (DANGEROUS_TAGS.has(node.tagName.toLowerCase())) return null

  const props = node.properties ?? {}
  for (const key of Object.keys(props)) {
    const lk = key.toLowerCase()
    if (lk.startsWith('on')) delete props[key]
    if (
      (lk === 'href' || lk === 'src' || lk === 'xlink:href') &&
      isJavascriptProtocol(props[key])
    ) {
      delete props[key]
    }
  }
  node.children = node.children.flatMap((child) => {
    const cleaned = sanitizeNode(child as HastElement | Literal)
    return cleaned ? [cleaned as HastElement] : []
  })
  return node
}

function rehypeSanitizeRaw() {
  return (tree: Root) => {
    tree.children = tree.children.flatMap((child) => {
      const cleaned = sanitizeNode(child as HastElement | Literal)
      return cleaned ? [cleaned] : []
    })
    return tree
  }
}

function extractText(children: React.ReactNode): string {
  if (typeof children === 'string') return children
  if (Array.isArray(children)) return children.map(extractText).join('')
  return ''
}

export default function MarkdownRender({
  content,
  className,
  blocks,
}: MarkdownRenderProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  // 渲染后按序把 block 元数据注入到顶层可见块元素上。
  // 不走 rehype 插件改 hast，避免 react-markdown 内部对注入节点的处理异常。
  useEffect(() => {
    const root = containerRef.current
    if (!root || !blocks || blocks.length === 0) return
    const topLevel = Array.from(root.children).filter(
      (el): el is HTMLElement => el instanceof HTMLElement,
    )
    for (let i = 0; i < Math.min(topLevel.length, blocks.length); i++) {
      const block = blocks[i]
      if (!block) break
      topLevel[i].dataset.blockId = block.block_id
      topLevel[i].dataset.blockIndex = String(block.block_index)
    }
  }, [content, blocks])

  // 顺序：先 rehypeRaw 把内联 HTML 解析成 hast 元素节点，紧跟 rehypeSanitizeRaw 做防御清洗
  //（此时 raw 节点已被解析，逐元素处理才能覆盖 script/事件属性），最后 rehypeKatex，
  // 避免 DOMPurify 误清 KaTeX 生成的 math 标记。
  const rehypePlugins = useMemo(
    () => [rehypeRaw, rehypeSanitizeRaw, rehypeKatex],
    [],
  )

  const components = useMemo<Components>(
    () => ({
      // pre 本身不输出 DOM（children 是 code），但 code block 是顶层块，
      // 需要有一个挂载 data-block-id 的可见容器，供行内评论锚定。
      pre: ({ children }) => <div className="md-pre-wrap">{children}</div>,
      code: ({ className: cls, children }) => {
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
      table: ({ children }) => (
        <div className="md-table-wrap">
          <table>{children}</table>
        </div>
      ),
    }),
    [],
  )

  return (
    <div ref={containerRef} className={`markdown ${className ?? ''}`}>
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