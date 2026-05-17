import { UploadZone } from '@/components/upload/UploadZone'
import { FileList } from '@/components/upload/FileList'
import { Play, Loader2, Brain } from 'lucide-react'
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
      const { session_id } = await uploadFiles(files)
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
    <div className="max-w-2xl mx-auto py-16 px-6 animate-fade-up">
      {/* Hero */}
      <div className="text-center mb-10">
        <h2 className="text-[32px] font-bold text-[var(--color-text-primary)] tracking-tight leading-tight">
          上传判决文书
        </h2>
        <p className="mt-2 text-[15px] text-[var(--color-text-secondary)] leading-relaxed">
          支持 .txt 格式，可批量上传。系统将自动识别文书结构并智能分析。
        </p>
      </div>

      <UploadZone onFilesSelected={handleFilesSelected} />

      {files.length > 0 && (
        <div className="mt-5 space-y-4">
          <div className="apple-card p-4">
            <FileList files={files} onRemove={removeFile} />
          </div>

          {error && (
            <div className="px-4 py-3 rounded-xl bg-[var(--color-red)]/6 text-[13px] text-[var(--color-red)] font-medium">
              {error}
            </div>
          )}

          <div className="flex gap-3 justify-end">
            <button
              onClick={() => setFiles([])}
              disabled={uploading}
              className="px-5 py-2.5 text-[14px] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors disabled:opacity-40 font-medium"
            >
              清空
            </button>
            <button
              onClick={() => handleStart('pipeline')}
              disabled={uploading}
              className={cn(
                'flex items-center gap-2 px-6 py-2.5 rounded-full text-[14px] font-semibold transition-all',
                'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] shadow-sm hover:shadow-md disabled:opacity-50'
              )}
            >
              {uploading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
              {uploading ? '处理中...' : '固定管线'}
            </button>
            <button
              onClick={() => handleStart('agent')}
              disabled={uploading}
              className={cn(
                'flex items-center gap-2 px-6 py-2.5 rounded-full text-[14px] font-semibold transition-all',
                'bg-[var(--color-purple)] text-white hover:opacity-90 shadow-sm hover:shadow-md disabled:opacity-50'
              )}
            >
              {uploading ? <Loader2 size={16} className="animate-spin" /> : <Brain size={16} />}
              {uploading ? '处理中...' : 'Agent 分析'}
            </button>
          </div>
        </div>
      )}

      {files.length === 0 && (
        <div className="mt-8 grid grid-cols-2 gap-4">
          <div className="apple-card p-6 text-center">
            <div className="w-12 h-12 rounded-full bg-[var(--color-accent)]/8 flex items-center justify-center mx-auto mb-3">
              <Play size={20} className="text-[var(--color-accent)]" />
            </div>
            <div className="text-sm font-semibold text-[var(--color-text-primary)]">固定管线</div>
            <div className="text-xs text-[var(--color-text-tertiary)] mt-1">16步统一流程处理</div>
          </div>
          <div className="apple-card p-6 text-center">
            <div className="w-12 h-12 rounded-full bg-[var(--color-purple)]/8 flex items-center justify-center mx-auto mb-3">
              <Brain size={20} className="text-[var(--color-purple)]" />
            </div>
            <div className="text-sm font-semibold text-[var(--color-text-primary)]">Agent 分析</div>
            <div className="text-xs text-[var(--color-text-tertiary)] mt-1">自主感知·策略自适应</div>
          </div>
        </div>
      )}
    </div>
  )
}
