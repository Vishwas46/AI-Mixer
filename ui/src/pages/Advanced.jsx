import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion as Motion } from 'framer-motion'
import { Disc3, Music2, Zap, Play } from 'lucide-react'
import TaskProgress from '../components/TaskProgress'
import { apiFetch } from '../api'
import './Advanced.css'

// Non-Sandalwood mix modes, kept available but out of the main flow.
const MODES = [
  {
    id: 'single',
    name: 'Quick Mashup',
    icon: Music2,
    description: 'Voice of song A over the music of song B — fast, no styling options',
  },
  {
    id: 'dj',
    name: 'DJ Set',
    icon: Disc3,
    description: 'One continuous mix from every analyzed song in your library',
  },
]

const DJ_STYLES = ['relaxed', 'energetic', 'pro']

function Advanced() {
  const navigate = useNavigate()
  const [songs, setSongs] = useState([])
  const [selectedMode, setSelectedMode] = useState('single')
  const [selectedSongs, setSelectedSongs] = useState([])
  const [mixStyle, setMixStyle] = useState('relaxed')
  const [taskId, setTaskId] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSongs()
  }, [])

  const fetchSongs = async () => {
    try {
      const [songsData, analysisData] = await Promise.all([
        apiFetch('/api/songs'),
        apiFetch('/api/analysis/all'),
      ])
      const analyses = analysisData.analyses || {}
      const analyzed = (songsData.songs || [])
        .map(s => ({ ...s, filename: s.name, analysis: analyses[s.name] || null }))
        .filter(s => s.analysis)
      setSongs(analyzed)
    } catch (err) {
      console.error('Failed to fetch songs:', err)
    } finally {
      setLoading(false)
    }
  }

  const toggleSongSelection = (filename) => {
    setSelectedSongs(prev => {
      if (prev.includes(filename)) {
        return prev.filter(f => f !== filename)
      }
      if (prev.length >= 2) {
        return [...prev.slice(1), filename]
      }
      return [...prev, filename]
    })
  }

  const startMashup = async () => {
    setError(null)
    try {
      let data
      if (selectedMode === 'single') {
        if (selectedSongs.length !== 2) {
          setError('Select exactly 2 songs for a quick mashup')
          return
        }
        data = await apiFetch('/api/mashup/single', {
          method: 'POST',
          body: JSON.stringify({
            songA: selectedSongs[0],
            songB: selectedSongs[1],
            output_name: `quick_mashup_${Date.now()}`,
          }),
        })
      } else {
        data = await apiFetch('/api/mashup/djset', {
          method: 'POST',
          body: JSON.stringify({ songs_dir: 'songs/', mix_style: mixStyle }),
        })
      }
      setTaskId(data.task_id)
      setResult(null)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleComplete = (task) => {
    setTaskId(null)
    if (task.status === 'completed') {
      setResult(task.result || { done: true })
    } else if (task.error) {
      setError(task.error)
    }
  }

  const currentMode = MODES.find(m => m.id === selectedMode)

  return (
    <div className="studio-page fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Advanced</h1>
          <p className="page-subtitle">
            Other mix modes — for Sandalwood mashups, use the main Sandalwood studio
          </p>
        </div>
      </div>

      {/* Mode Selection */}
      <div className="mode-selection">
        {MODES.map((mode) => {
          const Icon = mode.icon
          return (
            <Motion.button
              key={mode.id}
              className={`mode-card glass-card ${selectedMode === mode.id ? 'active' : ''}`}
              onClick={() => {
                setSelectedMode(mode.id)
                setSelectedSongs([])
                setError(null)
              }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Icon size={28} className="mode-icon" />
              <div className="mode-name">{mode.name}</div>
              <div className="mode-desc">{mode.description}</div>
            </Motion.button>
          )
        })}
      </div>

      {/* DJ Set options */}
      {selectedMode === 'dj' && (
        <div className="options-panel glass-card">
          <div className="option-group">
            <label className="option-label">
              <Zap size={16} />
              Mix style
            </label>
            <select value={mixStyle} onChange={(e) => setMixStyle(e.target.value)}>
              {DJ_STYLES.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <p className="option-hint">
            The DJ set uses every analyzed song in your library.
          </p>
        </div>
      )}

      {/* Song Selection (quick mashup only) */}
      {selectedMode === 'single' && (
        <div className="song-selection">
          <div className="section-header">
            <h2>Select Songs</h2>
            <span className="selection-count">
              {selectedSongs.length} selected (need 2 — first = voice, second = music)
            </span>
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="spinner" />
              <span>Loading analyzed songs...</span>
            </div>
          ) : songs.length === 0 ? (
            <div className="empty-state glass-card">
              <Music2 size={48} className="empty-icon" />
              <h3>No analyzed songs</h3>
              <p>Go to Library and analyze some songs first</p>
            </div>
          ) : (
            <div className="songs-grid">
              {songs.map((song) => {
                const isSelected = selectedSongs.includes(song.filename)
                const order = selectedSongs.indexOf(song.filename) + 1
                return (
                  <Motion.div
                    key={song.filename}
                    className={`song-select-card glass-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => toggleSongSelection(song.filename)}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {isSelected && (
                      <div className="selection-badge">{order === 1 ? 'Voice' : 'Music'}</div>
                    )}
                    <div className="song-select-name">{song.filename}</div>
                    <div className="song-select-meta">
                      <span>{Math.round(song.analysis.beat_grid?.tempo || song.analysis.bpm)} BPM</span>
                      <span>{song.analysis.tala?.tala_name || song.analysis.key_str || song.analysis.key}</span>
                    </div>
                  </Motion.div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="error-banner glass-card">{error}</div>
      )}

      {/* Action Button */}
      <div className="action-area">
        {taskId ? (
          <TaskProgress taskId={taskId} onComplete={handleComplete} />
        ) : result ? (
          <div className="result-card glass-card">
            <div className="result-success">
              <Zap size={24} />
              <span>Mix created successfully!</span>
            </div>
            <p className="result-info">
              Open My Mixes to listen and download
            </p>
            <button
              className="btn btn-primary"
              onClick={() => navigate('/results')}
            >
              Go to My Mixes
            </button>
          </div>
        ) : (
          <button
            className="btn btn-primary btn-large"
            onClick={startMashup}
            disabled={selectedMode === 'single' && selectedSongs.length !== 2}
          >
            <Play size={20} />
            Create {currentMode?.name}
          </button>
        )}
      </div>
    </div>
  )
}

export default Advanced
