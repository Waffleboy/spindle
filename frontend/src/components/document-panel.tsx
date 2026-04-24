import { useState, useCallback, useRef } from "react"
import { cn } from "@/lib/utils"
import type { DocumentType } from "@/lib/types"
import { Button } from "./ui/button"
import { ScrollArea } from "./ui/scroll-area"
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle2,
  File,
  X,
  Trash2,
} from "lucide-react"

interface DocumentPanelProps {
  documents: DocumentType[]
  selectedDocId: string | null
  onSelectDoc: (id: string | null) => void
  onUploadAndProcess: (files: File[], companyContext?: string) => Promise<void>
  onClearAll: () => Promise<void>
  onDeleteDocument: (id: string) => Promise<void>
  isProcessing: boolean
}

export function DocumentPanel({
  documents,
  selectedDocId,
  onSelectDoc,
  onUploadAndProcess,
  onClearAll,
  onDeleteDocument,
  isProcessing,
}: DocumentPanelProps) {
  const [dragOver, setDragOver] = useState(false)
  const [stagedFiles, setStagedFiles] = useState<File[]>([])
  const [companyContext, setCompanyContext] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      setStagedFiles((prev) => [...prev, ...files])
    }
  }, [])

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? [])
      if (files.length > 0) {
        setStagedFiles((prev) => [...prev, ...files])
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    },
    []
  )

  const removeFile = useCallback((index: number) => {
    setStagedFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleProcess = async () => {
    if (stagedFiles.length === 0) return
    await onUploadAndProcess(
      stagedFiles,
      companyContext.trim() || undefined
    )
    setStagedFiles([])
    setCompanyContext("")
  }

  const getFileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase()
    if (ext === "pdf") return <FileText className="h-4 w-4 text-rose-400" />
    if (ext === "docx" || ext === "doc")
      return <FileText className="h-4 w-4 text-blue-400" />
    if (ext === "xlsx" || ext === "xls" || ext === "csv")
      return <FileText className="h-4 w-4 text-emerald-400" />
    return <File className="h-4 w-4 text-zinc-400" />
  }

  return (
    <div className="flex h-full w-72 flex-col border-r border-zinc-800 bg-zinc-900/30">
      <div className="border-b border-zinc-800 p-4">
        <h2 className="text-sm font-semibold text-zinc-200">Documents</h2>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Upload zone */}
        <div className="p-3 space-y-3">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              "relative flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-all",
              dragOver
                ? "border-indigo-500 bg-indigo-500/10 animate-pulse-border"
                : "border-zinc-700 bg-zinc-800/30 hover:border-zinc-600 hover:bg-zinc-800/50"
            )}
          >
            <Upload
              className={cn(
                "h-8 w-8 mb-2",
                dragOver ? "text-indigo-400" : "text-zinc-500"
              )}
            />
            <span className="text-xs text-zinc-400 text-center">
              Drop files here or click to browse
            </span>
            <span className="text-[10px] text-zinc-600 mt-1">
              PDF, DOCX, XLSX, CSV
            </span>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.xlsx,.xls,.csv"
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>

          {/* Staged files */}
          {stagedFiles.length > 0 && (
            <div className="space-y-1">
              <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
                Ready to process ({stagedFiles.length})
              </span>
              {stagedFiles.map((file, idx) => (
                <div
                  key={`${file.name}-${idx}`}
                  className="flex items-center gap-2 rounded-md bg-zinc-800/50 px-2 py-1.5 text-xs"
                >
                  {getFileIcon(file.name)}
                  <span className="flex-1 truncate text-zinc-300">
                    {file.name}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      removeFile(idx)
                    }}
                    className="text-zinc-600 hover:text-zinc-400"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Company context */}
          <textarea
            placeholder="Company context (optional)..."
            value={companyContext}
            onChange={(e) => setCompanyContext(e.target.value)}
            className="w-full rounded-md border border-zinc-700 bg-zinc-800/50 p-2 text-xs text-zinc-300 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none"
            rows={2}
          />

          <Button
            onClick={handleProcess}
            disabled={stagedFiles.length === 0 || isProcessing}
            className="w-full"
          >
            {isProcessing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Process {stagedFiles.length > 0 ? `(${stagedFiles.length})` : ""}
              </>
            )}
          </Button>
        </div>

        {/* Document list */}
        <div className="flex-1 overflow-hidden">
          {documents.length > 0 && (
            <div className="flex items-center justify-between border-t border-zinc-800 px-3 py-2">
              <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
                Uploaded ({documents.length})
              </span>
              <button
                onClick={onClearAll}
                disabled={isProcessing}
                className="text-[10px] text-zinc-600 hover:text-red-400 transition-colors disabled:opacity-50"
                title="Clear all documents"
              >
                Clear all
              </button>
            </div>
          )}
          <ScrollArea className="h-full px-3 pb-3">
            <div className="space-y-1">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() =>
                    onSelectDoc(selectedDocId === doc.id ? null : doc.id)
                  }
                  className={cn(
                    "group flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-xs transition-colors",
                    selectedDocId === doc.id
                      ? "bg-indigo-500/10 border border-indigo-500/30 text-indigo-300"
                      : "hover:bg-zinc-800/50 text-zinc-400"
                  )}
                >
                  {getFileIcon(doc.original_filename)}
                  <div className="flex-1 min-w-0">
                    <div className="truncate font-medium text-zinc-300">
                      {doc.original_filename}
                    </div>
                    <div className="text-[10px] text-zinc-600">
                      {doc.detected_doc_type ?? doc.file_type}
                      {doc.page_count ? ` - ${doc.page_count} pages` : ""}
                    </div>
                  </div>
                  {doc.processed_at ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0" />
                  ) : isProcessing ? (
                    <Loader2 className="h-3.5 w-3.5 text-zinc-600 animate-spin flex-shrink-0" />
                  ) : null}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteDocument(doc.id)
                    }}
                    disabled={isProcessing}
                    className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 transition-all disabled:opacity-50 flex-shrink-0"
                    title="Remove document"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  )
}
