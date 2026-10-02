import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Landing   from './pages/Landing'
import Upload    from './pages/Upload'
import Dashboard from './pages/Dashboard'
import Scheduler from './pages/Scheduler'
import Carbon    from './pages/Carbon'
import './App.css'

import { useState, useEffect } from 'react'
import { auth, loginWithGoogle, logoutUser, subscribeAuth } from './firebase'

function Navbar() {
  const loc = useLocation()
  const isHome = loc.pathname === '/'
  const [user, setUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(false)

  useEffect(() => {
    const unsub = subscribeAuth(u => setUser(u))
    return unsub
  }, [])

  const handleAuth = async () => {
    if (user) {
      await logoutUser()
      toast.success('Signed out successfully')
    } else {
      setAuthLoading(true)
      const res = await loginWithGoogle()
      setAuthLoading(false)
      if (res.success) {
        toast.success(`Welcome ${res.user.displayName || 'Plant Manager'}!`)
      } else {
        toast.error(`Sign in note: ${res.error || 'Configure Firebase API key in .env'}`)
      }
    }
  }

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

        <div style={{display:'flex', alignItems:'center', gap:'12px'}}>
          {user ? (
            <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
              {user.photoURL ? (
                <img src={user.photoURL} alt="User" style={{width:30, height:30, borderRadius:'50%'}} />
              ) : (
                <span style={{background:'rgba(59,158,255,0.2)', padding:'4px 8px', borderRadius:20, fontSize:12}}>👤</span>
              )}
              <span style={{fontSize:13, fontWeight:600, color:'var(--text)'}}>
                {user.displayName ? user.displayName.split(' ')[0] : 'Manager'}
              </span>
              <button
                onClick={handleAuth}
                style={{background:'transparent', border:'1px solid var(--border)', color:'var(--text2)', borderRadius:6, padding:'4px 8px', fontSize:11, cursor:'pointer'}}
              >
                Sign Out
              </button>
            </div>
          ) : (
            <button
              onClick={handleAuth}
              disabled={authLoading}
              style={{background:'rgba(59,158,255,0.15)', border:'1px solid rgba(59,158,255,0.3)', color:'var(--blue-light)', borderRadius:8, padding:'6px 12px', fontSize:12, fontWeight:600, cursor:'pointer', display:'flex', alignItems:'center', gap:4}}
            >
              🔥 {authLoading ? 'Connecting...' : 'Firebase Login'}
            </button>
          )}
          <NavLink to="/upload" className="nav-cta">Get Started →</NavLink>
        </div>
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
