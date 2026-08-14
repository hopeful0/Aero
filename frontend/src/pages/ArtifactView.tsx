import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useArtifact, useFeedback, useCreateFeedback } from '@/api/hooks'
import MarkdownRender from '@/components/render/MarkdownRender'
import LineageDrawer from '@/components/lineage/LineageDrawer'
import type { FeedbackKind } from '@/api/types'

export default function ArtifactView() {
  const { artifactId } = useParams()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [comment, setComment] = useState('')

  const {
    data: artifact,
    isLoading,
    error,
  } = useArtifact(artifactId)
  const { data: feedbackList } = useFeedback(artifactId)
  const feedbackMut = useCreateFeedback(artifactId ?? '')

  if (!artifactId) {
    return <p className="muted">缺少产物 ID</p>
  }
  if (isLoading) return <p className="muted">加载中…</p>
  if (error) {
    return (
      <p className="error">
        {error instanceof Error ? error.message : '加载失败'}
      </p>
    )
  }
  if (!artifact) return <p className="muted">未找到产物</p>

  const onVote = async (kind: FeedbackKind) => {
    try {
      await feedbackMut.mutateAsync({ kind })
    } catch {
      // 错误由 UI 显示
    }
  }

  const onComment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!comment.trim()) return
    try {
      await feedbackMut.mutateAsync({ kind: 'comment', body: comment.trim() })
      setComment('')
    } catch {
      // 错误由 UI 显示
    }
  }

  const feedbacks = artifact.feedback ?? feedbackList ?? []
  const ctx = artifact.context ?? null

  return (
    <section className="page artifact">
      <header className="artifact__header">
        <div>
          <h1 className="artifact__title">{artifact.title}</h1>
          {artifact.summary ? (
            <p className="artifact__summary">{artifact.summary}</p>
          ) : null}
          <div className="artifact__meta">
            <span className="chip chip--ver">v{artifact.version}</span>
            {artifact.artifact_type ? (
              <span className="chip">{artifact.artifact_type}</span>
            ) : null}
            {artifact.tags.map((t) => (
              <span key={t} className="chip chip--tag">
                {t}
              </span>
            ))}
            {artifact.creator_agent_id ? (
              <span className="meta-label">
                Agent: {artifact.creator_agent_id}
              </span>
            ) : null}
            <time className="meta-label">
              {new Date(artifact.created_at).toLocaleString()}
            </time>
          </div>
        </div>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => setDrawerOpen(true)}
        >
          血统
        </button>
      </header>

      <div className="artifact__body">
        <MarkdownRender content={artifact.content ?? ''} />
      </div>

      {ctx ? (
        <details className="artifact__context">
          <summary>上下文快照</summary>
          <div className="context">
            {ctx.prompt_snapshot ? (
              <div className="context__section">
                <h4>Prompt 快照</h4>
                <pre className="context__pre">{ctx.prompt_snapshot}</pre>
              </div>
            ) : null}
            {ctx.execution_trace_id ? (
              <div className="context__section">
                <h4>Trace ID</h4>
                <code>{ctx.execution_trace_id}</code>
              </div>
            ) : null}
            {ctx.external_refs &&
            Object.keys(ctx.external_refs).length > 0 ? (
              <div className="context__section">
                <h4>外部溯源</h4>
                <ul className="context__refs">
                  {Object.entries(ctx.external_refs).map(([k, v]) => (
                    <li key={k}>
                      <span className="context__ref-key">{k}</span>:{' '}
                      <code>{String(v)}</code>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </details>
      ) : null}

      <section className="feedback">
        <h3 className="feedback__heading">反馈</h3>
        <div className="feedback__bar">
          <button
            type="button"
            className="btn btn--up"
            onClick={() => onVote('thumbs_up')}
            disabled={feedbackMut.isPending}
          >
            👍 Useful
          </button>
          <button
            type="button"
            className="btn btn--down"
            onClick={() => onVote('thumbs_down')}
            disabled={feedbackMut.isPending}
          >
            👎 Needs Revision
          </button>
        </div>
        <form className="feedback__form" onSubmit={onComment}>
          <textarea
            className="feedback__textarea"
            placeholder="整体评论…"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
          />
          <button
            type="submit"
            className="btn btn--primary"
            disabled={feedbackMut.isPending || !comment.trim()}
          >
            提交评论
          </button>
        </form>
        {feedbackMut.error ? (
          <p className="error">
            {feedbackMut.error instanceof Error
              ? feedbackMut.error.message
              : '提交失败'}
          </p>
        ) : null}

        <h4 className="feedback__subhead">已有反馈</h4>
        {feedbacks.length > 0 ? (
          <ul className="feedback__list">
            {feedbacks.map((fb) => (
              <li key={fb.id} className="feedback__item">
                <span className={`chip chip--fb chip--fb-${fb.kind}`}>
                  {fb.kind}
                </span>
                <span className="meta-label">v{fb.version_no}</span>
                {fb.body ? <p className="feedback__body">{fb.body}</p> : null}
                <time className="meta-label">
                  {new Date(fb.created_at).toLocaleString()}
                </time>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">暂无反馈</p>
        )}
      </section>

      <LineageDrawer
        artifactId={artifactId}
        creatorAgentId={artifact.creator_agent_id}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
    </section>
  )
}
