import { useEffect, useMemo, useState } from 'react'
import { getDeployment } from './api/client'
import { BranchDropdown } from './components/BranchDropdown'
import { DeployButton } from './components/DeployButton'
import { FilerIPInput, isValidIPv4 } from './components/FilerIPInput'
import { LogViewer } from './components/LogViewer'
import { RepoSelector } from './components/RepoSelector'
import { StatusIndicator } from './components/StatusIndicator'
import { TokenModal } from './components/TokenModal'
import { useBranches } from './hooks/useBranches'
import { useDeploy } from './hooks/useDeploy'
import { useQueryParams } from './hooks/useQueryParams'
import { useWebSocket } from './hooks/useWebSocket'
import type { RepoName } from './types'

function App() {
  const [queryParams, setQueryParams] = useQueryParams()
  const [repo, setRepo] = useState<RepoName | null>(queryParams.repo)
  const [branch, setBranch] = useState<string>(queryParams.branch ?? '')
  const [filerIP, setFilerIP] = useState<string>(queryParams.filerIP ?? '')

  const { branches, loading: branchLoading, error: branchError } = useBranches(repo)
  const { status, activeRepo, deploymentId, loading, error, startDeploy, setFinalStatus } = useDeploy()
  const { logs, connected, done, credentialPrompt, clearCredentialPrompt, submitCredential } = useWebSocket(deploymentId)

  useEffect(() => {
    setQueryParams({
      repo,
      branch,
      filerIP,
    })
  }, [branch, filerIP, repo, setQueryParams])

  useEffect(() => {
    if (!done || !deploymentId) {
      return
    }

    const loadResult = async () => {
      try {
        const deployment = await getDeployment(deploymentId)
        setFinalStatus(deployment.status === 'success' ? 'success' : 'failed')
      } catch {
        setFinalStatus('failed')
      }
    }

    void loadResult()
  }, [deploymentId, done, setFinalStatus])

  const deployDisabled = useMemo(() => {
    if (!repo || !branch || !filerIP || !isValidIPv4(filerIP)) {
      return true
    }

    return status === 'running' && activeRepo === repo
  }, [activeRepo, branch, filerIP, repo, status])

  const handleRepoChange = (nextRepo: RepoName) => {
    setRepo(nextRepo)
    setBranch('')
  }

  const handleDeploy = async () => {
    if (!repo || !branch || !filerIP || !isValidIPv4(filerIP)) {
      return
    }

    await startDeploy({
      repo,
      branch,
      filerIP,
    })
  }

  return (
    <main className="mx-auto min-h-screen w-full max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      {credentialPrompt && (
        <TokenModal
          message={credentialPrompt}
          onSubmit={submitCredential}
          onClose={clearCredentialPrompt}
        />
      )}

      <div className="rounded-xl border border-slate-300 bg-slate-50 p-6 shadow-sm">
        <div className="mb-6 flex items-center justify-between gap-4">
          <h1 className="text-2xl font-bold text-slate-900">Deploy Tool</h1>
          <StatusIndicator status={status} />
        </div>

        <div className="space-y-5">
          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">Repository</p>
            <RepoSelector value={repo} onChange={handleRepoChange} />
          </div>

          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">Branch</p>
            <BranchDropdown
              branches={branches}
              selected={branch || null}
              onSelect={setBranch}
              loading={branchLoading}
            />
            {branchError && <p className="mt-1 text-xs text-red-600">{branchError}</p>}
          </div>

          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">Filer IP</p>
            <FilerIPInput value={filerIP} onChange={setFilerIP} />
          </div>

          <div>
            <DeployButton disabled={deployDisabled} loading={loading || (status === 'running' && !done)} onClick={handleDeploy} />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
      </div>

      <div className="mt-6">
        <LogViewer
          logs={logs}
          connected={connected}
          deploymentActive={status === 'running' || done}
          done={done}
          status={status}
        />
      </div>
    </main>
  )
}

export default App
