import { useEffect, useRef, useState } from 'react'
import WaveSurfer from 'wavesurfer.js'
import { Play, Pause, Volume2, VolumeX } from 'lucide-react'
import './AudioPlayer.css'

function AudioPlayer({ src, title }) {
  const containerRef = useRef(null)
  const wavesurferRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentTime, setCurrentTime] = useState('0:00')
  const [duration, setDuration] = useState('0:00')
  const [isReady, setIsReady] = useState(false)

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
      height: 60,
      normalize: true,
      backend: 'WebAudio',
    })

    wavesurfer.load(src)

    wavesurfer.on('ready', () => {
      wavesurferRef.current = wavesurfer
      setDuration(formatTime(wavesurfer.getDuration()))
      setIsReady(true)
    })

    wavesurfer.on('audioprocess', () => {
      setCurrentTime(formatTime(wavesurfer.getCurrentTime()))
    })

    wavesurfer.on('play', () => setIsPlaying(true))
    wavesurfer.on('pause', () => setIsPlaying(false))
    wavesurfer.on('finish', () => setIsPlaying(false))

    return () => {
      wavesurfer.destroy()
    }
  }, [src])

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

  return (
    <div className="audio-player glass-card">
      {title && <div className="player-title">{title}</div>}
      <div className="player-controls">
        <button
          className="btn btn-primary play-btn"
          onClick={togglePlay}
          disabled={!isReady}
        >
          {isPlaying ? <Pause size={18} /> : <Play size={18} />}
        </button>
        <span className="time-display">{currentTime}</span>
        <div className="waveform-container" ref={containerRef} />
        <span className="time-display">{duration}</span>
        <button className="btn btn-ghost" onClick={toggleMute}>
          {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
        </button>
      </div>
    </div>
  )
}

export default AudioPlayer
