import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { submitCredentialToken } from '../api/client'
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
  credentialPrompt: string | null
  clearCredentialPrompt: () => void
  submitCredential: (token: string) => Promise<void>
} {
  const [logs, setLogs] = useState<LogMessage[]>([])
  const [connected, setConnected] = useState(false)
  const [done, setDone] = useState(false)
  const [credentialPrompt, setCredentialPrompt] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)

  const clearCredentialPrompt = useCallback(() => {
    setCredentialPrompt(null)
  }, [])

  const submitCredential = useCallback(async (token: string) => {
    const trimmedToken = token.trim()
    if (!trimmedToken) {
      return
    }

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'credential_response',
          token: trimmedToken,
        }),
      )
      setCredentialPrompt(null)
      return
    }

    await submitCredentialToken(trimmedToken)
    setCredentialPrompt(null)
  }, [])

  useEffect(() => {
    if (!deploymentId) {
      setLogs([])
      setConnected(false)
      setDone(false)
      setCredentialPrompt(null)
      socketRef.current = null
      return
    }

    const url = createWebSocketUrl(deploymentId)
    const socket = new WebSocket(url)
    socketRef.current = socket

    setLogs([])
    setConnected(false)
    setDone(false)
    setCredentialPrompt(null)

    socket.onopen = () => {
      setConnected(true)
    }

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as LogMessage
        setLogs((previous) => [...previous, message])
        if (message.type === 'credential_required') {
          setCredentialPrompt(message.line)
        }
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
      if (socketRef.current === socket) {
        socketRef.current = null
      }
    }

    return () => {
      socket.close()
      if (socketRef.current === socket) {
        socketRef.current = null
      }
      setConnected(false)
    }
  }, [deploymentId])

  return useMemo(
    () => ({
      logs,
      connected,
      done,
      credentialPrompt,
      clearCredentialPrompt,
      submitCredential,
    }),
    [clearCredentialPrompt, connected, credentialPrompt, done, logs, submitCredential],
  )
}
