import { useState, useEffect, useRef } from 'react'
import { motion as Motion, AnimatePresence } from 'framer-motion'
import { Upload, Music, Clock, Key, Activity, RefreshCw, Search, X, ChevronDown, ChevronUp } from 'lucide-react'
import TaskProgress from '../components/TaskProgress'
import { apiFetch } from '../api'
import './Library.css'

function Library() {
  const [songs, setSongs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [analyzingId, setAnalyzingId] = useState(null)
  const [expandedSong, setExpandedSong] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const fileInputRef = useRef(null)

  const fetchSongs = async () => {
    try {
      // /api/songs lists files (name, has_analysis); analysis details live
      // in the cache exposed by /api/analysis/all — merge the two here
      const [songsData, analysisData] = await Promise.all([
        apiFetch('/api/songs'),
        apiFetch('/api/analysis/all'),
      ])
      const analyses = analysisData.analyses || {}
      setSongs((songsData.songs || []).map(s => ({
        ...s,
        filename: s.name,
        analysis: analyses[s.name] || null,
      })))
    } catch (err) {
      console.error('Failed to fetch songs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSongs()
  }, [])

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/songs/upload', {
        method: 'POST',
        body: formData,
      })
      if (res.ok) {
        fetchSongs()
      }
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const analyzeKannada = async (filename) => {
    try {
      const res = await fetch('/api/analyze/kannada', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
      })
      const data = await res.json()
      setAnalyzingId(data.task_id)
    } catch (err) {
      console.error('Analysis failed:', err)
    }
  }

  const handleAnalysisComplete = (task) => {
    setAnalyzingId(null)
    if (task.status === 'completed') {
      fetchSongs()
    }
  }

  const filteredSongs = songs.filter(song =>
    song.filename.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatDuration = (seconds) => {
    if (!seconds) return '--:--'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="library-page fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Song Library</h1>
          <p className="page-subtitle">Manage and analyze your audio files</p>
        </div>
        <div className="header-actions">
          <button
            className="btn btn-secondary"
            onClick={fetchSongs}
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            Refresh
          </button>
          <button
            className="btn btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <Upload size={16} />
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp3,.wav,.flac,.m4a"
            onChange={handleUpload}
            style={{ display: 'none' }}
          />
        </div>
      </div>

      {analyzingId && (
        <div className="analysis-progress">
          <TaskProgress taskId={analyzingId} onComplete={handleAnalysisComplete} />
        </div>
      )}

      <div className="search-bar glass-card">
        <Search size={18} className="search-icon" />
        <input
          type="text"
          placeholder="Search songs..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button className="btn btn-ghost" onClick={() => setSearchQuery('')}>
            <X size={16} />
          </button>
        )}
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner" />
          <span>Loading songs...</span>
        </div>
      ) : filteredSongs.length === 0 ? (
        <div className="empty-state glass-card">
          <Music size={48} className="empty-icon" />
          <h3>No songs found</h3>
          <p>Upload some audio files to get started</p>
        </div>
      ) : (
        <div className="songs-list">
          <AnimatePresence>
            {filteredSongs.map((song, index) => (
              <Motion.div
                key={song.filename}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ delay: index * 0.05 }}
                className="song-card glass-card glass-card-hover"
              >
                <div
                  className="song-header"
                  onClick={() => setExpandedSong(
                    expandedSong === song.filename ? null : song.filename
                  )}
                >
                  <div className="song-info">
                    <Music size={20} className="song-icon" />
                    <div>
                      <div className="song-name">{song.filename}</div>
                      <div className="song-meta">
                        {song.analysis ? (
                          <>
                            <span className="meta-item">
                              <Activity size={12} />
                              {Math.round(song.analysis.bpm || song.analysis.beat_grid?.tempo)} BPM
                            </span>
                            <span className="meta-item">
                              <Key size={12} />
                              {song.analysis.key || song.analysis.tala?.primary_tala || 'Unknown'}
                            </span>
                            <span className="meta-item">
                              <Clock size={12} />
                              {formatDuration(song.analysis.duration)}
                            </span>
                          </>
                        ) : (
                          <span className="badge badge-warning">Not analyzed</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="song-actions">
                    {!song.analysis && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          analyzeKannada(song.filename)
                        }}
                        disabled={analyzingId}
                      >
                        Analyze
                      </button>
                    )}
                    {expandedSong === song.filename ? (
                      <ChevronUp size={20} />
                    ) : (
                      <ChevronDown size={20} />
                    )}
                  </div>
                </div>

                <AnimatePresence>
                  {expandedSong === song.filename && song.analysis && (
                    <Motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="song-details"
                    >
                      <div className="details-grid">
                        <div className="detail-card">
                          <div className="detail-label">Tala</div>
                          <div className="detail-value">
                            {song.analysis.tala?.primary_tala || 'Unknown'}
                          </div>
                          {song.analysis.tala?.confidence && (
                            <div className="detail-sub">
                              {Math.round(song.analysis.tala.confidence * 100)}% confidence
                            </div>
                          )}
                        </div>
                        <div className="detail-card">
                          <div className="detail-label">Scale</div>
                          <div className="detail-value">
                            {song.analysis.scale_profile?.primary_scale || 'Unknown'}
                          </div>
                        </div>
                        <div className="detail-card">
                          <div className="detail-label">Energy</div>
                          <div className="detail-value">
                            {song.analysis.spectral?.energy_level || 'Medium'}
                          </div>
                        </div>
                        <div className="detail-card">
                          <div className="detail-label">Beat Grid</div>
                          <div className="detail-value">
                            {song.analysis.beat_grid?.is_tempo_stable ? 'Stable' : 'Variable'}
                          </div>
                          {song.analysis.beat_grid?.tempo_stability && (
                            <div className="detail-sub">
                              {Math.round(song.analysis.beat_grid.tempo_stability * 100)}% stability
                            </div>
                          )}
                        </div>
                      </div>

                      {song.analysis.dj_cue_points && (
                        <div className="cue-points">
                          <div className="detail-label">DJ Cue Points</div>
                          <div className="cue-tags">
                            {song.analysis.dj_cue_points.mix_in && (
                              <span className="badge badge-success">
                                Mix In: {formatDuration(song.analysis.dj_cue_points.mix_in.time)}
                              </span>
                            )}
                            {song.analysis.dj_cue_points.mix_out && (
                              <span className="badge badge-warning">
                                Mix Out: {formatDuration(song.analysis.dj_cue_points.mix_out.time)}
                              </span>
                            )}
                            {song.analysis.dj_cue_points.drop && (
                              <span className="badge badge-primary">
                                Drop: {formatDuration(song.analysis.dj_cue_points.drop.time)}
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {song.analysis.sections && (
                        <div className="sections-info">
                          <div className="detail-label">Sections</div>
                          <div className="sections-list">
                            {song.analysis.sections.slice(0, 6).map((section, i) => (
                              <span key={i} className="section-tag">
                                {section.type} ({formatDuration(section.start)})
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </Motion.div>
                  )}
                </AnimatePresence>
              </Motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}

export default Library
