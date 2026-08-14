import { useEffect, useState } from 'react'
import { highlightCode } from '@/lib/shiki'

interface CodeBlockProps {
  code: string
  lang: string
}

export default function CodeBlock({ code, lang }: CodeBlockProps) {
  const [html, setHtml] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let active = true
    highlightCode(code.replace(/\n$/, ''), lang).then((out) => {
      if (active) setHtml(out)
    })
    return () => {
      active = false
    }
  }, [code, lang])

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(code.replace(/\n$/, ''))
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  if (html) {
    return (
      <div className="codeblock">
        <div className="codeblock__bar">
          <span className="codeblock__lang">{lang}</span>
          <button
            type="button"
            className="codeblock__copy"
            onClick={onCopy}
            aria-label="copy code"
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <div
          className="codeblock__code"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </div>
    )
  }
  return (
    <div className="codeblock codeblock--fallback">
      <div className="codeblock__bar">
        <span className="codeblock__lang">{lang}</span>
        <button
          type="button"
          className="codeblock__copy"
          onClick={onCopy}
          aria-label="copy code"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="codeblock__code">
        <code>{code.replace(/\n$/, '')}</code>
      </pre>
    </div>
  )
}
