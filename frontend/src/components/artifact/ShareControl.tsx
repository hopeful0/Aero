import { useEffect, useRef, useState } from 'react'
import Drawer from '@/components/Drawer'
import {
  useCreateShareToken,
  useRevokeShareToken,
  useToggleVisibility,
} from '@/api/hooks'
import type { ShareTokenCreateResult } from '@/api/types'

interface ShareControlProps {
  artifactId: string
  visibility: 'private' | 'public'
  onUpdated?: (next: 'private' | 'public') => void
}

export default function ShareControl({
  artifactId,
  visibility,
  onUpdated,
}: ShareControlProps) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [activeLink, setActiveLink] = useState<ShareTokenCreateResult | null>(null)
  const [linkError, setLinkError] = useState<string | null>(null)
  const toggleMut = useToggleVisibility(artifactId)
  const createTokenMut = useCreateShareToken()
  const revokeTokenMut = useRevokeShareToken()
  const copyTimer = useRef<number | null>(null)

  useEffect(
    () => () => {
      if (copyTimer.current) window.clearTimeout(copyTimer.current)
    },
    [],
  )

  const next = visibility === 'public' ? 'private' : 'public'
  const toggling = toggleMut.isPending

  const doToggle = async () => {
    setErrorMsg(null)
    try {
      await toggleMut.mutateAsync({ visibility: next })
      onUpdated?.(next)
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : '切换失败')
    }
  }

  const onClickToggle = () => {
    if (next === 'public') {
      setConfirmOpen(true)
    } else {
      void doToggle()
    }
  }

  const onConfirmPublic = async () => {
    setConfirmOpen(false)
    await doToggle()
  }

  const flashCopied = async (url: string) => {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(url)
      } else {
        const ta = document.createElement('textarea')
        ta.value = url
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      }
      setCopied(true)
      if (copyTimer.current) window.clearTimeout(copyTimer.current)
      copyTimer.current = window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  const onCreateLink = async () => {
    setLinkError(null)
    try {
      const created = await createTokenMut.mutateAsync({ artifactId })
      setActiveLink(created)
    } catch (e) {
      setLinkError(e instanceof Error ? e.message : '生成失败')
    }
  }

  const onRevokeLink = async () => {
    if (!activeLink) return
    setLinkError(null)
    try {
      await revokeTokenMut.mutateAsync({
        artifactId,
        tokenId: activeLink.share_token_id,
      })
      setActiveLink(null)
    } catch (e) {
      setLinkError(e instanceof Error ? e.message : '吊销失败')
    }
  }

  return (
    <div className="share-control">
      <button
        type="button"
        className="btn btn--ghost"
        onClick={onClickToggle}
        disabled={toggling}
        aria-pressed={visibility === 'public'}
        aria-label={visibility === 'public' ? '设为私有' : '设为公开'}
      >
        {toggling ? '处理中…' : visibility === 'public' ? '设为私有' : '设为公开'}
      </button>
      {errorMsg ? <p className="error">{errorMsg}</p> : null}
      <div className="share-control__token">
        <div className="share-control__token-head">
          <span className="muted">匿名定向分享</span>
          {activeLink ? (
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => void flashCopied(activeLink.url)}
              aria-label="复制分享链接"
            >
              {copied ? '已复制' : '复制链接'}
            </button>
          ) : (
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => void onCreateLink()}
              disabled={createTokenMut.isPending}
            >
              {createTokenMut.isPending ? '生成中…' : '生成链接'}
            </button>
          )}
        </div>
        {activeLink ? (
          <div className="share-control__token-box">
            <code className="share-control__token-url">{activeLink.url}</code>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => void onRevokeLink()}
              disabled={revokeTokenMut.isPending}
            >
              {revokeTokenMut.isPending ? '吊销中…' : '吊销'}
            </button>
          </div>
        ) : (
          <p className="share-control__token-hint muted">
            生成一次性匿名链接，无需登录即可查看该产物（不含行内评论与反馈）。
          </p>
        )}
        {linkError ? <p className="error">{linkError}</p> : null}
      </div>
      <Drawer
        title="确认设为公开"
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
      >
        <div className="share-control__warn">
          <p>设为公开后，任何人无需登录即可读取：</p>
          <ul>
            <li>产物正文、版本、上下文快照</li>
            <li>Prompt 快照、外部溯源（task_id/trace_id 等）</li>
          </ul>
          <p className="share-control__risk">
            ⚠ 公开后无法控制阅读范围，注意 Prompt 与 external_refs 的泄露风险。
          </p>
          <div className="share-control__actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setConfirmOpen(false)}
            >
              取消
            </button>
            <button
              type="button"
              className="btn btn--primary"
              onClick={onConfirmPublic}
              disabled={toggling}
            >
              确认设为公开
            </button>
          </div>
        </div>
      </Drawer>
    </div>
  )
}
