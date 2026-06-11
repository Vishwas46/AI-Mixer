import { useEffect, useState, useRef } from 'react'
import { CheckCircle, AlertCircle, Loader } from 'lucide-react'
import { apiUrl } from '../api'
import './TaskProgress.css'

function TaskProgress({ taskId, onComplete }) {
  const [task, setTask] = useState(null)
  const [logs, setLogs] = useState([])
  const logsEndRef = useRef(null)

  useEffect(() => {
    if (!taskId) return

    let finished = false
    let pollTimer = null
    const eventSource = new EventSource(apiUrl(`/api/tasks/${taskId}/stream`))

    const finish = (data) => {
      if (finished) return
      finished = true
      eventSource.close()
      if (pollTimer) clearTimeout(pollTimer)
      if (onComplete) onComplete(data)
    }

    // The stream emits per-field events — {type:'log', message},
    // {type:'progress', progress}, {type:'status', status} and a terminal
    // {type:'complete', status, result|error} — merge them into the task
    // instead of treating each event as a full task object.
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'log') {
        if (data.message) setLogs(prev => [...prev, data.message])
        return
      }
      setTask(prev => ({ ...(prev || { status: 'running', progress: 0 }), ...data }))
      if (data.type === 'complete') {
        finish(data)
      }
    }

    eventSource.onerror = () => {
      if (finished) return
      eventSource.close()
      // Fall back to polling the task endpoint
      const poll = async () => {
        if (finished) return
        try {
          const res = await fetch(apiUrl(`/api/tasks/${taskId}`))
          const data = await res.json()
          setTask(data)
          if (data.log) setLogs(data.log)
          if (data.status === 'completed' || data.status === 'failed') {
            finish(data)
          } else {
            pollTimer = setTimeout(poll, 1000)
          }
        } catch (err) {
          console.error('Poll error:', err)
          pollTimer = setTimeout(poll, 2000)
        }
      }
      poll()
    }

    return () => {
      finished = true
      eventSource.close()
      if (pollTimer) clearTimeout(pollTimer)
    }
  }, [taskId])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  if (!task) {
    return (
      <div className="task-progress glass-card">
        <div className="flex items-center gap-md">
          <div className="spinner" />
          <span>Starting task...</span>
        </div>
      </div>
    )
  }

  const statusIcon = {
    pending: <Loader className="spin" size={20} />,
    running: <Loader className="spin" size={20} />,
    completed: <CheckCircle size={20} className="status-success" />,
    failed: <AlertCircle size={20} className="status-error" />,
  }

  return (
    <div className="task-progress glass-card">
      <div className="task-header">
        <div className="task-status">
          {statusIcon[task.status]}
          <span className="status-text">{task.status}</span>
        </div>
        {task.progress > 0 && task.status === 'running' && (
          <span className="progress-percent">{task.progress}%</span>
        )}
      </div>

      {task.status === 'running' && (
        <div className="progress-bar">
          <div
            className="progress-bar-fill"
            style={{ width: `${task.progress || 0}%` }}
          />
        </div>
      )}

      {logs.length > 0 && (
        <div className="task-logs">
          {logs.slice(-10).map((log, i) => (
            <div key={i} className="log-line">
              {log}
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      )}

      {task.error && (
        <div className="task-error">
          <AlertCircle size={16} />
          <span>{task.error}</span>
        </div>
      )}
    </div>
  )
}

export default TaskProgress
