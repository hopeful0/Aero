import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { http } from './client'
import { useAuthStore } from '@/store/auth'
import type {
  AddAgentScopeInput,
  AgentCreateResult,
  AgentScopeInfo,
  Artifact,
  ArtifactListItem,
  ArtifactListParams,
  ArtifactVersion,
  Feedback,
  FeedbackKind,
  ForkResult,
  HumanRegisterResult,
  LineageNode,
  LoginResult,
  NewVersionResult,
  Project,
  PublishResult,
  VersionBlock,
} from './types'

const qk = {
  artifact: (id: string, version?: number) =>
    ['artifact', id, version ?? null] as const,
  artifacts: (params: ArtifactListParams) => ['artifacts', params] as const,
  versions: (id: string) => ['versions', id] as const,
  blocks: (id: string, version: number) => ['blocks', id, version] as const,
  lineage: (id: string) => ['lineage', id] as const,
  feedback: (id: string, version?: number) =>
    ['feedback', id, version ?? null] as const,
  projects: () => ['projects'] as const,
  agentScopes: () => ['agentScopes'] as const,
}

export function useArtifact(id: string | undefined, version?: number) {
  return useQuery<Artifact>({
    queryKey: qk.artifact(id ?? '', version),
    queryFn: () => {
      const params: Record<string, boolean | number> = {
        include_context: true,
        include_feedback: true,
      }
      if (version) params.version = version
      return http.get<Artifact>(`/artifacts/${id}`, { params })
    },
    enabled: Boolean(id),
  })
}

export function useArtifactList(params: ArtifactListParams) {
  return useQuery<ArtifactListItem[]>({
    queryKey: qk.artifacts(params),
    queryFn: () => http.get<ArtifactListItem[]>('/artifacts', { params }),
  })
}

export function useVersions(id: string | undefined) {
  return useQuery<ArtifactVersion[]>({
    queryKey: qk.versions(id ?? ''),
    queryFn: () => http.get<ArtifactVersion[]>(`/artifacts/${id}/versions`),
    enabled: Boolean(id),
  })
}

// blocks 端点用 OptionalPrincipal：匿名可读 public 产物，前端不依赖登录态。
export function useVersionBlocks(
  id: string | undefined,
  versionNo: number | undefined,
) {
  return useQuery<VersionBlock[]>({
    queryKey: qk.blocks(id ?? '', versionNo ?? 0),
    queryFn: () =>
      http.get<VersionBlock[]>(
        `/artifacts/${id}/versions/${versionNo}/blocks`,
      ),
    enabled: Boolean(id) && typeof versionNo === 'number',
  })
}

export function useLineage(id: string | undefined) {
  const human = useAuthStore((s) => s.human)
  return useQuery<LineageNode[]>({
    queryKey: qk.lineage(id ?? ''),
    queryFn: () => http.get<LineageNode[]>(`/artifacts/${id}/lineage`),
    enabled: Boolean(id) && !!human,
  })
}

// feedback list 端点用 CurrentPrincipal：需登录。version 参数决定 migration_status
// 的计算基准（查看版本）；缺省时后端取 current_version。
export function useFeedback(id: string | undefined, version?: number) {
  const human = useAuthStore((s) => s.human)
  return useQuery<Feedback[]>({
    queryKey: qk.feedback(id ?? '', version),
    queryFn: () =>
      http.get<Feedback[]>(`/artifacts/${id}/feedback`, {
        params: version ? { version } : undefined,
      }),
    enabled: Boolean(id) && !!human,
  })
}

export function useProjects() {
  const human = useAuthStore((s) => s.human)
  return useQuery<Project[]>({
    queryKey: qk.projects(),
    queryFn: () => http.get<Project[]>('/projects'),
    enabled: !!human,
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation<
    LoginResult,
    Error,
    { email: string; password: string }
  >({
    mutationFn: (input) => http.post<LoginResult>('/auth/login', input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.projects() })
    },
  })
}

