export type RepoName = 'nbn-daemon' | 'unity'

export interface DeployRequest {
  repo: RepoName
  branch: string
  filerIP: string
}

export interface DeployResponse {
  deploymentId: string
  status: 'started'
}

export interface DeploymentStatus {
  id: string
  repo: RepoName
  branch: string
  filerIP: string
  status: 'running' | 'success' | 'failed'
  exitCode: number | null
  startedAt: string
  completedAt: string | null
}

export type LogMessageType = 'stdout' | 'stderr' | 'system' | 'credential_required'

export interface LogMessage {
  type: LogMessageType
  line: string
  timestamp: string
  done?: boolean
}

export type DeployState = 'idle' | 'running' | 'success' | 'failed'
