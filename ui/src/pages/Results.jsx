import { useState, useEffect } from 'react'
import { motion as Motion, AnimatePresence } from 'framer-motion'
import { Headphones, Download, Trash2, RefreshCw, Clock, FileAudio } from 'lucide-react'
import AudioPlayer from '../components/AudioPlayer'
import { apiFetch, apiUrl } from '../api'
import './Results.css'

function Results() {
  const [outputs, setOutputs] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedOutput, setSelectedOutput] = useState(null)

  const fetchOutputs = async () => {
    setLoading(true)
    try {
      const data = await apiFetch('/api/outputs')
      // Keep only audio (the folder also holds .txt mix reports) and map
      // the API's name/modified/size_bytes fields to what this page renders
      const audio = (data.outputs || [])
        .filter(o => /\.(mp3|wav|flac|m4a|ogg)$/i.test(o.name))
        .map(o => ({ ...o, filename: o.name, created_at: o.modified, size: o.size_bytes }))
      setOutputs(audio)
    } catch (err) {
      console.error('Failed to fetch outputs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOutputs()
  }, [])

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return dateStr
    }
  }

  const formatSize = (bytes) => {
    if (!bytes) return 'Unknown'
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(1)} MB`
  }

  const downloadFile = (filename) => {
    const link = document.createElement('a')
    link.href = apiUrl(`/api/stream/${filename}`)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="results-page fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Results</h1>
          <p className="page-subtitle">Listen to your generated mixes</p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={fetchOutputs}
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Audio Player Area */}
      {selectedOutput && (
        <Motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="player-area"
        >
          <AudioPlayer
            src={apiUrl(`/api/stream/${selectedOutput.filename}`)}
            title={selectedOutput.filename}
          />
        </Motion.div>
      )}

      {/* Outputs List */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner" />
          <span>Loading outputs...</span>
        </div>
      ) : outputs.length === 0 ? (
        <div className="empty-state glass-card">
          <Headphones size={48} className="empty-icon" />
          <h3>No mixes yet</h3>
          <p>Go to Studio and create your first mashup</p>
        </div>
      ) : (
        <div className="outputs-grid">
          <AnimatePresence>
            {outputs.map((output, index) => (
              <Motion.div
                key={output.filename}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ delay: index * 0.05 }}
                className={`output-card glass-card glass-card-hover ${
                  selectedOutput?.filename === output.filename ? 'active' : ''
                }`}
                onClick={() => setSelectedOutput(output)}
              >
                <div className="output-icon">
                  <FileAudio size={32} />
                </div>
                <div className="output-info">
                  <div className="output-name">{output.filename}</div>
                  <div className="output-meta">
                    <span className="meta-item">
                      <Clock size={12} />
                      {formatDate(output.created_at)}
                    </span>
                    <span className="meta-item">
                      {formatSize(output.size)}
                    </span>
                  </div>
                </div>
                <div className="output-actions">
                  <button
                    className="btn btn-ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      downloadFile(output.filename)
                    }}
                    title="Download"
                  >
                    <Download size={18} />
                  </button>
                </div>
              </Motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}

export default Results
