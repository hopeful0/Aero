import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from '@/components/Layout'
import RequireAuth from '@/components/RequireAuth'
import Health from '@/pages/Health'
import Login from '@/pages/Login'
import Square from '@/pages/Square'
import Onboarding from '@/pages/Onboarding'
import ProjectView from '@/pages/ProjectView'
import ArtifactView from '@/pages/ArtifactView'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/health" element={<Health />} />

      <Route element={<Layout />}>
        <Route path="/" element={<Square />} />
        <Route path="/artifacts/:artifactId" element={<ArtifactView />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/projects/:projectId" element={<ProjectView />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
