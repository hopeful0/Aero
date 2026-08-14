import { useParams } from 'react-router-dom'

export default function ProjectView() {
  const { projectId } = useParams()
  return (
    <section className="page">
      <h1>项目 {projectId}</h1>
      <p>占位：项目内产物列表（后续实现）。</p>
    </section>
  )
}
