import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload, Music, Sparkles, Play, Loader, Check,
  ArrowRight, Info, Zap, Heart, Clock, Volume2,
  ChevronDown, X, Download
} from 'lucide-react'
import AudioPlayer from '../components/AudioPlayer'
import CompatibilityGraph from '../components/CompatibilityGraph'
import './Home.css'

// Friendly explanations for technical terms
const FRIENDLY_TERMS = {
  bpm: { label: 'Tempo', icon: Clock, desc: 'How fast the song is - songs with similar tempo blend smoothly' },
  key: { label: 'Musical Key', icon: Music, desc: 'The "home note" - matching keys sound harmonious together' },
  energy: { label: 'Energy', icon: Zap, desc: 'How intense/powerful the song feels' },
  mood: { label: 'Mood', icon: Heart, desc: 'The emotional feeling of the song' },
}

function Home() {
  const navigate = useNavigate()
  const [songs, setSongs] = useState([])
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisProgress, setAnalysisProgress] = useState({ current: 0, total: 0, stage: '' })
  const [analysisResults, setAnalysisResults] = useState(null)
  const [bestMashup, setBestMashup] = useState(null)
  const [creatingMashup, setCreatingMashup] = useState(false)
  const [mashupProgress, setMashupProgress] = useState({ percent: 0, stage: '' })
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState(null)

  // Fetch existing songs on mount
  useEffect(() => {
    fetchExistingSongs()
  }, [])

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

    // Add files to list with uploading status
    const newSongs = files.map(f => ({ name: f.name, status: 'uploading', file: f }))
    setSongs(prev => [...prev, ...newSongs])

    // Upload each file
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
  }

  // Main analysis function - analyzes all songs deeply
  const analyzeAllSongs = async () => {
    const songsToAnalyze = songs.filter(s => s.status === 'ready' || s.status === 'analyzed')
    if (songsToAnalyze.length < 2) {
      setError('Add at least 2 songs to create a mashup')
      return
    }

    setAnalyzing(true)
    setError(null)
    setAnalysisProgress({ current: 0, total: songsToAnalyze.length, stage: 'Starting deep analysis...' })

    const results = []

    for (let i = 0; i < songsToAnalyze.length; i++) {
      const song = songsToAnalyze[i]
      setAnalysisProgress({
        current: i + 1,
        total: songsToAnalyze.length,
        stage: `Listening to "${song.name.replace('.mp3', '')}"...`
      })

      // Update song status
      setSongs(prev => prev.map(s =>
        s.name === song.name ? { ...s, status: 'analyzing' } : s
      ))

      try {
        // Start Kannada analysis (deep analysis)
        const res = await fetch('/api/analyze/kannada', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: song.name })
        })
        const taskData = await res.json()

        // Poll for completion
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

          // Update progress stage based on logs
          if (status.log && status.log.length > 0) {
            const lastLog = status.log[status.log.length - 1]
            if (lastLog.includes('beat')) {
              setAnalysisProgress(prev => ({ ...prev, stage: `Finding the rhythm in "${song.name.replace('.mp3', '')}"...` }))
            } else if (lastLog.includes('vocal')) {
              setAnalysisProgress(prev => ({ ...prev, stage: `Detecting vocals in "${song.name.replace('.mp3', '')}"...` }))
            } else if (lastLog.includes('tala') || lastLog.includes('scale')) {
              setAnalysisProgress(prev => ({ ...prev, stage: `Understanding the musical structure...` }))
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

    // Calculate compatibility and find best mashup
    setAnalysisProgress({ current: songsToAnalyze.length, total: songsToAnalyze.length, stage: 'Finding the perfect combinations...' })

    const analyzedSongs = results.filter(s => s.analysis)
    if (analyzedSongs.length >= 2) {
      const compatibilityData = calculateCompatibility(analyzedSongs)
      setAnalysisResults(compatibilityData)

      // Find best pair
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

  // Calculate compatibility between all song pairs
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

        // BPM compatibility (0-30 points)
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

        // Key compatibility (0-30 points)
        const key1 = a1.key || 'C'
        const key2 = a2.key || 'C'
        const keyMatch = checkKeyCompatibility(key1, key2)
        score += keyMatch.score
        reasons.push({ type: 'key', text: keyMatch.reason, good: keyMatch.score >= 20 })

        // Energy compatibility (0-20 points)
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

        // Tala/rhythm compatibility (0-20 points)
        const tala1 = a1.tala?.detected_tala
        const tala2 = a2.tala?.detected_tala
        if (tala1 && tala2 && tala1 === tala2) {
          score += 20
          reasons.push({ type: 'rhythm', text: `Same rhythm pattern (${tala1})`, good: true })
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
    // Simplified key compatibility check
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

  // Create the best mashup
  const createBestMashup = async () => {
    if (!bestMashup) return

    setCreatingMashup(true)
    setMashupProgress({ percent: 0, stage: 'Starting to create your mashup...' })
    setError(null)

    try {
      const res = await fetch('/api/mashup/single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          song1: bestMashup.song1.name,
          song2: bestMashup.song2.name
        })
      })
      const taskData = await res.json()

      // Poll for completion with friendly messages
      const stages = [
        'Analyzing song structures...',
        'Finding the best blend points...',
        'Matching tempos and keys...',
        'Creating smooth transitions...',
        'Polishing the final mix...'
      ]
      let stageIndex = 0

      while (true) {
        await new Promise(r => setTimeout(r, 1500))
        const statusRes = await fetch(`/api/tasks/${taskData.task_id}`)
        const status = await statusRes.json()

        if (status.status === 'completed') {
          setMashupProgress({ percent: 100, stage: 'Your mashup is ready!' })
          setBestMashup(prev => ({ ...prev, outputFile: status.result?.output_file }))
          break
        } else if (status.status === 'failed') {
          throw new Error(status.error || 'Failed to create mashup')
        }

        // Update progress with friendly stages
        const percent = Math.min(95, (status.progress || 0))
        if (percent > (stageIndex + 1) * 20 && stageIndex < stages.length - 1) {
          stageIndex++
        }
        setMashupProgress({ percent, stage: stages[stageIndex] })
      }
    } catch (err) {
      setError(err.message)
    }

    setCreatingMashup(false)
  }

  const readySongs = songs.filter(s => s.status === 'ready' || s.status === 'analyzed')

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
            Drop your songs below. We'll find the perfect combinations and create a professional mashup for you.
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
          <motion.div
            className="error-message"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {error}
          </motion.div>
        )}
      </section>

      {/* Analysis Section */}
      {songs.length >= 2 && !analysisResults && (
        <section className="action-section">
          <motion.button
            className="btn btn-primary btn-large analyze-btn"
            onClick={analyzeAllSongs}
            disabled={analyzing || readySongs.length < 2}
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
                Analyze & Find Best Mashup
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
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
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

            {/* Best Mashup Recommendation */}
            {bestMashup && (
              <motion.div
                className="best-mashup-card glass-card"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 }}
              >
                <div className="best-header">
                  <Sparkles className="best-icon" />
                  <div>
                    <h2>Best Mashup Found!</h2>
                    <p className="compatibility-score">
                      {bestMashup.score}% Compatible
                    </p>
                  </div>
                </div>

                <div className="best-songs">
                  <div className="best-song">
                    <Music size={24} />
                    <span>{bestMashup.song1.name.replace('.mp3', '')}</span>
                  </div>
                  <div className="best-connector">+</div>
                  <div className="best-song">
                    <Music size={24} />
                    <span>{bestMashup.song2.name.replace('.mp3', '')}</span>
                  </div>
                </div>

                <div className="reasons-list">
                  {bestMashup.reasons.map((reason, i) => (
                    <div key={i} className={`reason-item ${reason.good ? 'good' : 'neutral'}`}>
                      {reason.good ? <Check size={16} /> : <Info size={16} />}
                      <span>{reason.text}</span>
                    </div>
                  ))}
                </div>

                {!bestMashup.outputFile ? (
                  <motion.button
                    className="btn btn-primary btn-large create-btn"
                    onClick={createBestMashup}
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
                        Create This Mashup
                      </>
                    )}
                  </motion.button>
                ) : (
                  <div className="mashup-ready">
                    <div className="ready-badge">
                      <Check size={20} />
                      Your mashup is ready!
                    </div>
                    <AudioPlayer src={`/remix_outputs/${bestMashup.outputFile}`} />
                    <a
                      href={`/remix_outputs/${bestMashup.outputFile}`}
                      download
                      className="btn btn-secondary"
                    >
                      <Download size={18} />
                      Download Mashup
                    </a>
                  </div>
                )}

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
              <p>Add 2 or more songs you want to mashup</p>
            </div>
            <div className="step">
              <div className="step-icon">2</div>
              <h3>AI Analyzes</h3>
              <p>We detect tempo, key, energy & find the best matches</p>
            </div>
            <div className="step">
              <div className="step-icon">3</div>
              <h3>Get Your Mashup</h3>
              <p>One click to create a professional mashup</p>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

export default Home
