import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.tsx'
import Dashboard from './pages/Dashboard.tsx'
import CaseDetail from './pages/CaseDetail.tsx'
import Analytics from './pages/Analytics.tsx'
import Settings from './pages/Settings.tsx'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/cases/:id" element={<CaseDetail />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default App
