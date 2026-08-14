import { useEffect, useState } from 'react'

interface HealthState {
  loading: boolean
  ok: boolean
  status: number
  payload: unknown
  error: string | null
}

const INITIAL: HealthState = {
  loading: true,
  ok: false,
  status: 0,
  payload: null,
  error: null,
}

export default function Health() {
  const [state, setState] = useState<HealthState>(INITIAL)

  useEffect(() => {
    let active = true
    setState(INITIAL)
    fetch('/healthz', { headers: { Accept: 'application/json' } })
      .then(async (res) => {
        const text = await res.text()
        let payload: unknown = text
        try {
          payload = JSON.parse(text)
        } catch {
          payload = text
        }
        if (!active) return
        setState({
          loading: false,
          ok: res.ok,
          status: res.status,
          payload,
          error: res.ok ? null : `HTTP ${res.status}`,
        })
      })
      .catch((err: unknown) => {
        if (!active) return
        setState({
          loading: false,
          ok: false,
          status: 0,
          payload: null,
          error: err instanceof Error ? err.message : String(err),
        })
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <section className="page">
      <h1>后端健康</h1>
      {state.loading ? (
        <p>探测中…</p>
      ) : (
        <dl className="health">
          <div>
            <dt>状态</dt>
            <dd>{state.ok ? '✅ OK' : '❌ DOWN'}</dd>
          </div>
          <div>
            <dt>HTTP</dt>
            <dd>{state.status || '—'}</dd>
          </div>
          {state.error ? (
            <div>
              <dt>错误</dt>
              <dd>{state.error}</dd>
            </div>
          ) : null}
          <div>
            <dt>响应</dt>
            <dd>
              <pre className="health__payload">
                {typeof state.payload === 'string'
                  ? state.payload
                  : JSON.stringify(state.payload, null, 2)}
              </pre>
            </dd>
          </div>
        </dl>
      )}
    </section>
  )
}
