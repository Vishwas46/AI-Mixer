import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Library from './pages/Library'
import Studio from './pages/Studio'
import Results from './pages/Results'
import './App.css'

function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Library />} />
          <Route path="/studio" element={<Studio />} />
          <Route path="/results" element={<Results />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