export function useRegisterHuman() {
  return useMutation<
    HumanRegisterResult,
    Error,
    { name: string; email: string; password: string }
  >({
    mutationFn: (input) =>
      http.post<HumanRegisterResult>('/humans', input),
  })
}

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation<Project, Error, { name: string }>({
    mutationFn: (input) => http.post<Project>('/projects', input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.projects() })
    },
  })
}

export function useCreateAgent() {
  return useMutation<
    AgentCreateResult,
    Error,
    {
      name: string
      owner_human_id: string
      project_id: string
      role?: string
    }
  >({
    mutationFn: (input) => http.post<AgentCreateResult>('/agents', input),
  })
}

export function usePublishArtifact() {
  return useMutation<
    PublishResult,
    Error,
    {
      project_id: string
      title: string
      summary?: string
      artifact_type?: string
      content: string
      tags?: string[]
      parent_artifact_id?: string
      context?: Record<string, unknown>
    }
  >({
    mutationFn: (input) => http.post<PublishResult>('/artifacts', input),
  })
}

export function useCreateVersion(id: string) {
  const qc = useQueryClient()
  return useMutation<
    NewVersionResult,
    Error,
    {
      base_version: number
      title?: string
      summary?: string
      content: string
      changelog?: string
      context?: Record<string, unknown>
    }
  >({
    mutationFn: (input) =>
      http.post<NewVersionResult>(`/artifacts/${id}/versions`, input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.artifact(id) })
      void qc.invalidateQueries({ queryKey: qk.versions(id) })
    },
  })
}

export function useFork(id: string) {
  return useMutation<
    ForkResult,
    Error,
    {
      new_title?: string
      content?: string
      context?: Record<string, unknown>
      from_version?: number
    }
  >({
    mutationFn: (input) => {
      const config =
        input.from_version !== undefined
          ? { params: { from_version: input.from_version } }
          : undefined
      return http.post<ForkResult>(`/artifacts/${id}/fork`, input, config)
    },
  })
}

export function useCreateFeedback(id: string) {
  const qc = useQueryClient()
  return useMutation<
    Feedback,
    Error,
    {
      kind: FeedbackKind
      body?: string
      block_id?: string
      version_no?: number
      selector?: string
    }
  >({
    mutationFn: (input) =>
      http.post<Feedback>(`/artifacts/${id}/feedback`, input),
    onSuccess: () => {
      // 前缀匹配所有 version 的 feedback 查询（整体 + 行内共用）。
      void qc.invalidateQueries({ queryKey: ['feedback', id] })
      void qc.invalidateQueries({ queryKey: qk.artifact(id) })
    },
  })
}

export function useToggleVisibility(id: string) {
  const qc = useQueryClient()
  return useMutation<
    { visibility: 'private' | 'public' },
    Error,
    { visibility: 'private' | 'public' }
  >({
    mutationFn: (input) =>
      http.patch<{ visibility: 'private' | 'public' }>(
        `/artifacts/${id}`,
        input,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['artifact', id] })
      void qc.invalidateQueries({ queryKey: ['artifacts'] })
    },
  })
}

// A-2 scope 管理
export function useAgentScopes() {
  const human = useAuthStore((s) => s.human)
  return useQuery<AgentScopeInfo[]>({
    queryKey: qk.agentScopes(),
    queryFn: () => http.get<AgentScopeInfo[]>('/agents'),
    enabled: !!human,
  })
}

export function useAddAgentScope(agentId: string) {
  const qc = useQueryClient()
  return useMutation<void, Error, AddAgentScopeInput>({
    mutationFn: (input) =>
      http.post<void>(`/agents/${agentId}/scopes`, input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.agentScopes() })
    },
  })
}

export function useRevokeAgentScope(agentId: string) {
  const qc = useQueryClient()
  return useMutation<void, Error, { projectId: string }>({
    mutationFn: ({ projectId }) =>
      http.delete<void>(`/agents/${agentId}/scopes/${projectId}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.agentScopes() })
    },
  })
}

export type { FeedbackKind }
