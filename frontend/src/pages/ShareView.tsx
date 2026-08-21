import { Link, useParams } from 'react-router-dom'
import { useShareTokenRead } from '@/api/hooks'
import { ApiError } from '@/api/client'
import MarkdownRender from '@/components/render/MarkdownRender'

export default function ShareView() {
  const { artifactId, token } = useParams()
  const { data, isLoading, error } = useShareTokenRead(artifactId, token)

  if (isLoading) return <p className="muted">加载中…</p>

  if (error) {
    const is404 = error instanceof ApiError && error.status === 404
    return (
      <div className="artifact__notfound" role="alert">
        <h1>{is404 ? '分享链接无效或已失效' : '暂时无法访问'}</h1>
        <p className="muted">
          {is404
            ? '该分享链接不存在、已被吊销或已过期。'
            : error instanceof Error
              ? error.message
              : '加载失败'}
        </p>
      </div>
    )
  }

  if (!data) return <p className="muted">未找到分享内容</p>

  return (
    <section className="page artifact">
      <header className="artifact__header">
        <div>
          <h1 className="artifact__title">{data.title}</h1>
          {data.summary ? <p className="artifact__summary">{data.summary}</p> : null}
          <div className="artifact__meta">
            <span className="chip chip--ver">v{data.version}</span>
            {data.artifact_type ? <span className="chip">{data.artifact_type}</span> : null}
            {data.tags.map((tag) => (
              <span key={tag} className="chip chip--tag">
                {tag}
              </span>
            ))}
            <time className="meta-label">
              {new Date(data.created_at).toLocaleString()}
            </time>
          </div>
        </div>
      </header>
      {data.content ? (
        <div className="artifact__body">
          <MarkdownRender content={data.content} />
        </div>
      ) : (
        <p className="muted">该产物暂无正文内容。</p>
      )}
      <footer className="artifact__share-footer">
        <span className="muted">由匿名分享链接公开</span>
        <Link className="link" to="/">
          返回首页
        </Link>
      </footer>
    </section>
  )
}