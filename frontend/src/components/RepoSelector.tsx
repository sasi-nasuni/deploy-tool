import type { RepoName } from '../types'

interface RepoSelectorProps {
  value: RepoName | null
  onChange: (repo: RepoName) => void
}

const REPOS: RepoName[] = ['nbn-daemon', 'unity']

export function RepoSelector({ value, onChange }: RepoSelectorProps) {
  return (
    <div className="inline-flex rounded-lg border border-slate-300 bg-white p-1 shadow-sm">
      {REPOS.map((repo) => {
        const isActive = value === repo
        return (
          <button
            key={repo}
            type="button"
            onClick={() => onChange(repo)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition ${
              isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-200'
            }`}
          >
            {repo}
          </button>
        )
      })}
    </div>
  )
}
