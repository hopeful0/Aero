import { useNavigate } from 'react-router-dom'
import Drawer from '@/components/Drawer'
import { useLineage } from '@/api/hooks'
import LineageTree from './LineageTree'

interface LineageDrawerProps {
  artifactId: string
  creatorAgentId?: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function LineageDrawer({
  artifactId,
  creatorAgentId,
  open,
  onOpenChange,
}: LineageDrawerProps) {
  const { data: chain, isLoading, error } = useLineage(open ? artifactId : undefined)
  const navigate = useNavigate()

  const handleSelect = (id: string) => {
    onOpenChange(false)
    navigate(`/artifacts/${id}`)
  }

  return (
    <Drawer
      title="血统面板"
      description="源 Agent · fork 演进树"
      open={open}
      onOpenChange={onOpenChange}
    >
      <section className="lineage">
        <h3 className="lineage__heading">源 Agent</h3>
        <p className="lineage__value">
          {creatorAgentId ?? '—'}
        </p>

        <h3 className="lineage__heading">fork 演进树</h3>
        {isLoading ? (
          <p className="lineage__muted">加载中…</p>
        ) : error ? (
          <p className="lineage__error">
            {error instanceof Error ? error.message : '加载失败'}
          </p>
        ) : chain && chain.length > 0 ? (
          <LineageTree
            key={artifactId}
            chain={chain}
            currentArtifactId={artifactId}
            onSelect={handleSelect}
          />
        ) : (
          <p className="lineage__muted">无 lineage 数据</p>
        )}
        <p className="lineage__hint">
          根节点为源产物，自上而下为 fork 演进链路（向上祖先、向下后代），当前产物高亮显示。点击节点可跳转。
        </p>
      </section>
    </Drawer>
  )
}
