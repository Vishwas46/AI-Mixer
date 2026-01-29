import { useEffect, useState, useRef } from 'react'
import { CheckCircle, AlertCircle, Loader } from 'lucide-react'
import './TaskProgress.css'

function TaskProgress({ taskId, onComplete }) {
  const [task, setTask] = useState(null)
  const [logs, setLogs] = useState([])
  const logsEndRef = useRef(null)
  const eventSourceRef = useRef(null)

  useEffect(() => {
    if (!taskId) return

    // Use SSE for live updates
    const eventSource = new EventSource(`/api/tasks/${taskId}/stream`)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setTask(data)
      if (data.log) {
        setLogs(data.log)
      }
      if (data.status === 'completed' || data.status === 'failed') {
        eventSource.close()
        if (onComplete) {
          onComplete(data)
        }
      }
    }

    eventSource.onerror = () => {
      eventSource.close()
      // Fall back to polling
      pollTask()
    }

    return () => {
      eventSource.close()
    }
  }, [taskId])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const pollTask = async () => {
    try {
      const res = await fetch(`/api/tasks/${taskId}`)
      const data = await res.json()
      setTask(data)
      if (data.log) {
        setLogs(data.log)
      }
      if (data.status !== 'completed' && data.status !== 'failed') {
        setTimeout(pollTask, 1000)
      } else if (onComplete) {
        onComplete(data)
      }
    } catch (err) {
      console.error('Poll error:', err)
    }
  }

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
