import { useEffect, useMemo, useState } from 'react'
import type { LogMessage } from '../types'

function createWebSocketUrl(deploymentId: string): string {
  if (window.location.hostname === 'localhost') {
    return `ws://localhost:8000/api/ws/logs/${deploymentId}`
  }

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/api/ws/logs/${deploymentId}`
}

export function useWebSocket(deploymentId: string | null): {
  logs: LogMessage[]
  connected: boolean
  done: boolean
} {
  const [logs, setLogs] = useState<LogMessage[]>([])
  const [connected, setConnected] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (!deploymentId) {
      setLogs([])
      setConnected(false)
      setDone(false)
      return
    }

    const url = createWebSocketUrl(deploymentId)
    const socket = new WebSocket(url)

    setLogs([])
    setConnected(false)
    setDone(false)

    socket.onopen = () => {
      setConnected(true)
    }

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as LogMessage
        setLogs((previous) => [...previous, message])
        if (message.done) {
          setDone(true)
        }
      } catch {
        setLogs((previous) => [
          ...previous,
          {
            type: 'system',
            line: String(event.data),
            timestamp: new Date().toISOString(),
          },
        ])
      }
    }

    socket.onerror = () => {
      setLogs((previous) => [
        ...previous,
        {
          type: 'system',
          line: 'WebSocket connection error',
          timestamp: new Date().toISOString(),
        },
      ])
    }

    socket.onclose = () => {
      setConnected(false)
    }

    return () => {
      socket.close()
      setConnected(false)
    }
  }, [deploymentId])

  return useMemo(
    () => ({
      logs,
      connected,
      done,
    }),
    [connected, done, logs],
  )
}
