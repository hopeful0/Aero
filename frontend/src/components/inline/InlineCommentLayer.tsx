import { useEffect, useState } from 'react'
import Drawer from '@/components/Drawer'
import MigrationBadge from './MigrationBadge'
import type { Feedback, VersionBlock } from '@/api/types'

interface SelectedBlock {
  id: string
  index: number
  path: string
  preview: string
}

interface InlineCommentLayerProps {
  // 查看版本的 block 列表：用于按 block_id 查 block_path，匹配 fuzzy 行内评论。
  blocks: VersionBlock[]
  // 全部评论（带 migration_status）：行内面板按 block_id/block_path 过滤；
  // stale 评论在此不匹配任何块，由版本级区域降级展示。
  feedbacks: Feedback[]
  canComment: boolean
  containerRef: React.RefObject<HTMLDivElement | null>
  onSubmit: (input: {
    body: string
    block_id: string
    version_no: number
  }) => Promise<void>
  submitting: boolean
  submitError: Error | null
  versionNo: number
}

export default function InlineCommentLayer({
  blocks,
  feedbacks,
  canComment,
  containerRef,
  onSubmit,
  submitting,
  submitError,
  versionNo,
}: InlineCommentLayerProps) {
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<SelectedBlock | null>(null)
  const [draft, setDraft] = useState('')

  // 事件委托：点击带 data-block-id 的块即打开行内评论面板。
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const onClick = (e: MouseEvent) => {
      const target = (e.target as HTMLElement).closest<HTMLElement>(
        '[data-block-id]',
      )
      if (!target) return
      const id = target.dataset.blockId
      const index = Number(target.dataset.blockIndex ?? NaN)
      if (!id || Number.isNaN(index)) return
      const block = blocks.find((b) => b.block_id === id)
      setSelected({
        id,
        index,
        path: block?.block_path ?? '',
        preview: (block?.content_preview ?? '').trim(),
      })
      setDraft('')
      setOpen(true)
    }
    container.addEventListener('click', onClick)
    return () => container.removeEventListener('click', onClick)
  }, [containerRef, blocks])

  const blockFeedbacks: Feedback[] = selected
    ? feedbacks
        .filter((fb) => {
          if (!fb.inline_anchor) return false
          // exact: block_id 命中查看版本；fuzzy: block_path 命中查看版本。
          if (fb.inline_anchor.block_id === selected.id) return true
          if (selected.path && fb.inline_anchor.block_path === selected.path) {
            return true
          }
          return false
        })
        .sort((a, b) => a.created_at.localeCompare(b.created_at))
    : []

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selected || !draft.trim()) return
    try {
      // 成功与否只取决于 onSubmit 返回的 promise，而不是闭包里快照的 submitError：
      // 若上次失败后本闭包捕获到旧的 submitError，下一次成功提交会被误判为失败从而不清空草稿。
      // 父组件 useMutation 会在新提交时把 error 置空，故这里无需也不应重置 submitError。
      await onSubmit({
        body: draft.trim(),
        block_id: selected.id,
        version_no: versionNo,
      })
      setDraft('')
    } catch {
      // 失败时由父组件 useMutation 写回 submitError，经 props 触发重新渲染展示错误。
    }
  }

  return (
    <Drawer
      open={open}
      onOpenChange={setOpen}
      title="行内评论"
      description={selected?.preview || undefined}
    >
      {selected ? (
        <section className="inline-comment">
          <div className="inline-comment__block-meta">
            <span className="chip">块 #{selected.index}</span>
            <code className="inline-comment__block-id">{selected.id}</code>
          </div>
          {selected.path ? (
            <p className="inline-comment__path muted">{selected.path}</p>
          ) : null}

          {canComment ? (
            <form className="inline-comment__form" onSubmit={handleSubmit}>
              <textarea
                className="feedback__textarea"
                placeholder="对该段落发表评论…"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={3}
              />
              <button
                type="submit"
                className="btn btn--primary"
                disabled={submitting || !draft.trim()}
              >
                {submitting ? '提交中…' : '提交评论'}
              </button>
            </form>
          ) : (
            <p className="muted inline-comment__login-hint">
              登录后可查看与发表行内评论。
            </p>
          )}

          {submitError && canComment ? (
            <p className="error">
              {submitError instanceof Error
                ? submitError.message
                : '提交失败'}
            </p>
          ) : null}

          <h4 className="feedback__subhead">
            已有评论（{blockFeedbacks.length}）
          </h4>
          {blockFeedbacks.length > 0 ? (
            <ul className="feedback__list">
              {blockFeedbacks.map((fb) => (
                <li key={fb.id} className="feedback__item">
                  <div className="feedback__item-head">
                    <MigrationBadge status={fb.migration_status} />
                    <span className="meta-label">v{fb.version_no}</span>
                    <time className="meta-label">
                      {new Date(fb.created_at).toLocaleString()}
                    </time>
                  </div>
                  {fb.body ? (
                    <p className="feedback__body">{fb.body}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">该段落暂无评论</p>
          )}
        </section>
      ) : null}
    </Drawer>
  )
}
