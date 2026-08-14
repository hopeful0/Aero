import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { http } from './client'
import type {
  AgentCreateResult,
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
} from './types'

const qk = {
  artifact: (id: string, version?: number) =>
    ['artifact', id, version ?? null] as const,
  artifacts: (params: ArtifactListParams) => ['artifacts', params] as const,
  versions: (id: string) => ['versions', id] as const,
  lineage: (id: string) => ['lineage', id] as const,
  feedback: (id: string) => ['feedback', id] as const,
  projects: () => ['projects'] as const,
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

export function useLineage(id: string | undefined) {
  return useQuery<LineageNode[]>({
    queryKey: qk.lineage(id ?? ''),
    queryFn: () => http.get<LineageNode[]>(`/artifacts/${id}/lineage`),
    enabled: Boolean(id),
  })
}

export function useFeedback(id: string | undefined) {
  return useQuery<Feedback[]>({
    queryKey: qk.feedback(id ?? ''),
    queryFn: () => http.get<Feedback[]>(`/artifacts/${id}/feedback`),
    enabled: Boolean(id),
  })
}

export function useProjects() {
  return useQuery<Project[]>({
    queryKey: qk.projects(),
    queryFn: () => http.get<Project[]>('/projects'),
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
      inline_anchor?: Record<string, unknown>
    }
  >({
    mutationFn: (input) =>
      http.post<Feedback>(`/artifacts/${id}/feedback`, input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.feedback(id) })
      void qc.invalidateQueries({ queryKey: qk.artifact(id) })
    },
  })
}

export type { FeedbackKind }
