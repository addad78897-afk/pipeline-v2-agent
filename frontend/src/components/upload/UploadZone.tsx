import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText } from 'lucide-react'
import { cn } from '@/utils/cn'

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void
}

export function UploadZone({ onFilesSelected }: UploadZoneProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      const txtFiles = accepted.filter((f) => f.name.endsWith('.txt') || f.type === 'text/plain')
      if (txtFiles.length > 0) onFilesSelected(txtFiles)
    },
    [onFilesSelected]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/plain': ['.txt'] },
    multiple: true,
  })

  return (
    <div
      {...getRootProps()}
      className={cn(
        'relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200',
        isDragActive
          ? 'border-cyan-400 bg-cyan-500/5'
          : 'border-[var(--color-border-accent)] hover:border-[var(--color-text-muted)] bg-[var(--color-bg-card)]'
      )}
    >
      <input {...getInputProps()} />
      <div className={cn('w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center transition-colors', isDragActive ? 'bg-cyan-500/10' : 'bg-white/5')}>
        <Upload size={28} className={isDragActive ? 'text-cyan-400' : 'text-[var(--color-text-muted)]'} />
      </div>
      {isDragActive ? (
        <p className="text-cyan-400 font-medium">松开以上传文件</p>
      ) : (
        <>
          <p className="text-sm text-[var(--color-text-secondary)] mb-1">
            拖拽 <span className="text-[var(--color-text-primary)]">.txt</span> 判决书文件到此处
          </p>
          <p className="text-xs text-[var(--color-text-muted)]">
            或点击选择文件 · 支持批量上传
          </p>
        </>
      )}
    </div>
  )
}
