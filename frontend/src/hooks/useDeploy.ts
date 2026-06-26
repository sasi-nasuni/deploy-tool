import { useCallback, useState } from 'react'
import { deploy } from '../api/client'
import type { DeployRequest, DeployState, RepoName } from '../types'

interface UseDeployReturn {
  status: DeployState
  activeRepo: RepoName | null
  deploymentId: string | null
  loading: boolean
  error: string | null
  startDeploy: (request: DeployRequest) => Promise<void>
  setFinalStatus: (status: Extract<DeployState, 'success' | 'failed'>) => void
}

export function useDeploy(): UseDeployReturn {
  const [status, setStatus] = useState<DeployState>('idle')
  const [activeRepo, setActiveRepo] = useState<RepoName | null>(null)
  const [deploymentId, setDeploymentId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const startDeploy = useCallback(async (request: DeployRequest) => {
    setStatus('running')
    setActiveRepo(request.repo)
    setDeploymentId(null)
    setError(null)

    try {
      const response = await deploy(request.repo, request.branch, request.filerIP)
      setDeploymentId(response.deploymentId)
    } catch (err) {
      setStatus('failed')
      setError(err instanceof Error ? err.message : 'Failed to start deployment')
    }
  }, [])

  const setFinalStatus = useCallback((nextStatus: Extract<DeployState, 'success' | 'failed'>) => {
    setStatus(nextStatus)
  }, [])

  return {
    status,
    activeRepo,
    deploymentId,
    loading: status === 'running' && deploymentId === null,
    error,
    startDeploy,
    setFinalStatus,
  }
}
