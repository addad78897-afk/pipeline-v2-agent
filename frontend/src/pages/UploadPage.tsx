import { UploadZone } from '@/components/upload/UploadZone'
import { FileList } from '@/components/upload/FileList'
import { Card } from '@/components/shared/Card'
import { Play, Settings, Loader2, Brain, Zap } from 'lucide-react'
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { uploadFiles } from '@/api/upload'
import { runPipeline } from '@/api/pipeline'
import { runAgent } from '@/api/agent'

export function UploadPage() {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleFilesSelected = useCallback((newFiles: File[]) => {
    setFiles((prev) => [...prev, ...newFiles])
    setError('')
  }, [])

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleStart = async (mode: 'pipeline' | 'agent' = 'pipeline') => {
    if (files.length === 0) return
    setUploading(true)
    setError('')
    try {
      // 1) 上传文件
      const { session_id } = await uploadFiles(files)
      // 2) 启动管线或Agent
      if (mode === 'agent') {
        const { job_id } = await runAgent(session_id)
        navigate(`/agent/${job_id}`)
      } else {
        const { job_id } = await runPipeline(session_id, undefined)
        navigate(`/pipeline/${job_id}`)
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || '上传失败，请重试')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto py-12 px-6 space-y-6 animate-fade-in-up">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold mb-2">上传商标侵权判决书</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          支持 .txt 格式，可批量上传多个文件。上传后将通过16步管线自动分析。
        </p>
      </div>

      <UploadZone onFilesSelected={handleFilesSelected} />

      {files.length > 0 && (
        <>
          <Card className="p-4">
            <FileList files={files} onRemove={removeFile} />
          </Card>

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-400/20 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="flex gap-3 justify-end">
            <button
              onClick={() => setFiles([])}
              disabled={uploading}
              className="px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors disabled:opacity-50"
            >
              清空
            </button>
            <button
              onClick={() => handleStart('pipeline')}
              disabled={uploading}
              className={cn(
                'flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-medium transition-colors',
                'bg-cyan-500 text-black hover:bg-cyan-400 disabled:opacity-50'
              )}
            >
              {uploading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Play size={16} />
              )}
              {uploading ? '上传中...' : '固定管线'}
            </button>
            <button
              onClick={() => handleStart('agent')}
              disabled={uploading}
              className={cn(
                'flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-medium transition-colors',
                'bg-gradient-to-r from-cyan-400 to-fuchsia-400 text-black hover:from-cyan-300 hover:to-fuchsia-300 disabled:opacity-50'
              )}
            >
              {uploading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Brain size={16} />
              )}
              {uploading ? '上传中...' : 'Agent 分析'}
            </button>
          </div>
        </>
      )}

      {files.length === 0 && (
        <Card className="p-8 text-center" hover={false}>
          <div className="flex gap-8 justify-center mb-4">
            <div className="text-center">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center mx-auto mb-2">
                <Play size={20} className="text-cyan-400" />
              </div>
              <div className="text-xs font-medium text-cyan-400">固定管线</div>
              <div className="text-[10px] text-[var(--color-text-muted)] mt-1">
                16步固定流程<br />所有文书统一处理
              </div>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/10 to-fuchsia-500/10 flex items-center justify-center mx-auto mb-2">
                <Brain size={20} className="text-fuchsia-400" />
              </div>
              <div className="text-xs font-medium text-fuchsia-400">Agent 分析</div>
              <div className="text-[10px] text-[var(--color-text-muted)] mt-1">
                逐份感知→自主规划<br />按需调用·策略自适应
              </div>
            </div>
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">
            两种模式均可从历史记录中查看结果
          </p>
        </Card>
      )}
    </div>
  )
}
