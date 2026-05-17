import { FileText, X } from 'lucide-react'

interface FileListProps {
  files: File[]
  onRemove: (index: number) => void
}

export function FileList({ files, onRemove }: FileListProps) {
  const totalSize = files.reduce((sum, f) => sum + f.size, 0)
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-[var(--color-text-secondary)]">
          {files.length} 个文件 · {formatSize(totalSize)}
        </span>
      </div>
      <div className="space-y-1 max-h-64 overflow-auto">
        {files.map((file, i) => (
          <div key={`${file.name}-${i}`} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors group">
            <FileText size={16} className="text-[var(--color-text-muted)] shrink-0" />
            <span className="text-sm text-[var(--color-text-primary)] truncate flex-1">{file.name}</span>
            <span className="text-xs text-[var(--color-text-muted)] shrink-0">{formatSize(file.size)}</span>
            <button
              onClick={() => onRemove(i)}
              className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/10 hover:text-red-400 transition-all text-[var(--color-text-muted)]"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
