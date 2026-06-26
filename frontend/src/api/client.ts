import type { DeploymentStatus, DeployRequest, DeployResponse, RepoName } from '../types'

export const API_BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    ...init,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Request failed with status ${response.status}`)
  }

  return (await response.json()) as T
}

export async function deploy(repo: string, branch: string, filerIP: string): Promise<{ deploymentId: string }> {
  const payload: DeployRequest = {
    repo: repo as RepoName,
    branch,
    filerIP,
  }

  const response = await request<DeployResponse>('/deploy', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

  return { deploymentId: response.deploymentId }
}

export async function getBranches(repo: string): Promise<string[]> {
  const result = await request<{ branches?: string[] } | string[]>(`/branches/${encodeURIComponent(repo)}`)
  if (Array.isArray(result)) {
    return result
  }

  return result.branches ?? []
}

export async function getStatus(): Promise<{ status: string; repos: Record<string, boolean>; docker: boolean }> {
  return request('/status')
}

export async function getDeployment(id: string): Promise<DeploymentStatus> {
  return request(`/deployments/${encodeURIComponent(id)}`)
}
