import { FileText, X } from 'lucide-react'

interface FileListProps { files: File[]; onRemove: (index: number) => void }

export function FileList({ files, onRemove }: FileListProps) {
  const totalSize = files.reduce((s, f) => s + f.size, 0)
  const fmt = (b: number) => b < 1024 ? `${b} B` : b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(1)} MB`

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] text-[var(--color-text-secondary)] font-medium">
          {files.length} 个文件 · {fmt(totalSize)}
        </span>
      </div>
      <div className="space-y-0.5 max-h-64 overflow-auto">
        {files.map((file, i) => (
          <div key={`${file.name}-${i}`} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-black/[0.03] transition-colors group">
            <FileText size={15} className="text-[var(--color-text-tertiary)] shrink-0" />
            <span className="text-[13px] text-[var(--color-text-primary)] truncate flex-1">{file.name}</span>
            <span className="text-[12px] text-[var(--color-text-tertiary)] shrink-0">{fmt(file.size)}</span>
            <button onClick={() => onRemove(i)} className="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-[var(--color-red)]/10 hover:text-[var(--color-red)] transition-all text-[var(--color-text-tertiary)]">
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
