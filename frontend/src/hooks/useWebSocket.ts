import { useEffect, useRef, useCallback } from 'react'
import { usePipelineStore } from '@/store/pipelineStore'
import { STEPS, type StepState } from '@/utils/constants'

export function useWebSocket(jobId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const { setJob, updateProgress, updateStep, setConnected, steps } = usePipelineStore()

  const connect = useCallback(() => {
    if (!jobId) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/pipeline/${jobId}`)

    ws.onopen = () => {
      setConnected(true)
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
        reconnectTimer.current = undefined
      }
    }

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)

      switch (msg.type) {
        case 'progress': {
          const stepNum = msg.step
          updateProgress(msg.progress_percent, stepNum)

          // 初始化步骤状态（如未初始化）
          const existing = steps.find((s) => s.number === stepNum)
          if (!existing || existing.status === 'PENDING') {
            updateStep(stepNum, {
              status: 'RUNNING',
              startedAt: new Date(msg.timestamp * 1000).toISOString(),
            })
          }
          break
        }

        case 'step_complete': {
          updateStep(msg.step, {
            status: 'COMPLETED',
            completedAt: new Date().toISOString(),
          })
          break
        }

        case 'step_error': {
          updateStep(msg.step, {
            status: 'FAILED',
            error: msg.error_message,
          })
          break
        }

        case 'pipeline_complete': {
          usePipelineStore.setState({ jobStatus: 'COMPLETED', progressPercent: 100 })
          break
        }
      }
    }

    ws.onclose = () => {
      setConnected(false)
      // 指数退避重连
      reconnectTimer.current = setTimeout(() => {
        connect()
      }, 2000)
    }

    ws.onerror = () => {
      ws.close()
    }

    wsRef.current = ws
  }, [jobId, setConnected, updateProgress, updateStep, steps])

  useEffect(() => {
    if (jobId) {
      setJob(jobId)
      connect()
    }
    return () => {
      wsRef.current?.close()
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }
  }, [jobId, connect, setJob])

  return { disconnect: () => wsRef.current?.close() }
}
