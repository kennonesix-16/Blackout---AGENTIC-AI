import type { ChaosEvent, TelemetrySnapshot } from '../types'

const configuredBase = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL
export const API_BASE_URL = (configuredBase || 'http://localhost:8000').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText || 'Request failed'}`)
  }
  return response.json() as Promise<T>
}

export const getHealth = () => request<unknown>('/health')
export const getState = () => request<TelemetrySnapshot>('/api/v1/state')
export const startSimulation = () => request<unknown>('/api/v1/scenario/start', { method: 'POST' })
export const resetSimulation = (seed = 42) => request<TelemetrySnapshot>('/api/v1/scenario/reset', { method: 'POST', body: JSON.stringify({ seed }) })
export const injectScenario = (event: ChaosEvent) => request<TelemetrySnapshot>('/api/v1/chaos', { method: 'POST', body: JSON.stringify(event) })

export function websocketUrl() {
  const explicit = import.meta.env.VITE_WS_BASE_URL
  if (explicit) return `${explicit.replace(/\/$/, '')}/ws/telemetry`
  return `${API_BASE_URL.replace(/^http/, 'ws')}/ws/telemetry`
}

export type { ChaosEvent }
