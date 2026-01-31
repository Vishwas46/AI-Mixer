import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload, Music, Sparkles, Play, Loader, Check,
  ArrowRight, Info, Zap, Heart, Clock, Volume2,
  ChevronDown, X, Download, Disc3, ListMusic, Mic2
} from 'lucide-react'
import AudioPlayer from '../components/AudioPlayer'
import CompatibilityGraph from '../components/CompatibilityGraph'
import './Home.css'

// Mashup modes with friendly descriptions
const MASHUP_MODES = [
  {
    id: 'quick',
    name: 'Quick Mashup',
    icon: Zap,
    desc: 'Best 2 songs blended together',
    minSongs: 2,
  },
  {
    id: 'djset',
    name: 'DJ Set',
    icon: Disc3,
    desc: 'All songs mixed into one continuous track',
    minSongs: 3,
    styles: [
      { id: 'relaxed', name: 'Relaxed', desc: 'Smooth, gentle transitions' },
      { id: 'energetic', name: 'Energetic', desc: 'High-energy, punchy drops' },
      { id: 'pro', name: 'Pro Mix', desc: 'Complex, DJ-style blends' },
    ]
  },
  {
    id: 'kannada',
    name: 'Kannada/Sandalwood',
    icon: Mic2,
    desc: 'Optimized for Indian film music with Tala detection',
    minSongs: 2,
    styles: [
      { id: 'energetic', name: 'Energetic', desc: 'High-energy dance mashup' },
      { id: 'smooth', name: 'Smooth', desc: 'Melodic, flowing transitions' },
      { id: 'showcase', name: 'Showcase', desc: 'Highlight each song\'s best parts' },
    ],
    hasDuration: true
  }
]

