import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useProjects } from '@/api/hooks'
import ProjectCreateForm from '@/components/onboarding/ProjectCreateForm'
import AgentCreateForm from '@/components/onboarding/AgentCreateForm'
import AgentTokenDisplay from '@/components/onboarding/AgentTokenDisplay'
import type { AgentCreateResult } from '@/api/types'

type CreatedAgent = Omit<AgentCreateResult, 'token'> & {
  token: string | null
}

export default function Onboarding() {
  const { data: projects } = useProjects()

  const [createdAgent, setCreatedAgent] = useState<CreatedAgent | null>(null)
  const [createdProjectId, setCreatedProjectId] = useState<string | null>(null)
  const [tokenOpen, setTokenOpen] = useState(false)

  const handleAgentCreated = (result: AgentCreateResult, projectId: string) => {
    setCreatedAgent(result)
    setCreatedProjectId(projectId)
    setTokenOpen(true)
  }

  const handleTokenOpenChange = (open: boolean) => {
    setTokenOpen(open)
    if (!open) {
      setCreatedAgent((prev) => (prev ? { ...prev, token: null } : prev))
    }
  }

  const handleReset = () => {
    setCreatedAgent(null)
    const el = document.getElementById('onboarding-agent')
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const step1Done = (projects?.length ?? 0) > 0
  const step2Done = Boolean(createdAgent)

  return (
    <section className="page onboarding">
      <div className="onboarding__head">
        <h1>引导：配置你的 Agent 客户端</h1>
        <p className="onboarding__sub">
          完成三步即可让 Agent 通过 API 发布 / 检索产物。
        </p>
      </div>

      <ol className="onboarding__steps" aria-label="引导步骤">
        <li
          className={
            'onboarding__step' + (step1Done ? ' onboarding__step--done' : '')
          }
        >
          ① 创建 Project {step1Done ? '✓' : ''}
        </li>
        <li
          className={
            'onboarding__step' + (step2Done ? ' onboarding__step--done' : '')
          }
        >
          ② 创建 Agent {step2Done ? '✓' : ''}
        </li>
        <li
          className={
            'onboarding__step' + (step2Done ? ' onboarding__step--done' : '')
          }
        >
          ③ 获取 Token {step2Done ? '✓' : '—'}
        </li>
      </ol>

      <div className="onboarding__grid">
        <ProjectCreateForm />
        <AgentCreateForm onCreated={handleAgentCreated} />
      </div>

      <AgentTokenDisplay
        result={createdAgent}
        projectId={createdProjectId}
        open={tokenOpen}
        onOpenChange={handleTokenOpenChange}
        onReset={handleReset}
      />

      <div className="onboarding__actions">
        <Link className="btn btn--ghost" to="/">
          返回广场
        </Link>
      </div>
    </section>
  )
}
