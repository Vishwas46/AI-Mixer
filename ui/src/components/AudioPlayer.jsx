import { useEffect, useRef, useState, useMemo } from 'react'
import WaveSurfer from 'wavesurfer.js'
import { Play, Pause, Volume2, VolumeX, ZoomIn, ZoomOut, SkipBack, SkipForward } from 'lucide-react'
import './AudioPlayer.css'

function AudioPlayer({ src, title, cuePoints, analysis }) {
  const containerRef = useRef(null)
  const wavesurferRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentTime, setCurrentTime] = useState('0:00')
  const [duration, setDuration] = useState('0:00')
  const [durationSeconds, setDurationSeconds] = useState(0)
  const [isReady, setIsReady] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(50) // pixels per second
  const [volume, setVolume] = useState(1)

  // Extract cue points from analysis or props
  const markers = useMemo(() => {
    const djCues = cuePoints || analysis?.dj_cue_points
    if (!djCues) return []

    const result = []

    if (djCues.mix_in?.time) {
      result.push({
        time: djCues.mix_in.time,
        label: 'MIX IN',
        color: '#28E5FF',
        type: 'cue'
      })
    }

    if (djCues.drop?.time) {
      result.push({
        time: djCues.drop.time,
        label: 'DROP',
        color: '#FF4444',
        type: 'cue'
      })
    }

    if (djCues.mix_out?.time) {
      result.push({
        time: djCues.mix_out.time,
        label: 'MIX OUT',
        color: '#44FF44',
        type: 'cue'
      })
    }

    // Add hot cues
    if (djCues.hot_cues) {
      djCues.hot_cues.forEach(cue => {
        result.push({
          time: cue.time,
          label: cue.label || `Cue ${cue.number}`,
          color: '#FF44FF',
          type: 'hot'
        })
      })
    }

    return result.sort((a, b) => a.time - b.time)
  }, [cuePoints, analysis])

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  useEffect(() => {
    if (!containerRef.current || !src) return

    const wavesurfer = WaveSurfer.create({
      container: containerRef.current,
      waveColor: 'rgba(148, 163, 184, 0.4)',
      progressColor: '#6366f1',
      cursorColor: '#8b5cf6',
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      height: 80,
      normalize: true,
      backend: 'WebAudio',
      minPxPerSec: zoomLevel,
      scrollParent: true,
      autoScroll: true,
      autoCenter: true,
    })

    wavesurfer.load(src)

    wavesurfer.on('ready', () => {
      wavesurferRef.current = wavesurfer
      const dur = wavesurfer.getDuration()
      setDuration(formatTime(dur))
      setDurationSeconds(dur)
      setIsReady(true)
    })

    wavesurfer.on('audioprocess', () => {
      setCurrentTime(formatTime(wavesurfer.getCurrentTime()))
    })

    wavesurfer.on('seeking', () => {
      setCurrentTime(formatTime(wavesurfer.getCurrentTime()))
    })

    wavesurfer.on('play', () => setIsPlaying(true))
    wavesurfer.on('pause', () => setIsPlaying(false))
    wavesurfer.on('finish', () => setIsPlaying(false))

    return () => {
      wavesurfer.destroy()
    }
  }, [src])

  // Update zoom when level changes
  useEffect(() => {
    if (wavesurferRef.current && isReady) {
      wavesurferRef.current.zoom(zoomLevel)
    }
  }, [zoomLevel, isReady])

  const togglePlay = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause()
    }
  }

  const toggleMute = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.setMuted(!isMuted)
      setIsMuted(!isMuted)
    }
  }

  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev + 25, 200))
  }

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev - 25, 25))
  }

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value)
    setVolume(newVolume)
    if (wavesurferRef.current) {
      wavesurferRef.current.setVolume(newVolume)
    }
  }

  const skipToTime = (seconds) => {
    if (wavesurferRef.current) {
      wavesurferRef.current.seekTo(seconds / durationSeconds)
    }
  }

  const skip = (seconds) => {
    if (wavesurferRef.current) {
      const current = wavesurferRef.current.getCurrentTime()
      const newTime = Math.max(0, Math.min(durationSeconds, current + seconds))
      wavesurferRef.current.seekTo(newTime / durationSeconds)
    }
  }

  return (
    <div className="audio-player glass-card">
      {title && <div className="player-title">{title}</div>}

      {/* Cue Point Markers */}
      {markers.length > 0 && (
        <div className="cue-markers">
          {markers.map((marker, i) => (
            <button
              key={i}
              className="cue-marker-btn"
              style={{ '--cue-color': marker.color }}
              onClick={() => skipToTime(marker.time)}
              title={`${marker.label} (${formatTime(marker.time)})`}
            >
              <span className="cue-dot" />
              <span className="cue-label">{marker.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Main Controls */}
      <div className="player-controls">
        <button
          className="btn btn-ghost control-btn"
          onClick={() => skip(-10)}
          disabled={!isReady}
          title="Back 10s"
        >
          <SkipBack size={16} />
        </button>

        <button
          className="btn btn-primary play-btn"
          onClick={togglePlay}
          disabled={!isReady}
        >
          {isPlaying ? <Pause size={18} /> : <Play size={18} />}
        </button>

        <button
          className="btn btn-ghost control-btn"
          onClick={() => skip(10)}
          disabled={!isReady}
          title="Forward 10s"
        >
          <SkipForward size={16} />
        </button>

        <span className="time-display">{currentTime}</span>

        <div className="waveform-wrapper">
          <div className="waveform-container" ref={containerRef} />
          {/* Cue point indicators on waveform */}
          {isReady && markers.length > 0 && (
            <div className="waveform-markers">
              {markers.map((marker, i) => (
                <div
                  key={i}
                  className="waveform-marker"
                  style={{
                    left: `${(marker.time / durationSeconds) * 100}%`,
                    '--marker-color': marker.color
                  }}
                  title={marker.label}
                />
              ))}
            </div>
          )}
        </div>

        <span className="time-display">{duration}</span>

        {/* Volume Control */}
        <div className="volume-control">
          <button className="btn btn-ghost control-btn" onClick={toggleMute}>
            {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </button>
          <input
            type="range"
            className="volume-slider"
            min="0"
            max="1"
            step="0.05"
            value={volume}
            onChange={handleVolumeChange}
          />
        </div>

        {/* Zoom Controls */}
        <div className="zoom-controls">
          <button
            className="btn btn-ghost control-btn"
            onClick={handleZoomOut}
            disabled={zoomLevel <= 25}
            title="Zoom Out"
          >
            <ZoomOut size={16} />
          </button>
          <span className="zoom-level">{Math.round(zoomLevel / 50 * 100)}%</span>
          <button
            className="btn btn-ghost control-btn"
            onClick={handleZoomIn}
            disabled={zoomLevel >= 200}
            title="Zoom In"
          >
            <ZoomIn size={16} />
          </button>
        </div>
      </div>

      {/* Analysis Info */}
      {analysis && (
        <div className="player-info">
          {analysis.bpm && <span className="info-tag">🎵 {Math.round(analysis.bpm)} BPM</span>}
          {analysis.key && <span className="info-tag">🎹 {analysis.key}</span>}
          {analysis.tala?.detected_tala && (
            <span className="info-tag">🥁 {analysis.tala.detected_tala}</span>
          )}
          {analysis.energy !== undefined && (
            <span className="info-tag">⚡ {Math.round(analysis.energy * 100)}% energy</span>
          )}
        </div>
      )}
    </div>
  )
}

export default AudioPlayer
