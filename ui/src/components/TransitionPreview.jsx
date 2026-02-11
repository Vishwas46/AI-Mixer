import { useState, useRef, useEffect, useCallback } from 'react'
import { Play, Pause, RotateCcw, ArrowRight, Volume2 } from 'lucide-react'
import './TransitionPreview.css'

/**
 * A/B Transition Preview Component
 * Allows users to preview how two songs would transition between each other
 * at specific cue points.
 */
function TransitionPreview({ songA, songB, onClose }) {
  const audioARef = useRef(null)
  const audioBRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentPhase, setCurrentPhase] = useState('idle') // idle, a, transition, b
  const [transitionProgress, setTransitionProgress] = useState(0)
  const [transitionType, setTransitionType] = useState('crossfade') // crossfade, cut, filter
  const [transitionDuration, setTransitionDuration] = useState(4) // seconds

  // Get cue points from analysis
  const mixOutA = songA?.analysis?.dj_cue_points?.mix_out?.time || 30
  const mixInB = songB?.analysis?.dj_cue_points?.mix_in?.time || 0

  const startPreview = useCallback(() => {
    if (!audioARef.current || !audioBRef.current) return

    setIsPlaying(true)
    setCurrentPhase('a')
    setTransitionProgress(0)

    // Start song A 8 seconds before mix out point
    const startTimeA = Math.max(0, mixOutA - 8)
    audioARef.current.currentTime = startTimeA
    audioARef.current.volume = 1
    audioBRef.current.volume = 0
    audioARef.current.play()
  }, [mixOutA])

  const stopPreview = useCallback(() => {
    setIsPlaying(false)
    setCurrentPhase('idle')
    setTransitionProgress(0)

    if (audioARef.current) {
      audioARef.current.pause()
      audioARef.current.currentTime = 0
    }
    if (audioBRef.current) {
      audioBRef.current.pause()
      audioBRef.current.currentTime = 0
    }
  }, [])

  const resetPreview = useCallback(() => {
    stopPreview()
  }, [stopPreview])

  // Handle playback timing
  useEffect(() => {
    if (!isPlaying) return

    const audioA = audioARef.current
    const audioB = audioBRef.current
    if (!audioA || !audioB) return

    const handleTimeUpdate = () => {
      const currentTimeA = audioA.currentTime

      if (currentPhase === 'a') {
        // Check if we should start the transition
        if (currentTimeA >= mixOutA - transitionDuration) {
          setCurrentPhase('transition')
          audioB.currentTime = mixInB
          audioB.play()
        }
      }

      if (currentPhase === 'transition') {
        const transitionElapsed = currentTimeA - (mixOutA - transitionDuration)
        const progress = Math.min(1, transitionElapsed / transitionDuration)
        setTransitionProgress(progress)

        // Apply transition effect
        if (transitionType === 'crossfade') {
          audioA.volume = 1 - progress
          audioB.volume = progress
        } else if (transitionType === 'cut') {
          if (progress >= 0.5) {
            audioA.volume = 0
            audioB.volume = 1
          }
        } else if (transitionType === 'filter') {
          // Simulate filter with volume (real filter would need Web Audio API)
          audioA.volume = Math.max(0, 1 - progress * 1.5)
          audioB.volume = Math.min(1, progress * 1.5)
        }

        if (progress >= 1) {
          setCurrentPhase('b')
          audioA.pause()
          audioB.volume = 1
        }
      }

      if (currentPhase === 'b') {
        // Play song B for a few more seconds then stop
        const bPlayTime = audioB.currentTime - mixInB
        if (bPlayTime >= 8) {
          stopPreview()
        }
      }
    }

    audioA.addEventListener('timeupdate', handleTimeUpdate)
    audioB.addEventListener('timeupdate', handleTimeUpdate)

    return () => {
      audioA.removeEventListener('timeupdate', handleTimeUpdate)
      audioB.removeEventListener('timeupdate', handleTimeUpdate)
    }
  }, [isPlaying, currentPhase, mixOutA, mixInB, transitionDuration, transitionType, stopPreview])

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="transition-preview glass-card">
      <div className="preview-header">
        <h3>A/B Transition Preview</h3>
        <p className="preview-desc">Preview how these songs will blend together</p>
      </div>

      {/* Song Display */}
      <div className="preview-songs">
        <div className={`preview-song ${currentPhase === 'a' || currentPhase === 'transition' ? 'active' : ''}`}>
          <div className="song-label">Song A</div>
          <div className="song-title">{songA?.name?.replace('.mp3', '') || 'Song A'}</div>
          <div className="song-cue">Mix out @ {formatTime(mixOutA)}</div>
          <audio ref={audioARef} src={`/api/stream/${songA?.name}`} preload="auto" />
        </div>

        <div className="preview-transition-indicator">
          <ArrowRight size={24} />
          <div className={`transition-type-badge ${transitionType}`}>
            {transitionType}
          </div>
        </div>

        <div className={`preview-song ${currentPhase === 'b' || currentPhase === 'transition' ? 'active' : ''}`}>
          <div className="song-label">Song B</div>
          <div className="song-title">{songB?.name?.replace('.mp3', '') || 'Song B'}</div>
          <div className="song-cue">Mix in @ {formatTime(mixInB)}</div>
          <audio ref={audioBRef} src={`/api/stream/${songB?.name}`} preload="auto" />
        </div>
      </div>

      {/* Transition Progress */}
      {isPlaying && (
        <div className="transition-progress-section">
          <div className="phase-indicator">
            <span className={currentPhase === 'a' ? 'active' : ''}>Playing A</span>
            <span className={currentPhase === 'transition' ? 'active' : ''}>Transitioning</span>
            <span className={currentPhase === 'b' ? 'active' : ''}>Playing B</span>
          </div>
          {currentPhase === 'transition' && (
            <div className="transition-progress-bar">
              <div
                className="transition-progress-fill"
                style={{ width: `${transitionProgress * 100}%` }}
              />
            </div>
          )}
          <div className="volume-indicators">
            <div className="volume-indicator">
              <Volume2 size={14} />
              <span>A: {Math.round((1 - transitionProgress) * 100)}%</span>
            </div>
            <div className="volume-indicator">
              <Volume2 size={14} />
              <span>B: {Math.round(transitionProgress * 100)}%</span>
            </div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="preview-controls">
        <div className="transition-options">
          <label>Transition Type:</label>
          <div className="transition-type-buttons">
            {['crossfade', 'cut', 'filter'].map(type => (
              <button
                key={type}
                className={`type-btn ${transitionType === type ? 'active' : ''}`}
                onClick={() => setTransitionType(type)}
                disabled={isPlaying}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        <div className="duration-control">
          <label>Duration: {transitionDuration}s</label>
          <input
            type="range"
            min="1"
            max="8"
            value={transitionDuration}
            onChange={e => setTransitionDuration(Number(e.target.value))}
            disabled={isPlaying}
          />
        </div>
      </div>

      <div className="preview-actions">
        {!isPlaying ? (
          <button className="btn btn-primary" onClick={startPreview}>
            <Play size={18} />
            Preview Transition
          </button>
        ) : (
          <button className="btn btn-secondary" onClick={stopPreview}>
            <Pause size={18} />
            Stop
          </button>
        )}
        <button className="btn btn-ghost" onClick={resetPreview} disabled={!isPlaying}>
          <RotateCcw size={18} />
          Reset
        </button>
        {onClose && (
          <button className="btn btn-ghost" onClick={onClose}>
            Close
          </button>
        )}
      </div>
    </div>
  )
}

export default TransitionPreview
