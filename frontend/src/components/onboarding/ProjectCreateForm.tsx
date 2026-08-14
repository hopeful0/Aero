import { useState } from 'react'
import { useCreateProject } from '@/api/hooks'
import { ApiError } from '@/api/client'
import type { Project } from '@/api/types'

export default function ProjectCreateForm() {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<Project | null>(null)

  const createMut = useCreateProject()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const project = await createMut.mutateAsync({ name })
      setCreated(project)
      setName('')
    } catch (err) {
      if (err instanceof ApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError('创建项目失败')
    }
  }

  const loading = createMut.isPending

  return (
    <section className="onboarding__card">
      <h2 className="onboarding__card-title">① 创建 Project</h2>
      <p className="muted">
        Project 是产物的隔离容器。先建一个项目，Agent 才能向它发布产物。
      </p>
      <form className="onboarding__form" onSubmit={onSubmit}>
        <label className="field">
          <span>名称</span>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：astro-pipeline"
          />
        </label>
        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}
        <button type="submit" className="btn btn--primary" disabled={loading}>
          {loading ? '创建中…' : '创建项目'}
        </button>
      </form>
      {created ? (
        <p className="onboarding__created">
          <span className="chip chip--ver">✓ {created.name}</span>
          <span className="meta-label">{created.project_id}</span>
        </p>
      ) : null}
    </section>
  )
}
