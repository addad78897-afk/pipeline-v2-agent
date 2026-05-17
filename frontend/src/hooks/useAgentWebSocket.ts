import { useEffect, useRef, useCallback } from 'react'
import { useAgentStore } from '@/store/agentStore'

export function useAgentWebSocket(jobId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const {
    setJob, addThought, addToolComplete, addToolError,
    addDocComplete, setAgentComplete, setConnected,
    incrementDocumentsProcessed,
  } = useAgentStore()

  const connect = useCallback(() => {
    if (!jobId) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/api/ws/agent/${jobId}`)

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
        case 'agent_thought':
          addThought({
            timestamp: msg.timestamp,
            thought: msg.thought,
            phase: msg.phase,
            documentIndex: msg.document_index,
            profile: msg.profile,
            plan: msg.plan,
          })
          break

        case 'tool_start':
          // tool_start is optional to handle; complete/error are the important ones
          break

        case 'tool_complete':
          addToolComplete({
            timestamp: msg.timestamp,
            documentIndex: msg.document_index,
            tool_id: msg.tool_id,
            tool_name: msg.tool_name,
            phase: msg.phase || 0,
            duration_seconds: msg.duration_seconds,
            output_summary: msg.output_summary,
            verified: msg.verified,
          })
          break

        case 'tool_error':
          addToolError({
            timestamp: msg.timestamp,
            documentIndex: msg.document_index,
            tool_id: msg.tool_id,
            tool_name: msg.tool_name,
            phase: msg.phase || 0,
            error: msg.error,
            will_retry: msg.will_retry,
          })
          break

        case 'document_complete':
          addDocComplete({
            document_index: msg.document_index,
            filename: msg.filename,
            quality_score: msg.quality_score,
            strategy_used: msg.strategy_used,
            tools_run: msg.tools_run,
            errors: msg.errors,
          })
          incrementDocumentsProcessed()
          break

        case 'agent_complete':
          if (!msg.error) {
            setAgentComplete({
              total_files: msg.total_files,
              total_tools_run: msg.total_tools_run,
              total_llm_calls_saved: msg.total_llm_calls_saved,
              total_duration_seconds: msg.total_duration_seconds,
              avg_duration_per_doc: msg.avg_duration_per_doc,
            })
          } else {
            useAgentStore.setState({ jobStatus: 'FAILED' })
          }
          break
      }
    }

    ws.onclose = () => {
      setConnected(false)
      reconnectTimer.current = setTimeout(() => connect(), 2000)
    }

    ws.onerror = () => ws.close()
    wsRef.current = ws
  }, [jobId, setConnected, addThought, addToolComplete, addToolError, addDocComplete, setAgentComplete, incrementDocumentsProcessed])

  useEffect(() => {
    if (jobId) {
      connect()
    }
    return () => {
      wsRef.current?.close()
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }
  }, [jobId, connect])

  return { disconnect: () => wsRef.current?.close() }
}
