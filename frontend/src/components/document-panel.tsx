import { useState, useCallback, useRef, useMemo } from "react"
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
  Calendar,
  Globe,
  Database,
  FolderUp,
  ArrowLeft,
} from "lucide-react"

interface DocumentPanelProps {
  documents: DocumentType[]
  selectedDocId: string | null
  onSelectDoc: (id: string | null) => void
  onUploadAndProcess: (files: File[], companyContext?: string, splitRows?: boolean) => Promise<void>
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
  const [splitRows, setSplitRows] = useState(false)
  const [uploadSource, setUploadSource] = useState<"select" | "sharepoint" | "database" | "manual">("select")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const hasCsvFiles = stagedFiles.some((f) => f.name.toLowerCase().endsWith(".csv"))

  // Sort documents by report_date (preferred) or uploaded_at, most recent first
  const sortedDocuments = useMemo(() => {
    return [...documents].sort((a, b) => {
      const dateA = a.report_date ?? a.uploaded_at
      const dateB = b.report_date ?? b.uploaded_at
      return new Date(dateB).getTime() - new Date(dateA).getTime()
    })
  }, [documents])

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
      companyContext.trim() || undefined,
      splitRows || undefined
    )
    setStagedFiles([])
    setCompanyContext("")
    setSplitRows(false)
  }

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return dateStr
    const day = date.getDate()
    const month = date.toLocaleString("en-US", { month: "short" })
    const year = date.getFullYear()
    return `${day} ${month} ${year}`
  }

  const getDocDateLabel = (doc: DocumentType): { label: string; isApproximate: boolean } => {
    if (doc.report_date) {
      return { label: formatDate(doc.report_date), isApproximate: false }
    }
    return { label: `uploaded ${formatDate(doc.uploaded_at)}`, isApproximate: true }
  }

  const getFileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase()
    if (ext === "pdf") return <FileText className="h-4 w-4 text-rose-400" />
    if (ext === "docx" || ext === "doc")
      return <FileText className="h-4 w-4 text-blue-400" />
    if (ext === "xlsx" || ext === "xls" || ext === "csv")
      return <FileText className="h-4 w-4 text-emerald-400" />
    return <File className="h-4 w-4 text-muted-foreground" />
  }

  return (
    <div className="flex h-full w-72 flex-col border-r border-border bg-card">
      <div className="border-b border-border p-4">
        <h2 className="text-sm font-semibold text-foreground">Documents</h2>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Source selection / Upload zone */}
        <div className="p-3 space-y-3">
          {uploadSource === "select" ? (
            <div className="space-y-2">
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                Import from
              </span>
              {[
                { key: "sharepoint" as const, label: "Sharepoint", icon: Globe, desc: "Connect to Sharepoint" },
                { key: "database" as const, label: "Database", icon: Database, desc: "Import from database" },
                { key: "manual" as const, label: "Manual Upload", icon: FolderUp, desc: "Upload local files" },
              ].map(({ key, label, icon: Icon, desc }) => (
                <button
                  key={key}
                  onClick={() => setUploadSource(key)}
                  className="flex w-full items-center gap-3 rounded-lg border border-border bg-muted/50 px-3 py-3 text-left transition-all hover:border-primary/50 hover:bg-muted"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10">
                    <Icon className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <div className="text-xs font-medium text-foreground">{label}</div>
                    <div className="text-[10px] text-muted-foreground">{desc}</div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <>
              <button
                onClick={() => setUploadSource("select")}
                className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
              >
                <ArrowLeft className="h-3 w-3" />
                Back to sources
              </button>

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  "relative flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-all",
                  dragOver
                    ? "border-primary bg-primary/10 animate-pulse-border"
                    : "border-border bg-muted/50 hover:border-primary/50 hover:bg-muted"
                )}
              >
                <Upload
                  className={cn(
                    "h-8 w-8 mb-2",
                    dragOver ? "text-primary" : "text-muted-foreground"
                  )}
                />
                <span className="text-xs text-muted-foreground text-center">
                  Drop files here or click to browse
                </span>
                <span className="text-[10px] text-muted-foreground/70 mt-1">
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
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                    Ready to process ({stagedFiles.length})
                  </span>
                  {stagedFiles.map((file, idx) => (
                    <div
                      key={`${file.name}-${idx}`}
                      className="flex items-center gap-2 rounded-md bg-muted/50 px-2 py-1.5 text-xs"
                    >
                      {getFileIcon(file.name)}
                      <span className="flex-1 truncate text-foreground">
                        {file.name}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          removeFile(idx)
                        }}
                        className="text-muted-foreground hover:text-foreground"
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
                className="w-full rounded-md border border-border bg-muted/50 p-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
                rows={2}
              />

              {hasCsvFiles && (
                <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={splitRows}
                    onChange={(e) => setSplitRows(e.target.checked)}
                    className="rounded border-border accent-primary h-3.5 w-3.5"
                  />
                  Each CSV row is a separate document
                </label>
              )}

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
            </>
          )}
        </div>

        {/* Document list */}
        <div className="flex-1 overflow-hidden">
          {documents.length > 0 && (
            <div className="flex items-center justify-between border-t border-border px-3 py-2">
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                Uploaded ({documents.length})
              </span>
              <button
                onClick={onClearAll}
                disabled={isProcessing}
                className="text-[10px] text-muted-foreground hover:text-destructive transition-colors disabled:opacity-50"
                title="Clear all documents"
              >
                Clear all
              </button>
            </div>
          )}
          <ScrollArea className="h-full px-3 pb-3">
            <div className="space-y-1">
              {sortedDocuments.map((doc) => {
                const dateInfo = getDocDateLabel(doc)
                return (
                <button
                  key={doc.id}
                  onClick={() =>
                    onSelectDoc(selectedDocId === doc.id ? null : doc.id)
                  }
                  className={cn(
                    "group flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-xs transition-colors",
                    selectedDocId === doc.id
                      ? "bg-primary/10 border border-primary/30 text-primary"
                      : "hover:bg-muted text-muted-foreground"
                  )}
                >
                  {getFileIcon(doc.original_filename)}
                  <div className="flex-1 min-w-0">
                    <div className="truncate font-medium text-foreground">
                      {doc.original_filename}
                    </div>
                    <div className="text-[10px] text-muted-foreground/70">
                      {doc.detected_doc_type ?? doc.file_type}
                      {doc.page_count ? ` - ${doc.page_count} pages` : ""}
                    </div>
                    <div className="flex items-center gap-1 mt-0.5">
                      <Calendar className="h-2.5 w-2.5 text-muted-foreground/60 flex-shrink-0" />
                      <span
                        className={cn(
                          "text-[10px]",
                          dateInfo.isApproximate
                            ? "text-muted-foreground/50 italic"
                            : "text-muted-foreground/70"
                        )}
                      >
                        {dateInfo.label}
                      </span>
                    </div>
                  </div>
                  {doc.processed_at ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0" />
                  ) : isProcessing ? (
                    <Loader2 className="h-3.5 w-3.5 text-muted-foreground animate-spin flex-shrink-0" />
                  ) : null}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteDocument(doc.id)
                    }}
                    disabled={isProcessing}
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-all disabled:opacity-50 flex-shrink-0"
                    title="Remove document"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </button>
                )
              })}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  )
}
