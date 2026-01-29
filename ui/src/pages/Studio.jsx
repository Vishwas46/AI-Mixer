import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Disc3, Music2, Zap, Globe, Play, Settings, Clock, Shuffle } from 'lucide-react'
import TaskProgress from '../components/TaskProgress'
import './Studio.css'

const MODES = [
  {
    id: 'single',
    name: 'Single Mashup',
    icon: Music2,
    description: 'Blend two songs together into one seamless mix',
    endpoint: '/api/mashup/single',
  },
  {
    id: 'dj',
    name: 'DJ Set',
    icon: Disc3,
    description: 'Create a continuous mix from multiple songs',
    endpoint: '/api/mashup/djset',
  },
  {
    id: 'sandalwood',
    name: 'Sandalwood Mix',
    icon: Globe,
    description: 'Kannada-optimized mashup with Anand Audio style',
    endpoint: '/api/mashup/sandalwood',
  },
]

const STYLES = ['energetic', 'smooth', 'build-up', 'chill']

function Studio() {
  const [songs, setSongs] = useState([])
  const [selectedMode, setSelectedMode] = useState('single')
  const [selectedSongs, setSelectedSongs] = useState([])
  const [style, setStyle] = useState('energetic')
  const [duration, setDuration] = useState(15)
  const [taskId, setTaskId] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSongs()
  }, [])

  const fetchSongs = async () => {
    try {
      const res = await fetch('/api/songs')
      const data = await res.json()
      // Filter to only analyzed songs
      const analyzed = (data.songs || []).filter(s => s.analysis)
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
      // For single mashup, limit to 2 songs
      if (selectedMode === 'single' && prev.length >= 2) {
        return [...prev.slice(1), filename]
      }
      return [...prev, filename]
    })
  }

  const startMashup = async () => {
    const mode = MODES.find(m => m.id === selectedMode)
    if (!mode) return

    let body = {}
    if (selectedMode === 'single') {
      if (selectedSongs.length < 2) {
        alert('Select 2 songs for a single mashup')
        return
      }
      body = { song1: selectedSongs[0], song2: selectedSongs[1] }
    } else if (selectedMode === 'dj') {
      if (selectedSongs.length < 2) {
        alert('Select at least 2 songs for a DJ set')
        return
      }
      body = { songs: selectedSongs, target_duration: duration }
    } else if (selectedMode === 'sandalwood') {
      if (selectedSongs.length < 2) {
        alert('Select at least 2 songs for a Sandalwood mix')
        return
      }
      body = { songs: selectedSongs, style, duration_minutes: duration }
    }

    try {
      const res = await fetch(mode.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      setTaskId(data.task_id)
      setResult(null)
    } catch (err) {
      console.error('Mashup failed:', err)
    }
  }

  const handleComplete = (task) => {
    setTaskId(null)
    if (task.status === 'completed' && task.result) {
      setResult(task.result)
    }
  }

  const currentMode = MODES.find(m => m.id === selectedMode)

  return (
    <div className="studio-page fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Mixing Studio</h1>
          <p className="page-subtitle">Create your perfect mashup</p>
        </div>
      </div>

      {/* Mode Selection */}
      <div className="mode-selection">
        {MODES.map((mode) => {
          const Icon = mode.icon
          return (
            <motion.button
              key={mode.id}
              className={`mode-card glass-card ${selectedMode === mode.id ? 'active' : ''}`}
              onClick={() => {
                setSelectedMode(mode.id)
                setSelectedSongs([])
              }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Icon size={28} className="mode-icon" />
              <div className="mode-name">{mode.name}</div>
              <div className="mode-desc">{mode.description}</div>
            </motion.button>
          )
        })}
      </div>

      {/* Options */}
      {(selectedMode === 'dj' || selectedMode === 'sandalwood') && (
        <div className="options-panel glass-card">
          <div className="option-group">
            <label className="option-label">
              <Clock size={16} />
              Duration (minutes)
            </label>
            <input
              type="number"
              min="5"
              max="60"
              value={duration}
              onChange={(e) => setDuration(parseInt(e.target.value) || 15)}
            />
          </div>

          {selectedMode === 'sandalwood' && (
            <div className="option-group">
              <label className="option-label">
                <Zap size={16} />
                Style
              </label>
              <select value={style} onChange={(e) => setStyle(e.target.value)}>
                {STYLES.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Song Selection */}
      <div className="song-selection">
        <div className="section-header">
          <h2>Select Songs</h2>
          <span className="selection-count">
            {selectedSongs.length} selected
            {selectedMode === 'single' && ' (need 2)'}
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
                <motion.div
                  key={song.filename}
                  className={`song-select-card glass-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => toggleSongSelection(song.filename)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {isSelected && (
                    <div className="selection-badge">{order}</div>
                  )}
                  <div className="song-select-name">{song.filename}</div>
                  <div className="song-select-meta">
                    <span>{Math.round(song.analysis.beat_grid?.tempo || song.analysis.bpm)} BPM</span>
                    <span>{song.analysis.tala?.primary_tala || song.analysis.key}</span>
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}
      </div>

      {/* Action Button */}
      <div className="action-area">
        {taskId ? (
          <TaskProgress taskId={taskId} onComplete={handleComplete} />
        ) : result ? (
          <div className="result-card glass-card">
            <div className="result-success">
              <Zap size={24} />
              <span>Mashup created successfully!</span>
            </div>
            <p className="result-info">
              Check the Results page to listen to your mix
            </p>
            <button
              className="btn btn-primary"
              onClick={() => window.location.href = '/results'}
            >
              Go to Results
            </button>
          </div>
        ) : (
          <button
            className="btn btn-primary btn-large"
            onClick={startMashup}
            disabled={
              selectedSongs.length < 2 ||
              (selectedMode === 'single' && selectedSongs.length !== 2)
            }
          >
            <Play size={20} />
            Create {currentMode?.name}
          </button>
        )}
      </div>
    </div>
  )
}

export default Studio
