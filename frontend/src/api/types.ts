export interface ContextSnapshot {
  prompt_snapshot: string | null
  external_refs: Record<string, unknown> | null
  execution_trace_id: string | null
}

export interface Feedback {
  id: number
  artifact_id: string
  version_no: number
  author_human_id: string | null
  kind: FeedbackKind
  body: string | null
  inline_anchor: Record<string, unknown> | null
  created_at: string
}

export interface Artifact {
  artifact_id: string
  version: number
  title: string
  summary: string | null
  artifact_type: string | null
  tags: string[]
  creator_agent_id: string | null
  project_id: string | null
  content: string | null
  content_format: string | null
  changelog: string | null
  created_at: string
  updated_at: string | null
  visibility: 'private' | 'public'
  context?: ContextSnapshot | null
  feedback?: Feedback[]
}

export interface ArtifactListItem {
  artifact_id: string
  title: string
  summary: string | null
  current_version: number
  artifact_type: string | null
  tags: string[]
  updated_at: string
  visibility: 'private' | 'public'
}

export interface ArtifactVersion {
  version_no: number
  title: string | null
  summary: string | null
  content_format: string | null
  changelog: string | null
  created_at: string
}

export interface PublishResult {
  artifact_id: string
  version: number
  visibility: 'private' | 'public'
  web_url: string
}

export interface NewVersionResult {
  artifact_id: string
  version: number
}

export interface ForkResult {
  artifact_id: string
  version: number
  web_url: string
  parent_artifact_id: string
  parent_version_no: number
}

export type FeedbackKind = 'thumbs_up' | 'thumbs_down' | 'comment'

export interface LineageNodeVersion {
  version_no: number
  title: string | null
  created_at: string
}

export interface LineageParent {
  artifact_id: string
  version_no: number
  fork_note: string | null
}

export interface LineageNode {
  artifact_id: string
  title: string
  current_version: number
  project_id: string | null
  versions: LineageNodeVersion[]
  parent: LineageParent | null
}

export interface Project {
  project_id: string
  name: string
  created_at: string
}

export interface LoginResult {
  human_id: string
  name: string | null
}

export interface HumanRegisterResult {
  human_id: string
  name: string | null
  email: string | null
}

export interface AgentCreateResult {
  agent_id: string
  name: string | null
  owner_human_id: string
  token: string
}

export interface ArtifactListParams {
  project_id?: string
  tags?: string[]
  type?: string
  creator_agent_id?: string
  created_after?: string
  created_before?: string
  limit?: number
  offset?: number
}
