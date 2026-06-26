import { useCallback, useState } from 'react'
import type { RepoName } from '../types'

export interface DeployParams {
  repo: RepoName | null
  branch: string | null
  filerIP: string | null
}

const VALID_REPOS: RepoName[] = ['nbn-daemon', 'unity']

function parseRepo(repo: string | null): RepoName | null {
  if (!repo) {
    return null
  }

  return VALID_REPOS.includes(repo as RepoName) ? (repo as RepoName) : null
}

function parseInitialParams(): DeployParams {
  const query = new URLSearchParams(window.location.search)
  return {
    repo: parseRepo(query.get('repo')),
    branch: query.get('branch'),
    filerIP: query.get('filerIP'),
  }
}

function toNullable(value: string | null | undefined): string | null {
  if (value === null || value === undefined) {
    return null
  }

  const normalized = value.trim()
  return normalized.length > 0 ? normalized : null
}

export function useQueryParams(): [DeployParams, (params: Partial<DeployParams>) => void] {
  const [params, setParams] = useState<DeployParams>(() => parseInitialParams())

  const updateParams = useCallback((nextParams: Partial<DeployParams>) => {
    setParams((previous) => {
      const updated: DeployParams = {
        ...previous,
        ...nextParams,
      }

      const query = new URLSearchParams(window.location.search)

      const repo = updated.repo
      if (repo) {
        query.set('repo', repo)
      } else {
        query.delete('repo')
      }

      const branch = toNullable(updated.branch)
      if (branch) {
        query.set('branch', branch)
      } else {
        query.delete('branch')
      }

      const filerIP = toNullable(updated.filerIP)
      if (filerIP) {
        query.set('filerIP', filerIP)
      } else {
        query.delete('filerIP')
      }

      const nextUrl = `${window.location.pathname}${query.toString() ? `?${query.toString()}` : ''}`
      window.history.replaceState(null, '', nextUrl)

      return {
        repo,
        branch,
        filerIP,
      }
    })
  }, [])

  return [params, updateParams]
}
