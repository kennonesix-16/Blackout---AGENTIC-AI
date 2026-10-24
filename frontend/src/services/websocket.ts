import { websocketUrl } from './api'

export interface TelemetrySocketOptions<T> {
  onMessage: (value: T) => void
  onStatus: (connected: boolean) => void
  onError: (message: string) => void
}

export function createTelemetrySocket<T>({ onMessage, onStatus, onError }: TelemetrySocketOptions<T>) {
  let socket: WebSocket | undefined
  let retryTimer: number | undefined
  let stopped = false
  let retryMs = 1000

  const connect = () => {
    if (stopped) return
    try {
      socket = new WebSocket(websocketUrl())
      socket.onopen = () => {
        retryMs = 1000
        onStatus(true)
      }
      socket.onmessage = (event) => {
        try {
          onMessage(JSON.parse(event.data) as T)
        } catch {
          onError('Live telemetry returned invalid JSON.')
        }
      }
      socket.onerror = () => {
        onStatus(false)
        onError('Live telemetry unavailable. Retrying…')
      }
      socket.onclose = () => {
        onStatus(false)
        if (!stopped) {
          retryTimer = window.setTimeout(connect, retryMs)
          retryMs = Math.min(retryMs * 2, 8000)
        }
      }
    } catch {
      onStatus(false)
      onError('Unable to open the telemetry socket.')
      retryTimer = window.setTimeout(connect, retryMs)
    }
  }

  connect()

  return () => {
    stopped = true
    if (retryTimer) window.clearTimeout(retryTimer)
    socket?.close()
  }
}
