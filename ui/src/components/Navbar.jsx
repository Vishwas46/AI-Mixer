import { NavLink } from 'react-router-dom'
import { Music, Disc3, Headphones } from 'lucide-react'
import './Navbar.css'

function Navbar() {
  return (
    <nav className="navbar glass-card">
      <div className="navbar-brand">
        <Disc3 className="brand-icon" size={28} />
        <span className="brand-text">AI-Mixer</span>
      </div>

      <div className="navbar-links">
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Music size={18} />
          <span>Library</span>
        </NavLink>
        <NavLink to="/studio" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Disc3 size={18} />
          <span>Studio</span>
        </NavLink>
        <NavLink to="/results" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Headphones size={18} />
          <span>Results</span>
        </NavLink>
      </div>
    </nav>
  )
}

export default Navbar
