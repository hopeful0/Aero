import { useEffect, useState } from 'react'
import { useAuthStore } from '@/store/auth'
import { useCreateAgent, useProjects } from '@/api/hooks'
import { ApiError } from '@/api/client'
import type { AgentCreateResult } from '@/api/types'

const ROLES = ['both', 'publisher', 'consumer'] as const

interface Props {
  onCreated: (result: AgentCreateResult, projectId: string) => void
}

function resolveAgentError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === 'BAD_REQUEST') {
      const details = err.details as Record<string, unknown> | undefined
      const msgHasScope = err.message.toLowerCase().includes('scope')
      const detailsHit =
        details &&
        ('owner_human_id' in details || 'project_id' in details)
      if (msgHasScope || detailsHit) {
        return 'Owner 需先拥有该项目的权限（scope）。M1 默认 owner=自己，请确认你已对该项目有访问权限。'
      }
      return err.message
    }
    if (err.code === 'FORBIDDEN') return '你没有该项目的访问权限。'
    if (err.status === 0 || err.code === 'UNKNOWN')
      return '网络错误，请检查连接后重试。'
    if (err.code === 'UNAUTHORIZED') return '登录已失效，请重新登录。'
    return err.message
  }
  if (err instanceof Error) return err.message
  return '操作失败'
}

export default function AgentCreateForm({ onCreated }: Props) {
  const human = useAuthStore((s) => s.human)
  const { data: projects, isLoading: projectsLoading } = useProjects()
  const createMut = useCreateAgent()

  const [name, setName] = useState('')
  const [projectId, setProjectId] = useState('')
  const [role, setRole] = useState<string>('both')
  const [error, setError] = useState<string | null>(null)

  const noProjects = !projects || projects.length === 0

  useEffect(() => {
    if (!projectId && projects && projects.length > 0) {
      setProjectId(projects[0].project_id)
    }
  }, [projects, projectId])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!human || !projectId) return
    setError(null)
    try {
      const result = await createMut.mutateAsync({
        name,
        owner_human_id: human.humanId,
        project_id: projectId,
        role,
      })
      onCreated(result, projectId)
      setName('')
    } catch (err) {
      setError(resolveAgentError(err))
    }
  }

  const loading = createMut.isPending

  return (
    <section className="onboarding__card" id="onboarding-agent">
      <h2 className="onboarding__card-title">② 创建 Agent</h2>
      <p className="muted">
        Agent 通过 Bearer Token 走 API 发布/检索产物。创建后立即展示一次性 Token。
      </p>
      <form className="onboarding__form" onSubmit={onSubmit}>
        <label className="field">
          <span>项目</span>
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            disabled={noProjects}
          >
            <option value="">
              {projectsLoading
                ? '加载中…'
                : noProjects
                  ? '请先在左侧创建 Project'
                  : '选择项目'}
            </option>
            {projects?.map((p) => (
              <option key={p.project_id} value={p.project_id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>名称</span>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：designer-agent"
          />
        </label>
        <label className="field">
          <span>角色</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            aria-label="agent role"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <p className="onboarding__owner">
          Owner = {human?.name ?? human?.humanId ?? '—'}（你自己，默认绑定）
        </p>
        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          className="btn btn--primary"
          disabled={loading || noProjects || !projectId}
        >
          {loading ? '创建中…' : '创建 Agent'}
        </button>
      </form>
    </section>
  )
}
