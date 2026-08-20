import { useMemo } from 'react'
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { Edge, Node, NodeProps } from '@xyflow/react'
import type { LineageNode } from '@/api/types'

type ArtifactNodeData = {
  title: string
  version: number
  isCurrent: boolean
  isRoot: boolean
  [key: string]: unknown
}

type ArtifactNodeType = Node<ArtifactNodeData, 'artifact'>

const NODE_WIDTH = 200
const NODE_HEIGHT = 76
const GAP_X = 48
const GAP_Y = 56

function buildLayout(chain: LineageNode[], currentId: string) {
  const nodeMap = new Map<string, LineageNode>()
  for (const n of chain) nodeMap.set(n.artifact_id, n)

  const children = new Map<string, LineageNode[]>()
  const roots: LineageNode[] = []
  for (const n of chain) {
    const parentId = n.parent?.artifact_id
    if (parentId && nodeMap.has(parentId)) {
      const arr = children.get(parentId) ?? []
      arr.push(n)
      children.set(parentId, arr)
    } else {
      roots.push(n)
    }
  }

  const pos = new Map<string, { x: number; y: number }>()
  let leafX = 0
  const place = (node: LineageNode, depth: number) => {
    const kids = children.get(node.artifact_id) ?? []
    if (kids.length === 0) {
      pos.set(node.artifact_id, { x: leafX, y: depth * (NODE_HEIGHT + GAP_Y) })
      leafX += NODE_WIDTH + GAP_X
      return
    }
    for (const k of kids) place(k, depth + 1)
    const first = pos.get(kids[0].artifact_id)
    const last = pos.get(kids[kids.length - 1].artifact_id)
    if (!first || !last) return
    pos.set(node.artifact_id, {
      x: (first.x + last.x) / 2,
      y: depth * (NODE_HEIGHT + GAP_Y),
    })
  }
  for (const r of roots) place(r, 0)

  const nodes: ArtifactNodeType[] = chain.map((n) => {
    const p = pos.get(n.artifact_id) ?? { x: 0, y: 0 }
    return {
      id: n.artifact_id,
      type: 'artifact',
      position: p,
      data: {
        title: n.title,
        version: n.current_version,
        isCurrent: n.artifact_id === currentId,
        isRoot: !n.parent || !nodeMap.has(n.parent.artifact_id),
      },
      draggable: false,
    }
  })

  const edges: Edge[] = []
  for (const n of chain) {
    const parentId = n.parent?.artifact_id
    if (parentId && nodeMap.has(parentId)) {
      edges.push({
        id: `${parentId}->${n.artifact_id}`,
        source: parentId,
        target: n.artifact_id,
        type: 'smoothstep',
        markerEnd: { type: MarkerType.ArrowClosed },
      })
    }
  }

  return { nodes, edges }
}

function ArtifactNode({ data }: NodeProps<ArtifactNodeType>) {
  return (
    <div
      className={
        'lineage-tree__node' +
        (data.isCurrent ? ' lineage-tree__node--current' : '') +
        (data.isRoot ? ' lineage-tree__node--root' : '')
      }
    >
      <Handle type="target" position={Position.Top} isConnectable={false} />
      <div className="lineage-tree__node-title" title={data.title}>
        {data.title}
      </div>
      <div className="lineage-tree__node-meta">
        <span className="lineage-tree__ver">v{data.version}</span>
        {data.isCurrent ? (
          <span className="lineage-tree__tag">当前</span>
        ) : null}
        {data.isRoot ? (
          <span className="lineage-tree__tag lineage-tree__tag--root">root</span>
        ) : null}
      </div>
      <Handle type="source" position={Position.Bottom} isConnectable={false} />
    </div>
  )
}

const nodeTypes = { artifact: ArtifactNode }

interface LineageTreeProps {
  chain: LineageNode[]
  currentArtifactId: string
  onSelect: (artifactId: string) => void
}

export default function LineageTree({
  chain,
  currentArtifactId,
  onSelect,
}: LineageTreeProps) {
  const { nodes, edges } = useMemo(
    () => buildLayout(chain, currentArtifactId),
    [chain, currentArtifactId],
  )

  return (
    <div className="lineage-tree">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelect(node.id)}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        panOnScroll
        minZoom={0.2}
        maxZoom={1.6}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
