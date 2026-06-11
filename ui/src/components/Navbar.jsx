import { NavLink } from 'react-router-dom'
import { Music, Disc3, Headphones, Radio, SlidersHorizontal } from 'lucide-react'
import './Navbar.css'

function Navbar() {
  return (
    <nav className="navbar glass-card">
      <NavLink to="/" className="navbar-brand">
        <Disc3 className="brand-icon" size={28} />
        <span className="brand-text">Sandalwood AI Mixer</span>
      </NavLink>

      <div className="navbar-links">
        <NavLink to="/" className={({ isActive }) => `nav-link sandalwood-link ${isActive ? 'active' : ''}`} end>
          <Radio size={18} />
          <span>Sandalwood</span>
        </NavLink>
        <NavLink to="/library" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Music size={18} />
          <span>Library</span>
        </NavLink>
        <NavLink to="/results" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Headphones size={18} />
          <span>My Mixes</span>
        </NavLink>
        <NavLink to="/advanced" className={({ isActive }) => `nav-link nav-link-secondary ${isActive ? 'active' : ''}`}>
          <SlidersHorizontal size={16} />
          <span>Advanced</span>
        </NavLink>
      </div>
    </nav>
  )
}

export default Navbar
