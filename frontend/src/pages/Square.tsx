import { Link, useSearchParams } from 'react-router-dom'
import { useArtifactList, useProjects } from '@/api/hooks'
import type { ArtifactListItem } from '@/api/types'

const ARTIFACT_TYPES = ['', 'markdown', 'code', 'json_schema', 'html']

export default function Square() {
  const [params, setParams] = useSearchParams()
  const projectId = params.get('project_id') ?? undefined
  const tagsParam = params.get('tags') ?? ''
  const tags = tagsParam ? tagsParam.split(',').map((t) => t.trim()).filter(Boolean) : undefined
  const type = params.get('type') ?? undefined
  const creator = params.get('creator_agent_id') ?? undefined

  const { data, isLoading, error } = useArtifactList({
    project_id: projectId,
    tags,
    type,
    creator_agent_id: creator,
    limit: 50,
    offset: 0,
  })
  const { data: projects } = useProjects()

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('offset')
    setParams(next, { replace: true })
  }

  return (
    <section className="page square">
      <div className="square__head">
        <h1>产物广场</h1>
        <p className="square__sub">
          按项目 / 标签 / 类型 / 创建者过滤，点击卡片进入评审。
        </p>
      </div>

      <form className="square__filters" onSubmit={(e) => e.preventDefault()}>
        <label className="field">
          <span>项目</span>
          <select
            value={projectId ?? ''}
            onChange={(e) => update('project_id', e.target.value)}
          >
            <option value="">全部</option>
            {projects?.map((p) => (
              <option key={p.project_id} value={p.project_id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>标签（逗号分隔）</span>
          <input
            type="text"
            value={tagsParam}
            onChange={(e) => update('tags', e.target.value)}
            placeholder="tag1,tag2"
          />
        </label>
        <label className="field">
          <span>类型</span>
          <select
            value={type ?? ''}
            onChange={(e) => update('type', e.target.value)}
          >
            {ARTIFACT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t || '全部'}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>创建 Agent ID</span>
          <input
            type="text"
            value={creator ?? ''}
            onChange={(e) => update('creator_agent_id', e.target.value)}
            placeholder="agent_..."
          />
        </label>
      </form>

      {isLoading ? (
        <p className="muted">加载中…</p>
      ) : error ? (
        <p className="error">
          {error instanceof Error ? error.message : '加载失败'}
        </p>
      ) : data && data.length > 0 ? (
        <ul className="square__grid">
          {data.map((item: ArtifactListItem) => (
            <li key={item.artifact_id} className="card">
              <Link
                className="card__link"
                to={`/artifacts/${item.artifact_id}`}
              >
                <h3 className="card__title">{item.title}</h3>
                {item.summary ? (
                  <p className="card__summary">{item.summary}</p>
                ) : null}
                <div className="card__meta">
                  <span className="chip chip--ver">v{item.current_version}</span>
                  {item.artifact_type ? (
                    <span className="chip">{item.artifact_type}</span>
                  ) : null}
                  {item.tags.map((t) => (
                    <span key={t} className="chip chip--tag">
                      {t}
                    </span>
                  ))}
                </div>
                <time className="card__time">
                  {new Date(item.updated_at).toLocaleString()}
                </time>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">暂无产物，调整过滤条件或等待 Agent 发布。</p>
      )}
    </section>
  )
}
