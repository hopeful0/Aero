import { Outlet, useNavigate, useSearchParams } from 'react-router-dom'
import { useProjects } from '@/api/hooks'
import { useAuthStore } from '@/store/auth'

export default function Layout() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const { data: projects } = useProjects()
  const human = useAuthStore((s) => s.human)
  const token = useAuthStore((s) => s.token)
  const setToken = useAuthStore((s) => s.setToken)
  const clear = useAuthStore((s) => s.clear)

  const projectId = params.get('project_id') ?? ''
  const onProjectChange = (value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set('project_id', value)
    else next.delete('project_id')
    setParams(next, { replace: true })
  }

  const onSearch = (value: string) => {
    const next = new URLSearchParams(params)
    const tags = value
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)
    if (tags.length) next.set('tags', tags.join(','))
    else next.delete('tags')
    next.delete('offset')
    setParams(next, { replace: true })
    if (location.pathname !== '/') navigate('/')
  }

  const onLogout = () => {
    clear()
    navigate('/login')
  }

  return (
    <div className="layout">
      <header className="layout__header">
        <button
          type="button"
          className="layout__brand"
          onClick={() => navigate('/')}
        >
          Aero
        </button>
        {human ? (
          <>
            <select
              className="layout__project-selector"
              value={projectId}
              onChange={(e) => onProjectChange(e.target.value)}
              aria-label="project selector"
            >
              <option value="">全部项目</option>
              {projects?.map((p) => (
                <option key={p.project_id} value={p.project_id}>
                  {p.name}
                </option>
              ))}
            </select>
            <input
              className="layout__search"
              type="search"
              aria-label="search by tags"
              placeholder="按标签搜索（逗号分隔）…"
              defaultValue={params.get('tags') ?? ''}
              onKeyDown={(e) => {
                if (e.key === 'Enter')
                  onSearch((e.target as HTMLInputElement).value)
              }}
            />
          </>
        ) : null}
        <div className="layout__auth">
          {human ? (
            <label className="layout__token-label">
              Agent Token
              <input
                className="layout__token-input"
                type="password"
                placeholder="agent_id.secret（用于读取产物）"
                defaultValue={token ?? ''}
                onChange={(e) => setToken(e.target.value || null)}
              />
            </label>
          ) : null}
          {human ? (
            <span className="layout__user">
              {human.name}{' '}
              <button type="button" className="layout__logout" onClick={onLogout}>
                登出
              </button>
            </span>
          ) : (
            <button
              type="button"
              className="layout__login"
              onClick={() => navigate('/login')}
            >
              登录
            </button>
          )}
        </div>
      </header>
      <main className="layout__main">
        <Outlet />
      </main>
    </div>
  )
}
