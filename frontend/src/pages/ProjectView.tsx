import { useParams } from 'react-router-dom'

export default function ProjectView() {
  const { projectId } = useParams()
  return (
    <section className="page">
      <h1>项目 {projectId}</h1>
      <p className="muted">该视图合并至产物广场（带 project_id 过滤）。</p>
    </section>
  )
}
