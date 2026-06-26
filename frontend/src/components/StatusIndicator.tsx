import type { DeployState } from '../types'

interface StatusIndicatorProps {
  status: DeployState
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const config = {
    idle: 'bg-slate-200 text-slate-700',
    running: 'bg-blue-100 text-blue-700',
    success: 'bg-emerald-100 text-emerald-700',
    failed: 'bg-red-100 text-red-700',
  } as const

  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${config[status]}`}>
      {status === 'running' && <span className="h-2 w-2 animate-spin rounded-full border border-current border-t-transparent" />}
      {status}
    </span>
  )
}
