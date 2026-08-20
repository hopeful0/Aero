import { useMemo, useState } from 'react'
import { useAuthStore } from '@/store/auth'
import { useAddAgentScope, useAgentScopes, useRevokeAgentScope } from '@/api/hooks'
import type { AgentRole, AgentScopeInfo } from '@/api/types'

const ROLES: AgentRole[] = ['both', 'publisher', 'consumer']
const WRITE_ROLES = new Set(['both', 'publisher'])

function resolveError(err: unknown): string {
  if (err instanceof Error) return err.message
  return '操作失败'
}

export default function ScopeManager() {
  const human = useAuthStore((s) => s.human)
  const { data: agents, isLoading } = useAgentScopes()

  if (!human) return null

  return (
    <section className="onboarding__card scope-mgmt">
      <h2 className="onboarding__card-title">③ 管理 Agent 的 Project 权限</h2>
      <p className="muted">
        查看各 Agent 已挂载的 Project 与角色，可追加或回收跨 Project 的权限。
      </p>
      {isLoading ? (
        <p className="muted">加载中…</p>
      ) : !agents || agents.length === 0 ? (
        <p className="muted">
          暂无可见的 Agent。先在上方创建 Agent，或让其他 Project 的负责人为本 Agent
          追加权限。
        </p>
      ) : (
        agents.map((agent) => <AgentScopeRow key={agent.agent_id} agent={agent} />)
      )}
    </section>
  )
}

function AgentScopeRow({ agent }: { agent: AgentScopeInfo }) {
  const [adding, setAdding] = useState(false)
  const [projectId, setProjectId] = useState('')
  const [role, setRole] = useState<string>('both')
  const [error, setError] = useState<string | null>(null)
  const addMut = useAddAgentScope(agent.agent_id)
  const revokeMut = useRevokeAgentScope(agent.agent_id)

  const writableProjects = useMemo(() => {
    const map = new Map<string, string>()
    for (const p of agent.projects) {
      if (p.current_human_role && WRITE_ROLES.has(p.current_human_role)) {
        map.set(p.project_id, p.name)
      }
    }
    return Array.from(map, ([project_id, name]) => ({ project_id, name }))
  }, [agent.projects])

  const onAdd = async () => {
    if (!projectId) {
      setError('请选择 Project')
      return
    }
    setError(null)
    try {
      await addMut.mutateAsync({ project_id: projectId, role })
      setAdding(false)
      setProjectId('')
    } catch (e) {
      setError(resolveError(e))
    }
  }

  const onRevoke = async (pid: string) => {
    setError(null)
    try {
      await revokeMut.mutateAsync({ projectId: pid })
    } catch (e) {
      setError(resolveError(e))
    }
  }

  return (
    <div className="scope-agent">
      <div className="scope-agent__head">
        <span className="scope-agent__name" title={agent.agent_id}>
          {agent.name || agent.agent_id}
        </span>
        {!agent.is_active ? (
          <span className="chip chip--vis-private">停用</span>
        ) : null}
      </div>

      {agent.projects.length === 0 ? (
        <p className="muted scope-agent__empty">该 Agent 尚未挂载任何 Project</p>
      ) : (
        <ul className="scope-agent__list">
          {agent.projects.map((p) => {
            const writable =
              p.current_human_role !== null && WRITE_ROLES.has(p.current_human_role)
            return (
              <li key={p.project_id} className="scope-agent__item">
                <div className="scope-agent__meta">
                  <span className="scope-agent__project">{p.name}</span>
                  <span className="chip chip--tag">{p.role}</span>
                  {writable ? (
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={() => onRevoke(p.project_id)}
                      disabled={revokeMut.isPending}
                    >
                      回收
                    </button>
                  ) : (
                    <span className="chip">只读</span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      {adding ? (
        <div className="scope-agent__add">
          <label className="field">
            <span>Project</span>
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">选择 Project</option>
              {writableProjects.map((p) => (
                <option key={p.project_id} value={p.project_id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>角色</span>
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <div className="scope-agent__actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={onAdd}
              disabled={addMut.isPending}
            >
              追加
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setAdding(false)}
            >
              取消
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => {
            setAdding(true)
            setError(null)
          }}
          disabled={writableProjects.length === 0}
        >
          {writableProjects.length === 0 ? '暂无可管理的 Project' : '＋ 追加 Project 权限'}
        </button>
      )}
    </div>
  )
}