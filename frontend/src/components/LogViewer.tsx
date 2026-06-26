import { useEffect, useRef, useState } from 'react'
import type { DeployState, LogMessage } from '../types'

interface LogViewerProps {
  logs: LogMessage[]
  connected: boolean
  deploymentActive: boolean
  done: boolean
  status: DeployState
}

function lineClass(type: LogMessage['type']): string {
  switch (type) {
    case 'stderr':
      return 'text-orange-300'
    case 'system':
      return 'text-cyan-300 italic'
    default:
      return 'text-gray-100'
  }
}

export function LogViewer({ logs, connected, deploymentActive, done, status }: LogViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [autoScroll, logs])

  const onScroll = () => {
    if (!containerRef.current) {
      return
    }

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const atBottom = scrollHeight - scrollTop - clientHeight < 16
    setAutoScroll(atBottom)
  }

  return (
    <div className="rounded-lg border border-slate-300 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-700">Deployment Logs</h2>
      <div
        ref={containerRef}
        onScroll={onScroll}
        className="h-80 overflow-y-auto rounded-md bg-gray-900 p-4 font-mono text-sm text-gray-100"
      >
        {!deploymentActive && logs.length === 0 && <p className="text-gray-400">Logs will appear after deployment starts.</p>}
        {deploymentActive && !connected && <p className="mb-1 text-cyan-300 italic">Connecting...</p>}
        {logs.map((message, index) => (
          <p key={`${message.timestamp}-${index}`} className={lineClass(message.type)}>
            {message.line}
          </p>
        ))}
        {done && status === 'success' && <p className="mt-2 text-emerald-300">✓ Deployment successful</p>}
        {done && status === 'failed' && <p className="mt-2 text-red-300">✗ Deployment failed</p>}
      </div>
    </div>
  )
}
