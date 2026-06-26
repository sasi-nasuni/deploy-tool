interface DeployButtonProps {
  disabled: boolean
  loading: boolean
  onClick: () => void
}

export function DeployButton({ disabled, loading, onClick }: DeployButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center justify-center rounded-md bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
    >
      {loading ? (
        <span className="inline-flex items-center gap-2">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-transparent" />
          Deploying...
        </span>
      ) : (
        'Deploy'
      )}
    </button>
  )
}
