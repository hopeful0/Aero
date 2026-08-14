import { useNavigate } from 'react-router-dom'
import Drawer from '@/components/Drawer'
import { useLineage } from '@/api/hooks'
import type { LineageNode } from '@/api/types'

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

  return (
    <Drawer
      title="血统面板"
      description="源 Agent · 上游 lineage · 上下文快照"
      open={open}
      onOpenChange={onOpenChange}
    >
      <section className="lineage">
        <h3 className="lineage__heading">源 Agent</h3>
        <p className="lineage__value">
          {creatorAgentId ?? '—'}
        </p>

        <h3 className="lineage__heading">上游 lineage 树</h3>
        {isLoading ? (
          <p className="lineage__muted">加载中…</p>
        ) : error ? (
          <p className="lineage__error">
            {error instanceof Error ? error.message : '加载失败'}
          </p>
        ) : chain && chain.length > 0 ? (
          <ol className="lineage__chain">
            {chain.map((node: LineageNode, idx) => (
              <li
                key={node.artifact_id}
                className={
                  'lineage__node' +
                  (idx === 0 ? ' lineage__node--current' : '')
                }
              >
                <button
                  type="button"
                  className="lineage__node-title"
                  onClick={() => navigate(`/artifacts/${node.artifact_id}`)}
                >
                  {node.title} <span className="lineage__ver">v{node.current_version}</span>
                </button>
                {node.parent ? (
                  <span className="lineage__parent">
                    ← forked from {node.parent.artifact_id} (v{node.parent.version_no})
                  </span>
                ) : (
                  <span className="lineage__root">[root]</span>
                )}
                <ul className="lineage__versions">
                  {node.versions.map((v) => (
                    <li key={v.version_no}>
                      v{v.version_no}
                      {v.title ? ` · ${v.title}` : ''}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        ) : (
          <p className="lineage__muted">无 lineage 数据</p>
        )}
      </section>
    </Drawer>
  )
}
