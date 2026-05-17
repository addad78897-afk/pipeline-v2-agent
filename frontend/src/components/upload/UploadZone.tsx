import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload } from 'lucide-react'
import { cn } from '@/utils/cn'

interface UploadZoneProps { onFilesSelected: (files: File[]) => void }

export function UploadZone({ onFilesSelected }: UploadZoneProps) {
  const onDrop = useCallback((accepted: File[]) => {
    const txtFiles = accepted.filter((f) => f.name.endsWith('.txt') || f.type === 'text/plain')
    if (txtFiles.length > 0) onFilesSelected(txtFiles)
  }, [onFilesSelected])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'text/plain': ['.txt'] }, multiple: true,
  })

  return (
    <div
      {...getRootProps()}
      className={cn(
        'relative border-2 border-dashed rounded-2xl p-14 text-center cursor-pointer transition-all duration-300',
        isDragActive
          ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/4 scale-[1.01]'
          : 'border-[var(--color-border)] bg-white hover:border-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-tertiary)]'
      )}
    >
      <input {...getInputProps()} />
      <div className={cn('w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center transition-colors', isDragActive ? 'bg-[var(--color-accent)]/10' : 'bg-[var(--color-bg-primary)]')}>
        <Upload size={26} className={isDragActive ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-tertiary)]'} />
      </div>
      {isDragActive ? (
        <p className="text-[15px] text-[var(--color-accent)] font-semibold">松开以上传文件</p>
      ) : (
        <>
          <p className="text-[15px] text-[var(--color-text-secondary)] mb-1">
            拖拽 <span className="text-[var(--color-text-primary)] font-semibold">.txt</span> 文件到此处
          </p>
          <p className="text-[13px] text-[var(--color-text-tertiary)]">或点击选择文件 · 支持批量上传</p>
        </>
      )}
    </div>
  )
}
