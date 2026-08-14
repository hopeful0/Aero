import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'

export default function RequireAuth() {
  const human = useAuthStore((s) => s.human)
  if (!human) return <Navigate to="/login" replace />
  return <Outlet />
}
