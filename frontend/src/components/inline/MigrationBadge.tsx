import type { MigrationStatus } from '@/api/types'

interface MigrationBadgeProps {
  status: MigrationStatus | null
}

// 行内评论迁移状态徽标。null 表示版本级评论，不渲染。
// exact: 块在新版本完全匹配；fuzzy: 路径命中且文本相似；stale: 无法定位。
export default function MigrationBadge({ status }: MigrationBadgeProps) {
  if (!status) return null
  const map: Record<MigrationStatus, { label: string; cls: string }> = {
    exact: { label: '段落匹配', cls: 'chip--mig-exact' },
    fuzzy: { label: '段落已修改', cls: 'chip--mig-fuzzy' },
    stale: { label: '段落已无法定位', cls: 'chip--mig-stale' },
  }
  const { label, cls } = map[status]
  return <span className={`chip chip--mig ${cls}`}>{label}</span>
}
