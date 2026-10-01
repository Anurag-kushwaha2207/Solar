import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Landing   from './pages/Landing'
import Upload    from './pages/Upload'
import Dashboard from './pages/Dashboard'
import Scheduler from './pages/Scheduler'
import Carbon    from './pages/Carbon'
import './App.css'

function Navbar() {
  const loc = useLocation()
  const isHome = loc.pathname === '/'

  return (
    <nav className={`navbar ${isHome ? 'navbar-transparent' : ''}`}>
      <div className="nav-inner">
        <NavLink to="/" className="nav-logo">
          <span className="logo-bolt">⚡</span>
          <span className="logo-name">UrjaMind</span>
        </NavLink>

        <div className="nav-links">
          <NavLink to="/upload"    className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>📥 Upload</NavLink>
          <NavLink to="/dashboard" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>📊 Dashboard</NavLink>
          <NavLink to="/scheduler" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>📅 Scheduler</NavLink>
          <NavLink to="/carbon"    className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>🌿 Carbon</NavLink>
        </div>

        <NavLink to="/upload" className="nav-cta">Get Started →</NavLink>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/"          element={<Landing />} />
        <Route path="/upload"    element={<Upload />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/scheduler" element={<Scheduler />} />
        <Route path="/carbon"    element={<Carbon />} />
      </Routes>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#0d1a2e',
            color: '#e8f4fd',
            border: '1px solid rgba(99,179,237,0.25)',
            borderRadius: '12px',
            fontSize: '14px',
          }
        }}
      />
    </BrowserRouter>
  )
}
