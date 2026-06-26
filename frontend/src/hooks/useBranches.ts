import { useCallback, useEffect, useState } from 'react'
import { getBranches } from '../api/client'
import type { RepoName } from '../types'

export function useBranches(repo: RepoName | null) {
  const [branches, setBranches] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchBranches = useCallback(async () => {
    if (!repo) {
      setBranches([])
      setError(null)
      return
    }

    try {
      setLoading(true)
      setError(null)
      const fetched = await getBranches(repo)
      setBranches(fetched)
    } catch (err) {
      setBranches([])
      setError(err instanceof Error ? err.message : 'Failed to load branches')
    } finally {
      setLoading(false)
    }
  }, [repo])

  useEffect(() => {
    void fetchBranches()
  }, [fetchBranches])

  return { branches, loading, error, refresh: fetchBranches }
}
