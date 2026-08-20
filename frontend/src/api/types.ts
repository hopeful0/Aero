export interface ContextSnapshot {
  prompt_snapshot: string | null
  external_refs: Record<string, unknown> | null
  execution_trace_id: string | null
}

// 行内评论锚点快照：创建评论时从 block 记录锁定，供 list_feedback 在线计算 migration_status。
export interface InlineAnchor {
  block_id: string
  block_path: string
  block_text: string
  selector: string | null
  version_no: number
}

// 行内评论迁移状态：以查看版本的 block map 为基准在线计算（不持久化）。
// exact: 块完全匹配；fuzzy: 路径命中且文本相似；stale: 无法定位；null: 版本级评论。
export type MigrationStatus = 'exact' | 'fuzzy' | 'stale'

export interface Feedback {
  id: number
  artifact_id: string
  version_no: number
  author_human_id: string | null
  kind: FeedbackKind
  body: string | null
  inline_anchor: InlineAnchor | null
  migration_status: MigrationStatus | null
  created_at: string
}

// 版本块映射：后端是 block_id 的权威源，前端只按 block_index 注入 DOM。
export interface VersionBlock {
  block_id: string
  block_path: string
  block_index: number
  block_text: string
  content_preview: string
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

// A-2 scope 管理：agent↔project 授予/回收
export interface AgentScopeProject {
  project_id: string
  name: string
  role: string
  current_human_role: string | null
}

export interface AgentScopeInfo {
  agent_id: string
  name: string | null
  owner_human_id: string
  is_active: boolean
  projects: AgentScopeProject[]
}

export interface AddAgentScopeInput {
  project_id: string
  role: string
}

export type AgentRole = 'publisher' | 'consumer' | 'both'

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
