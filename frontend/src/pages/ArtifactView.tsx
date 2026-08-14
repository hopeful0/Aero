import { useParams } from 'react-router-dom'

export default function ArtifactView() {
  const { artifactId } = useParams()
  return (
    <section className="page">
      <h1>产物 {artifactId}</h1>
      <p>占位：富文档渲染 + 反馈通道 + 血统面板（后续实现）。</p>
    </section>
  )
}
