import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Library from './pages/Library'
import Advanced from './pages/Advanced'
import SandalwoodStudio from './pages/SandalwoodStudio'
import Results from './pages/Results'
import './App.css'

function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<SandalwoodStudio />} />
          <Route path="/library" element={<Library />} />
          <Route path="/results" element={<Results />} />
          <Route path="/advanced" element={<Advanced />} />
          {/* Legacy routes */}
          <Route path="/sandalwood" element={<Navigate to="/" replace />} />
          <Route path="/studio" element={<Navigate to="/advanced" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
