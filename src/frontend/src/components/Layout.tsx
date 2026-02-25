import { Outlet, Link } from 'react-router-dom'

function Layout() {
  return (
    <div>
      <nav>
        <Link to="/">Dashboard</Link>
        <Link to="/analytics">Analytics</Link>
        <Link to="/settings">Settings</Link>
      </nav>
      <main>
        <Outlet />
      </main>
    </div>
  )
}

export default Layout
