import { Outlet } from 'react-router-dom'
import Drawer from '@/components/Drawer'

export default function Layout() {
  return (
    <div className="layout">
      <header className="layout__header">
        <div className="layout__brand">Aero</div>
        <div className="layout__project-selector" aria-label="project selector placeholder">
          [Project]
        </div>
        <input
          className="layout__search"
          type="search"
          aria-label="search placeholder"
          placeholder="搜索产物…"
          disabled
        />
      </header>
      <main className="layout__main">
        <Outlet />
      </main>
      <Drawer />
    </div>
  )
}