function Home() {
  const navigate = useNavigate()
  const [songs, setSongs] = useState([])
  const [selectedMode, setSelectedMode] = useState('quick')
  const [selectedStyle, setSelectedStyle] = useState('energetic')
  const [duration, setDuration] = useState(10)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisProgress, setAnalysisProgress] = useState({ current: 0, total: 0, stage: '' })
  const [analysisResults, setAnalysisResults] = useState(null)
  const [bestMashup, setBestMashup] = useState(null)
  const [creatingMashup, setCreatingMashup] = useState(false)
  const [mashupProgress, setMashupProgress] = useState({ percent: 0, stage: '' })
  const [mashupResult, setMashupResult] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState(null)

  const currentMode = MASHUP_MODES.find(m => m.id === selectedMode)

  // Fetch existing songs on mount
  useEffect(() => {
    fetchExistingSongs()
  }, [])

  // Reset style when mode changes
  useEffect(() => {
    if (currentMode?.styles) {
      setSelectedStyle(currentMode.styles[0].id)
    }
  }, [selectedMode])

  const fetchExistingSongs = async () => {
    try {
      const res = await fetch('/api/songs')
      const data = await res.json()
      if (data.songs) {
        const existingSongs = data.songs.map(s => ({
          name: s.filename,
          status: s.analyzed ? 'analyzed' : 'ready',
          analysis: s.analyzed ? s.analysis : null
        }))
        setSongs(existingSongs)
      }
    } catch (err) {
      console.error('Failed to fetch songs:', err)
    }
  }

  const handleDrop = useCallback(async (e) => {
    e.preventDefault()
    setDragOver(false)
    setError(null)

    const files = Array.from(e.dataTransfer.files).filter(f =>
      f.type.startsWith('audio/') || f.name.endsWith('.mp3') || f.name.endsWith('.wav')
    )

    if (files.length === 0) {
      setError('Please drop audio files (MP3 or WAV)')
      return
    }

    const newSongs = files.map(f => ({ name: f.name, status: 'uploading', file: f }))
    setSongs(prev => [...prev, ...newSongs])

    for (const song of newSongs) {
      try {
        const formData = new FormData()
        formData.append('file', song.file)

        const res = await fetch('/api/songs/upload', { method: 'POST', body: formData })
        if (!res.ok) throw new Error('Upload failed')

        setSongs(prev => prev.map(s =>
          s.name === song.name ? { ...s, status: 'ready' } : s
        ))
      } catch (err) {
        setSongs(prev => prev.map(s =>
          s.name === song.name ? { ...s, status: 'error', error: err.message } : s
        ))
      }
    }
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragOver(false)
  }, [])

  const removeSong = (name) => {
    setSongs(prev => prev.filter(s => s.name !== name))
    setAnalysisResults(null)
    setBestMashup(null)
    setMashupResult(null)
  }

  // Main analysis function
  const analyzeAllSongs = async () => {
    const songsToAnalyze = songs.filter(s => s.status === 'ready' || s.status === 'analyzed')
    if (songsToAnalyze.length < currentMode.minSongs) {
      setError(`Add at least ${currentMode.minSongs} songs for ${currentMode.name}`)
      return
    }

    setAnalyzing(true)
    setError(null)
    setMashupResult(null)
    setAnalysisProgress({ current: 0, total: songsToAnalyze.length, stage: 'Starting deep analysis...' })

    const results = []

    for (let i = 0; i < songsToAnalyze.length; i++) {
      const song = songsToAnalyze[i]
      setAnalysisProgress({
        current: i + 1,
        total: songsToAnalyze.length,
        stage: `Listening to "${song.name.replace('.mp3', '')}"...`
      })

      setSongs(prev => prev.map(s =>
        s.name === song.name ? { ...s, status: 'analyzing' } : s
      ))

      try {
        const res = await fetch('/api/analyze/kannada', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: song.name })
        })
        const taskData = await res.json()

        let analysis = null
        while (true) {
          await new Promise(r => setTimeout(r, 1000))
          const statusRes = await fetch(`/api/tasks/${taskData.task_id}`)
          const status = await statusRes.json()

          if (status.status === 'completed') {
            analysis = status.result
            break
          } else if (status.status === 'failed') {
            throw new Error(status.error || 'Analysis failed')
          }

          if (status.log && status.log.length > 0) {
            const lastLog = status.log[status.log.length - 1]
            if (lastLog.includes('beat')) {
              setAnalysisProgress(prev => ({ ...prev, stage: `Finding the rhythm...` }))
            } else if (lastLog.includes('vocal')) {
              setAnalysisProgress(prev => ({ ...prev, stage: `Detecting vocals...` }))
            } else if (lastLog.includes('tala')) {
              setAnalysisProgress(prev => ({ ...prev, stage: `Detecting Tala pattern...` }))
            } else if (lastLog.includes('scale')) {
              setAnalysisProgress(prev => ({ ...prev, stage: `Analyzing musical scale...` }))
            }
          }
        }

        results.push({ ...song, analysis, status: 'analyzed' })
        setSongs(prev => prev.map(s =>
          s.name === song.name ? { ...s, status: 'analyzed', analysis } : s
        ))

      } catch (err) {
        console.error(`Failed to analyze ${song.name}:`, err)
        setSongs(prev => prev.map(s =>
          s.name === song.name ? { ...s, status: 'error', error: err.message } : s
        ))
      }
    }

    setAnalysisProgress({ current: songsToAnalyze.length, total: songsToAnalyze.length, stage: 'Finding the perfect combinations...' })

    const analyzedSongs = results.filter(s => s.analysis)
    if (analyzedSongs.length >= 2) {
      const compatibilityData = calculateCompatibility(analyzedSongs)
      setAnalysisResults(compatibilityData)

      const bestPair = compatibilityData.connections.reduce((best, conn) =>
        conn.score > (best?.score || 0) ? conn : best
      , null)

      if (bestPair) {
        setBestMashup({
          song1: analyzedSongs.find(s => s.name === bestPair.from),
          song2: analyzedSongs.find(s => s.name === bestPair.to),
          score: bestPair.score,
          reasons: bestPair.reasons
        })
      }
    }

    setAnalyzing(false)
  }

  const calculateCompatibility = (analyzedSongs) => {
    const connections = []

    for (let i = 0; i < analyzedSongs.length; i++) {
      for (let j = i + 1; j < analyzedSongs.length; j++) {
        const s1 = analyzedSongs[i]
        const s2 = analyzedSongs[j]
        const a1 = s1.analysis
        const a2 = s2.analysis

        if (!a1 || !a2) continue

        const reasons = []
        let score = 0

        const bpm1 = a1.bpm || a1.beat_grid?.tempo || 120
        const bpm2 = a2.bpm || a2.beat_grid?.tempo || 120
        const bpmDiff = Math.abs(bpm1 - bpm2)
        const bpmRatio = Math.min(bpm1, bpm2) / Math.max(bpm1, bpm2)

        if (bpmDiff <= 3) {
          score += 30
          reasons.push({ type: 'tempo', text: 'Perfect tempo match!', good: true })
        } else if (bpmDiff <= 8) {
          score += 25
          reasons.push({ type: 'tempo', text: 'Very close tempo', good: true })
        } else if (bpmRatio > 0.48 && bpmRatio < 0.52) {
          score += 20
          reasons.push({ type: 'tempo', text: 'Half-time compatible', good: true })
        } else if (bpmDiff <= 15) {
          score += 15
          reasons.push({ type: 'tempo', text: 'Tempo can be adjusted', good: false })
        } else {
          reasons.push({ type: 'tempo', text: 'Different tempos', good: false })
        }

        const key1 = a1.key || 'C'
        const key2 = a2.key || 'C'
        const keyMatch = checkKeyCompatibility(key1, key2)
        score += keyMatch.score
        reasons.push({ type: 'key', text: keyMatch.reason, good: keyMatch.score >= 20 })

        const energy1 = a1.emotional_curve?.average_intensity || 0.5
        const energy2 = a2.emotional_curve?.average_intensity || 0.5
        const energyDiff = Math.abs(energy1 - energy2)

        if (energyDiff <= 0.15) {
          score += 20
          reasons.push({ type: 'energy', text: 'Similar energy levels', good: true })
        } else if (energyDiff <= 0.3) {
          score += 15
          reasons.push({ type: 'energy', text: 'Compatible energy', good: true })
        } else {
          score += 5
          reasons.push({ type: 'energy', text: 'Different energy - creates contrast', good: false })
        }

        const tala1 = a1.tala?.detected_tala
        const tala2 = a2.tala?.detected_tala
        if (tala1 && tala2 && tala1 === tala2) {
          score += 20
          reasons.push({ type: 'rhythm', text: `Same Tala (${tala1})`, good: true })
        } else if (a1.beat_grid?.is_tempo_stable && a2.beat_grid?.is_tempo_stable) {
          score += 15
          reasons.push({ type: 'rhythm', text: 'Both have steady beats', good: true })
        } else {
          score += 10
          reasons.push({ type: 'rhythm', text: 'Different rhythms', good: false })
        }

        connections.push({
          from: s1.name,
          to: s2.name,
          score,
          reasons,
          label: score >= 80 ? 'Perfect Match!' : score >= 60 ? 'Great Match' : score >= 40 ? 'Good Match' : 'Challenging'
        })
      }
    }

    return {
      songs: analyzedSongs,
      connections: connections.sort((a, b) => b.score - a.score)
    }
  }

  const checkKeyCompatibility = (key1, key2) => {
    const keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    const k1 = key1.replace('m', '').replace(' minor', '').replace(' major', '')
    const k2 = key2.replace('m', '').replace(' minor', '').replace(' major', '')

    if (k1 === k2) return { score: 30, reason: 'Same key - perfect harmony!' }

    const i1 = keys.indexOf(k1)
    const i2 = keys.indexOf(k2)
    if (i1 === -1 || i2 === -1) return { score: 15, reason: 'Keys detected' }

    const diff = Math.abs(i1 - i2)
    const camelotDiff = Math.min(diff, 12 - diff)

    if (camelotDiff <= 1) return { score: 28, reason: 'Adjacent keys - very harmonic' }
    if (camelotDiff === 5 || camelotDiff === 7) return { score: 25, reason: 'Relative keys - sound great together' }
    if (camelotDiff <= 2) return { score: 20, reason: 'Close keys - compatible' }
    return { score: 10, reason: 'Different keys - may need careful mixing' }
  }

  // Create mashup based on selected mode
  const createMashup = async () => {
    setCreatingMashup(true)
    setMashupProgress({ percent: 0, stage: 'Starting...' })
    setError(null)

    try {
      let endpoint, body, friendlyStages

      if (selectedMode === 'quick') {
        if (!bestMashup) {
          throw new Error('No compatible songs found')
        }
        endpoint = '/api/mashup/single'
        body = {
          songA: bestMashup.song1.name,
          songB: bestMashup.song2.name,
          output_name: `mashup_${Date.now()}`
        }
        friendlyStages = [
          'Analyzing song structures...',
          'Finding the best blend points...',
          'Matching tempos and keys...',
          'Creating smooth transitions...',
          'Polishing the final mix...'
        ]
      } else if (selectedMode === 'djset') {
        endpoint = '/api/mashup/djset'
        body = {
          songs_dir: 'songs',
          mix_style: selectedStyle
        }
        friendlyStages = [
          'Planning the setlist order...',
          'Analyzing transitions between songs...',
          `Applying ${selectedStyle} mixing style...`,
          'Creating seamless transitions...',
          'Building the continuous mix...',
          'Finalizing your DJ set...'
        ]
      } else if (selectedMode === 'kannada') {
        const analyzedSongs = songs.filter(s => s.status === 'analyzed')
        endpoint = '/api/mashup/sandalwood'
        body = {
          filenames: analyzedSongs.map(s => s.name),
          style: selectedStyle,
          duration: duration
        }
        friendlyStages = [
          'Deep analyzing Kannada music patterns...',
          'Detecting Tala and Ragam...',
          'Finding Pallavi and Charanam sections...',
          `Planning ${selectedStyle} style mashup...`,
          'Creating the perfect Sandalwood mix...',
          'Generating mashup report...'
        ]
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to start mashup')
      }

      const taskData = await res.json()
      let stageIndex = 0

      while (true) {
        await new Promise(r => setTimeout(r, 1500))
        const statusRes = await fetch(`/api/tasks/${taskData.task_id}`)
        const status = await statusRes.json()

        if (status.status === 'completed') {
          setMashupProgress({ percent: 100, stage: 'Your mashup is ready!' })
          setMashupResult({
            mode: selectedMode,
            style: selectedStyle,
            ...status.result
          })
          break
        } else if (status.status === 'failed') {
          throw new Error(status.error || 'Mashup creation failed')
        }

        const percent = Math.min(95, status.progress || (stageIndex / friendlyStages.length) * 100)
        if (percent > ((stageIndex + 1) / friendlyStages.length) * 100 && stageIndex < friendlyStages.length - 1) {
          stageIndex++
        }
        setMashupProgress({ percent, stage: friendlyStages[stageIndex] })
      }
    } catch (err) {
      setError(err.message)
    }

    setCreatingMashup(false)
  }

  const readySongs = songs.filter(s => s.status === 'ready' || s.status === 'analyzed')
  const canAnalyze = readySongs.length >= currentMode.minSongs

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="hero">
        <motion.div
          className="hero-content"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="hero-title">
            <Sparkles className="title-icon" />
            Create Amazing Mashups
          </h1>
          <p className="hero-subtitle">
            Drop your songs, pick a style, and let AI create the perfect mix
          </p>
        </motion.div>
      </section>

      {/* Drop Zone */}
      <section className="upload-section">
        <div
          className={`drop-zone glass-card ${dragOver ? 'drag-over' : ''} ${songs.length > 0 ? 'has-songs' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          {songs.length === 0 ? (
            <div className="drop-content">
              <Upload size={48} className="drop-icon" />
              <h3>Drop your songs here</h3>
              <p>MP3 or WAV files - add at least 2 songs</p>
            </div>
          ) : (
            <div className="songs-list">
              <AnimatePresence>
                {songs.map((song, i) => (
                  <motion.div
                    key={song.name}
                    className={`song-item ${song.status}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <div className="song-icon-wrapper">
                      {song.status === 'uploading' && <Loader className="spin" size={20} />}
                      {song.status === 'analyzing' && <Loader className="spin" size={20} />}
                      {song.status === 'analyzed' && <Check size={20} className="check-icon" />}
                      {(song.status === 'ready' || song.status === 'error') && <Music size={20} />}
                    </div>
                    <div className="song-info">
                      <span className="song-name">{song.name.replace('.mp3', '').replace('.wav', '')}</span>
                      {song.status === 'analyzed' && song.analysis && (
                        <span className="song-meta-mini">
                          {Math.round(song.analysis.bpm || song.analysis.beat_grid?.tempo || 0)} BPM
                          {song.analysis.key && ` • ${song.analysis.key}`}
                          {song.analysis.tala?.detected_tala && ` • ${song.analysis.tala.detected_tala}`}
                        </span>
                      )}
                      {song.status === 'analyzing' && (
                        <span className="song-meta-mini analyzing">Analyzing...</span>
                      )}
                      {song.status === 'error' && (
                        <span className="song-meta-mini error">{song.error}</span>
                      )}
                    </div>
                    <button className="remove-btn" onClick={() => removeSong(song.name)}>
                      <X size={16} />
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>

              <div className="add-more-hint">
                <Upload size={16} />
                <span>Drop more songs here</span>
              </div>
            </div>
          )}
        </div>

        {error && (
          <motion.div className="error-message" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            {error}
          </motion.div>
        )}
      </section>

      {/* Mode Selection */}
      {songs.length >= 2 && (
        <section className="mode-section">
          <h2 className="section-title">Choose Your Style</h2>
          <div className="mode-cards">
            {MASHUP_MODES.map(mode => (
              <motion.div
                key={mode.id}
                className={`mode-card glass-card ${selectedMode === mode.id ? 'active' : ''} ${readySongs.length < mode.minSongs ? 'disabled' : ''}`}
                onClick={() => readySongs.length >= mode.minSongs && setSelectedMode(mode.id)}
                whileHover={{ scale: readySongs.length >= mode.minSongs ? 1.02 : 1 }}
                whileTap={{ scale: readySongs.length >= mode.minSongs ? 0.98 : 1 }}
              >
                <mode.icon size={28} className="mode-icon" />
                <h3>{mode.name}</h3>
                <p>{mode.desc}</p>
                {readySongs.length < mode.minSongs && (
                  <span className="mode-requirement">Needs {mode.minSongs}+ songs</span>
                )}
              </motion.div>
            ))}
          </div>

          {/* Style Options */}
          {currentMode.styles && (
            <div className="style-options glass-card">
              <h3>
                {selectedMode === 'kannada' ? 'Mashup Style' : 'Mix Style'}
              </h3>
              <div className="style-buttons">
                {currentMode.styles.map(style => (
                  <button
                    key={style.id}
                    className={`style-btn ${selectedStyle === style.id ? 'active' : ''}`}
                    onClick={() => setSelectedStyle(style.id)}
                  >
                    <span className="style-name">{style.name}</span>
                    <span className="style-desc">{style.desc}</span>
                  </button>
                ))}
              </div>

              {/* Duration for Kannada mode */}
              {currentMode.hasDuration && (
                <div className="duration-option">
                  <label>
                    <Clock size={16} />
                    Target Duration
                  </label>
                  <div className="duration-input">
                    <input
                      type="range"
                      min="5"
                      max="30"
                      value={duration}
                      onChange={e => setDuration(Number(e.target.value))}
                    />
                    <span className="duration-value">{duration} minutes</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* Analysis Section */}
      {songs.length >= 2 && !analysisResults && (
        <section className="action-section">
          <motion.button
            className="btn btn-primary btn-large analyze-btn"
            onClick={analyzeAllSongs}
            disabled={analyzing || !canAnalyze}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {analyzing ? (
              <>
                <Loader className="spin" size={20} />
                {analysisProgress.stage}
              </>
            ) : (
              <>
                <Sparkles size={20} />
                Analyze Songs & Find Best Matches
              </>
            )}
          </motion.button>

          {analyzing && (
            <div className="analysis-progress-bar">
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${(analysisProgress.current / analysisProgress.total) * 100}%` }}
                />
              </div>
              <span className="progress-text">
                Song {analysisProgress.current} of {analysisProgress.total}
              </span>
            </div>
          )}
        </section>
      )}

      {/* Results Section */}
      {analysisResults && (
        <section className="results-section">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            {/* Compatibility Graph */}
            <div className="compatibility-section glass-card">
              <h2 className="section-title">
                <Heart size={20} />
                How Your Songs Connect
              </h2>
              <p className="section-desc">
                Thicker lines = better match. Hover over connections to see why.
              </p>
              <CompatibilityGraph data={analysisResults} />
            </div>

            {/* Create Mashup Button */}
            {!mashupResult ? (
              <motion.div
                className="create-mashup-card glass-card"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 }}
              >
                <div className="create-header">
                  <currentMode.icon size={32} className="create-icon" />
                  <div>
                    <h2>Ready to Create Your {currentMode.name}</h2>
                    {bestMashup && selectedMode === 'quick' && (
                      <p className="best-match-hint">
                        Best match: {bestMashup.song1.name.replace('.mp3', '')} + {bestMashup.song2.name.replace('.mp3', '')} ({bestMashup.score}%)
                      </p>
                    )}
                    {selectedMode !== 'quick' && (
                      <p className="style-hint">
                        Style: <strong>{currentMode.styles?.find(s => s.id === selectedStyle)?.name}</strong>
                        {currentMode.hasDuration && ` • ${duration} minutes`}
                      </p>
                    )}
                  </div>
                </div>

                {bestMashup && selectedMode === 'quick' && (
                  <div className="reasons-list">
                    {bestMashup.reasons.map((reason, i) => (
                      <div key={i} className={`reason-item ${reason.good ? 'good' : 'neutral'}`}>
                        {reason.good ? <Check size={16} /> : <Info size={16} />}
                        <span>{reason.text}</span>
                      </div>
                    ))}
                  </div>
                )}

                <motion.button
                  className="btn btn-primary btn-large create-btn"
                  onClick={createMashup}
                  disabled={creatingMashup}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {creatingMashup ? (
                    <>
                      <Loader className="spin" size={20} />
                      {mashupProgress.stage}
                    </>
                  ) : (
                    <>
                      <Zap size={20} />
                      Create {currentMode.name}
                    </>
                  )}
                </motion.button>

                {creatingMashup && (
                  <div className="mashup-progress">
                    <div className="progress-bar">
                      <div
                        className="progress-bar-fill"
                        style={{ width: `${mashupProgress.percent}%` }}
                      />
                    </div>
                  </div>
                )}
              </motion.div>
            ) : (
              <motion.div
                className="mashup-result-card glass-card"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
              >
                <div className="result-header">
                  <Check size={32} className="result-icon" />
                  <div>
                    <h2>Your {currentMode.name} is Ready!</h2>
                    <p className="result-meta">
                      {mashupResult.style && `Style: ${mashupResult.style}`}
                      {mashupResult.track_count && ` • ${mashupResult.track_count} tracks`}
                    </p>
                  </div>
                </div>

                {mashupResult.output_filename && (
                  <>
                    <AudioPlayer src={`/remix_outputs/${mashupResult.output_filename}`} />
                    <div className="result-actions">
                      <a
                        href={`/remix_outputs/${mashupResult.output_filename}`}
                        download
                        className="btn btn-primary"
                      >
                        <Download size={18} />
                        Download Audio
                      </a>
                    </div>
                  </>
                )}

                {mashupResult.report_filename && (
                  <div className="report-section">
                    <h3>Mashup Report</h3>
                    <p className="report-desc">
                      Detailed breakdown of transitions, timing, and song order
                    </p>
                    <a
                      href={`/remix_outputs/${mashupResult.report_filename}`}
                      download
                      className="btn btn-secondary"
                    >
                      <Download size={18} />
                      Download Report
                    </a>
                  </div>
                )}

                <button
                  className="btn btn-ghost"
                  onClick={() => {
                    setMashupResult(null)
                    setAnalysisResults(null)
                  }}
                >
                  Create Another Mashup
                </button>
              </motion.div>
            )}

            {/* All Connections */}
            <div className="all-matches glass-card">
              <h2 className="section-title">
                All Possible Combinations
                <span className="match-count">{analysisResults.connections.length} pairs</span>
              </h2>
              <div className="matches-list">
                {analysisResults.connections.slice(0, 10).map((conn, i) => (
                  <div key={i} className={`match-item ${conn.score >= 60 ? 'good' : ''}`}>
                    <div className="match-songs">
                      <span>{conn.from.replace('.mp3', '')}</span>
                      <ArrowRight size={16} />
                      <span>{conn.to.replace('.mp3', '')}</span>
                    </div>
                    <div className="match-score">
                      <span className="score-value">{conn.score}%</span>
                      <span className="score-label">{conn.label}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </section>
      )}

      {/* How It Works */}
      {songs.length === 0 && (
        <section className="how-it-works">
          <h2>How It Works</h2>
          <div className="steps">
            <div className="step">
              <div className="step-icon">1</div>
              <h3>Drop Your Songs</h3>
              <p>Add 2+ Kannada or any songs you want to mashup</p>
            </div>
            <div className="step">
              <div className="step-icon">2</div>
              <h3>Pick Your Style</h3>
              <p>Quick blend, DJ set, or Sandalwood-optimized mix</p>
            </div>
            <div className="step">
              <div className="step-icon">3</div>
              <h3>Get Your Mashup</h3>
              <p>AI analyzes and creates the perfect mix</p>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

export default Home
