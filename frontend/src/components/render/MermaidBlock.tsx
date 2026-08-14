import { useEffect, useId, useState } from 'react'
import mermaid from 'mermaid'
import DOMPurify from 'dompurify'

let initialized = false

function ensureInit(): void {
  if (initialized) return
  initialized = true
  mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'strict',
    fontFamily: 'system-ui, sans-serif',
  })
}

interface MermaidBlockProps {
  chart: string
}

export default function MermaidBlock({ chart }: MermaidBlockProps) {
  const rawId = useId()
  const id = `mermaid-${rawId.replace(/[^a-zA-Z0-9-]/g, '')}`
  const [svg, setSvg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    ensureInit()
    mermaid
      .parse(chart)
      .then(() => mermaid.render(id, chart))
      .then((res) => {
        if (active) {
          setSvg(DOMPurify.sanitize(res.svg, { USE_PROFILES: { svg: true, svgFilters: true } }))
          setError(null)
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : String(err))
          setSvg(null)
        }
      })
    return () => {
      active = false
    }
  }, [chart, id])

  if (error) {
    return (
      <pre className="mermaid-block mermaid-block--error">
        <code>{chart}</code>
        <span className="mermaid-block__error">{error}</span>
      </pre>
    )
  }
  if (svg) {
    return (
      <div
        className="mermaid-block"
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    )
  }
  return (
    <pre className="mermaid-block mermaid-block--placeholder">
      <code>{chart}</code>
    </pre>
  )
}
