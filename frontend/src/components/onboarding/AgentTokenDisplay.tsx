import { useEffect, useRef, useState } from 'react'
import Drawer from '@/components/Drawer'
import type { AgentCreateResult } from '@/api/types'

type TokenResult = Omit<AgentCreateResult, 'token'> & { token: string | null }

interface Props {
  result: TokenResult | null
  projectId?: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onReset?: () => void
}

const SAFETY_WARN =
  '此 token 仅显示一次，关闭后无法再取；请立即复制并保存到你 Agent 客户端的配置中；切勿泄露。'

export default function AgentTokenDisplay({
  result,
  projectId,
  open,
  onOpenChange,
  onReset,
}: Props) {
  const [copyState, setCopyState] = useState<'idle' | 'ok' | 'err'>('idle')
  const [projectIdCopyState, setProjectIdCopyState] = useState<
    'idle' | 'ok' | 'err'
  >('idle')
  const timer = useRef<number | null>(null)
  const projectIdTimer = useRef<number | null>(null)

  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current)
      if (projectIdTimer.current) window.clearTimeout(projectIdTimer.current)
    },
    [],
  )

  const onCopy = async () => {
    const token = result?.token
    if (!token) return
    try {
      if (!navigator.clipboard) {
        setCopyState('err')
        return
      }
      await navigator.clipboard.writeText(token)
      setCopyState('ok')
      if (timer.current) window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setCopyState('idle'), 2000)
    } catch {
      setCopyState('err')
    }
  }

  const onCopyProjectId = async () => {
    const id = projectId
    if (!id) return
    try {
      if (!navigator.clipboard) {
        setProjectIdCopyState('err')
        return
      }
      await navigator.clipboard.writeText(id)
      setProjectIdCopyState('ok')
      if (projectIdTimer.current) window.clearTimeout(projectIdTimer.current)
      projectIdTimer.current = window.setTimeout(
        () => setProjectIdCopyState('idle'),
        2000,
      )
    } catch {
      setProjectIdCopyState('err')
    }
  }

  const tokenVisible = open && Boolean(result?.token)
  const showFallback = Boolean(result) && !open

  const copyLabel =
    copyState === 'ok'
      ? '已复制 ✓'
      : copyState === 'err'
        ? '复制失败'
        : '复制 Token'

  return (
    <>
      <Drawer
        title="Agent Token（仅显示一次）"
        open={open}
        onOpenChange={onOpenChange}
      >
        {result ? (
          <div className="token">
            <p className="token__warn">{SAFETY_WARN}</p>
            <div className="token__meta">
              <div className="token__meta-row">
                <span className="meta-label">Agent ID</span>
                <code>{result.agent_id}</code>
              </div>
              <div className="token__meta-row">
                <span className="meta-label">Name</span>
                <span>{result.name ?? '—'}</span>
              </div>
              <div className="token__meta-row">
                <span className="meta-label">Owner</span>
                <code>{result.owner_human_id}</code>
              </div>
              {projectId ? (
                <div className="token__meta-row">
                  <span className="meta-label">Project ID</span>
                  <code>{projectId}</code>
                  <button
                    type="button"
                    className={
                      'token__id-copy' +
                      (projectIdCopyState === 'ok'
                        ? ' token__id-copy--ok'
                        : '') +
                      (projectIdCopyState === 'err'
                        ? ' token__id-copy--err'
                        : '')
                    }
                    onClick={onCopyProjectId}
                    aria-label="复制 Project ID"
                  >
                    {projectIdCopyState === 'ok'
                      ? '已复制 ✓'
                      : projectIdCopyState === 'err'
                        ? '失败'
                        : '复制'}
                  </button>
                </div>
              ) : null}
            </div>
            {tokenVisible ? (
              <pre className="token__value">{result.token}</pre>
            ) : (
              <p className="muted">Token 已离开展示区。</p>
            )}
            <div className="token__actions">
              <button
                type="button"
                className="btn btn--primary"
                onClick={onCopy}
                disabled={!tokenVisible}
                aria-label="复制 Agent Token"
              >
                {copyLabel}
              </button>
              <span
                className={
                  'token__copy-feedback' +
                  (copyState === 'ok' ? ' token__copy-feedback--ok' : '') +
                  (copyState === 'err' ? ' token__copy-feedback--err' : '')
                }
                aria-live="polite"
              >
                {copyState === 'err'
                  ? '复制失败，请手动选择 token 文本复制。'
                  : ''}
              </span>
            </div>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => onOpenChange(false)}
            >
              我已保存，关闭
            </button>
          </div>
        ) : null}
      </Drawer>

      {showFallback && result ? (
        <div className="token__dismissed">
          <p>
            ✓ Agent 已创建：<strong>{result.name ?? '—'}</strong>{' '}
            <code>{result.agent_id}</code>
          </p>
          <p className="token__dismissed-warn">
            Token 已离开展示区。后端不再存储 token 原文（仅存 hash），无法再次获取。如需新 token，请新建 Agent。
          </p>
          {onReset ? (
            <button
              type="button"
              className="btn btn--ghost"
              onClick={onReset}
            >
              重新建 Agent
            </button>
          ) : null}
        </div>
      ) : null}
    </>
  )
}
