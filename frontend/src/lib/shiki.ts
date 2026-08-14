import { createHighlighter, type Highlighter } from 'shiki'

const COMMON_LANGS = [
  'javascript',
  'typescript',
  'jsx',
  'tsx',
  'python',
  'bash',
  'shell',
  'json',
  'yaml',
  'html',
  'css',
  'sql',
  'markdown',
  'go',
  'rust',
  'java',
  'diff',
  'dockerfile',
] as const

const THEME = 'github-dark-dimmed'

let highlighterPromise: Promise<Highlighter> | null = null

export function getHighlighter(): Promise<Highlighter> {
  if (!highlighterPromise) {
    highlighterPromise = createHighlighter({
      themes: [THEME],
      langs: [...COMMON_LANGS],
    })
  }
  return highlighterPromise
}

export async function highlightCode(
  code: string,
  lang: string,
): Promise<string | null> {
  try {
    const hl = await getHighlighter()
    const loaded = hl.getLoadedLanguages()
    if (!loaded.includes(lang)) {
      await hl.loadLanguage(lang as never).catch(() => null)
    }
    return hl.codeToHtml(code, { lang, theme: THEME })
  } catch {
    return null
  }
}

export { THEME }
