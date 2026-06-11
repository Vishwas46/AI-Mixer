import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Music, Check, Info } from 'lucide-react'
import './CompatibilityGraph.css'

function CompatibilityGraph({ data }) {
  const [hoveredConnection, setHoveredConnection] = useState(null)
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 })
  const containerRef = useRef(null)

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const width = Math.min(containerRef.current.offsetWidth, 700)
        const height = Math.min(400, width * 0.6)
        setDimensions({ width, height })
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  if (!data || !data.songs || data.songs.length < 2) {
    return null
  }

  const { songs, connections } = data
  const { width, height } = dimensions

  // Calculate node positions in a circle
  const centerX = width / 2
  const centerY = height / 2
  const radius = Math.min(width, height) * 0.35

  const nodePositions = songs.map((song, i) => {
    const angle = (i / songs.length) * 2 * Math.PI - Math.PI / 2
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
      song
    }
  })

  // Get connection line properties
  const getConnectionStyle = (conn) => {
    const fromNode = nodePositions.find(n => n.song.name === conn.from)
    const toNode = nodePositions.find(n => n.song.name === conn.to)

    if (!fromNode || !toNode) return null

    const score = conn.score
    const strokeWidth = Math.max(1, (score / 100) * 6)
    const opacity = 0.3 + (score / 100) * 0.5

    let color = 'var(--text-muted)'
    if (score >= 80) color = 'var(--success)'
    else if (score >= 60) color = 'var(--accent-primary)'
    else if (score >= 40) color = 'var(--warning)'

    return {
      x1: fromNode.x,
      y1: fromNode.y,
      x2: toNode.x,
      y2: toNode.y,
      strokeWidth,
      opacity,
      color,
      score
    }
  }

  const hoveredConn = hoveredConnection
    ? connections.find(c =>
        (c.from === hoveredConnection.from && c.to === hoveredConnection.to) ||
        (c.from === hoveredConnection.to && c.to === hoveredConnection.from)
      )
    : null

  return (
    <div className="compatibility-graph" ref={containerRef}>
      <svg width={width} height={height} className="graph-svg">
        {/* Connection lines */}
        {connections.map((conn, i) => {
          const style = getConnectionStyle(conn)
          if (!style) return null

          const isHovered = hoveredConnection &&
            ((conn.from === hoveredConnection.from && conn.to === hoveredConnection.to) ||
             (conn.from === hoveredConnection.to && conn.to === hoveredConnection.from))

          return (
            <line
              key={i}
              x1={style.x1}
              y1={style.y1}
              x2={style.x2}
              y2={style.y2}
              stroke={style.color}
              strokeWidth={isHovered ? style.strokeWidth + 2 : style.strokeWidth}
              opacity={isHovered ? 1 : style.opacity}
              className="connection-line"
              onMouseEnter={() => setHoveredConnection(conn)}
              onMouseLeave={() => setHoveredConnection(null)}
            />
          )
        })}

        {/* Song nodes */}
        {nodePositions.map((node, i) => (
          <g key={i} transform={`translate(${node.x}, ${node.y})`}>
            <motion.circle
              r={24}
              className="song-node"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: i * 0.1 }}
            />
            <motion.circle
              r={20}
              className="song-node-inner"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: i * 0.1 + 0.05 }}
            />
            <Music size={16} x={-8} y={-8} className="node-icon" />
          </g>
        ))}

        {/* Song labels */}
        {nodePositions.map((node, i) => {
          const labelOffset = 35
          const angle = (i / songs.length) * 2 * Math.PI - Math.PI / 2
          const labelX = node.x + labelOffset * Math.cos(angle) * 0.8
          const labelY = node.y + labelOffset * Math.sin(angle) + 5

          return (
            <text
              key={`label-${i}`}
              x={labelX}
              y={labelY}
              className="song-label"
              textAnchor="middle"
            >
              {node.song.name.replace('.mp3', '').substring(0, 15)}
              {node.song.name.length > 18 ? '...' : ''}
            </text>
          )
        })}
      </svg>

      {/* Tooltip for hovered connection */}
      {hoveredConn && (
        <motion.div
          className="connection-tooltip glass-card"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="tooltip-header">
            <span className="tooltip-songs">
              {hoveredConn.from.replace('.mp3', '')} + {hoveredConn.to.replace('.mp3', '')}
            </span>
            <span className={`tooltip-score ${hoveredConn.score >= 60 ? 'good' : ''}`}>
              {hoveredConn.score}%
            </span>
          </div>
          <div className="tooltip-reasons">
            {hoveredConn.reasons.map((reason, i) => (
              <div key={i} className={`tooltip-reason ${reason.good ? 'good' : ''}`}>
                {reason.good ? <Check size={12} /> : <Info size={12} />}
                {reason.text}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Legend */}
      <div className="graph-legend">
        <div className="legend-item">
          <span className="legend-line thick success"></span>
          <span>Perfect (80%+)</span>
        </div>
        <div className="legend-item">
          <span className="legend-line medium primary"></span>
          <span>Great (60-79%)</span>
        </div>
        <div className="legend-item">
          <span className="legend-line thin muted"></span>
          <span>Possible (&lt;60%)</span>
        </div>
      </div>
    </div>
  )
}

export default CompatibilityGraph
