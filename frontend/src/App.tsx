import { Route, Routes } from 'react-router-dom'
import Layout from '@/components/Layout'
import Health from '@/pages/Health'
import Login from '@/pages/Login'
import Square from '@/pages/Square'
import ProjectView from '@/pages/ProjectView'
import ArtifactView from '@/pages/ArtifactView'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Square />} />
        <Route path="/health" element={<Health />} />
        <Route path="/login" element={<Login />} />
        <Route path="/projects/:projectId" element={<ProjectView />} />
        <Route path="/artifacts/:artifactId" element={<ArtifactView />} />
      </Route>
    </Routes>
  )
}
