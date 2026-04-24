import { useState, useEffect, useCallback, useRef } from "react"
import type {
  DocumentType,
  TaxonomyType,
  TaxonomyTemplateType,
  ExtractionType,
  EntityType,
  ContradictionType,
  PipelineStatus,
} from "@/lib/types"
import {
  uploadDocuments,
  processDocuments,
  getStatus,
  getDocuments,
  clearAllDocuments,
  deleteDocument,
  getTaxonomy,
  getTaxonomyTemplates,
  getExtractions,
  getEntities,
  getContradictions,
} from "@/lib/api"
import { DocumentPanel } from "@/components/document-panel"
import { TaxonomyPanel } from "@/components/taxonomy-panel"
import { TemplatesPanel } from "@/components/templates-panel"
import { ChatPanel } from "@/components/chat-panel"
import { TopBar } from "@/components/top-bar"
import { TooltipProvider } from "@/components/ui/tooltip"
import {
  NotificationProvider,
  useNotifications,
} from "@/lib/notifications"
import { NotificationDisplay } from "@/components/notifications"

function AppContent() {
  const [documents, setDocuments] = useState<DocumentType[]>([])
  const [taxonomy, setTaxonomy] = useState<TaxonomyType | null>(null)
  const [extractions, setExtractions] = useState<ExtractionType[]>([])
  const [entities, setEntities] = useState<EntityType[]>([])
  const [contradictions, setContradictions] = useState<ContradictionType[]>([])
  const [templates, setTemplates] = useState<TaxonomyTemplateType[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [centerTab, setCenterTab] = useState<"taxonomy" | "templates">("taxonomy")
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(
    null
  )
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastProcessedRef = useRef<{ documentIds: string[]; companyContext?: string } | null>(null)
  const { addNotification } = useNotifications()

  const fetchAllData = useCallback(async () => {
    try {
      const [docs, tax, ext, ent, cont, tmpls] = await Promise.all([
        getDocuments(),
        getTaxonomy(),
        getExtractions(),
        getEntities(),
        getContradictions(),
        getTaxonomyTemplates(),
      ])
      setDocuments(docs)
      setTaxonomy(tax)
      setExtractions(ext)
      setEntities(ent)
      setContradictions(cont)
      setTemplates(tmpls)
    } catch (err) {
      console.error("Failed to fetch data:", err)
    }
  }, [])

  const retryProcessing = useCallback(async () => {
    const last = lastProcessedRef.current
    if (!last) return
    try {
      await processDocuments(last.documentIds, last.companyContext)
      setIsProcessing(true)
      setPipelineStatus({
        status: "processing",
        current_step: "type_detection",
        steps_completed: [],
        total_documents: last.documentIds.length,
        processed_documents: 0,
      })
      addNotification({
        type: "info",
        title: "Retrying processing",
        message: "Re-running the pipeline on the same documents",
      })
    } catch (err) {
      addNotification({
        type: "error",
        title: "Retry failed",
        message: err instanceof Error ? err.message : "Failed to retry processing",
      })
    }
  }, [addNotification])

  // Poll pipeline status when processing
  useEffect(() => {
    if (isProcessing) {
      pollingRef.current = setInterval(async () => {
        try {
          const status = await getStatus()
          setPipelineStatus(status)

          if (
            status.status === "completed" ||
            status.status === "idle" ||
            status.status === "error"
          ) {
            setIsProcessing(false)
            setPipelineStatus(
              status.status === "completed" ? status : null
            )
            if (status.status === "error") {
              addNotification({
                type: "error",
                title: "Processing failed",
                message: status.error
                  ? status.error.split("\n")[0]
                  : "The pipeline encountered an error during processing",
                actionLabel: "Retry",
                onAction: retryProcessing,
                duration: 0,
              })
            } else if (status.status === "completed") {
              addNotification({
                type: "success",
                title: "Processing complete",
                message: "All documents have been processed successfully",
              })
            }
            await fetchAllData()
          }
        } catch (err) {
          console.error("Status poll failed:", err)
        }
      }, 2000)
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [isProcessing, fetchAllData, addNotification, retryProcessing])

  // Initial data load
  useEffect(() => {
    fetchAllData()
  }, [fetchAllData])

  const handleClearAll = async () => {
    try {
      await clearAllDocuments()
      await fetchAllData()
      setSelectedDocId(null)
      addNotification({
        type: "info",
        title: "Documents cleared",
        message: "All documents and associated data have been removed",
      })
    } catch (err) {
      addNotification({
        type: "error",
        title: "Failed to clear documents",
        message: err instanceof Error ? err.message : "Unknown error",
      })
    }
  }

  const handleDeleteDocument = async (documentId: string) => {
    try {
      await deleteDocument(documentId)
      if (selectedDocId === documentId) setSelectedDocId(null)
      await fetchAllData()
    } catch (err) {
      addNotification({
        type: "error",
        title: "Failed to delete document",
        message: err instanceof Error ? err.message : "Unknown error",
      })
    }
  }

  const handleUploadAndProcess = async (
    files: File[],
    companyContext?: string
  ) => {
    try {
      const uploadResult = await uploadDocuments(files, companyContext)
      // Immediately refresh documents list
      const docs = await getDocuments()
      setDocuments(docs)

      // Start processing
      lastProcessedRef.current = { documentIds: uploadResult.document_ids, companyContext }
      await processDocuments(uploadResult.document_ids, companyContext)
      setIsProcessing(true)
      setPipelineStatus({
        status: "processing",
        current_step: "type_detection",
        steps_completed: [],
        total_documents: uploadResult.document_ids.length,
        processed_documents: 0,
      })
      addNotification({
        type: "success",
        title: "Processing started",
        message: "Your documents are being processed",
      })
    } catch (err) {
      console.error("Upload/process failed:", err)
      setIsProcessing(false)
      addNotification({
        type: "error",
        title: "Upload failed",
        message:
          err instanceof Error
            ? err.message
            : "Failed to upload documents",
      })
    }
  }

  return (
    <TooltipProvider>
      <div className="flex h-screen flex-col overflow-hidden bg-zinc-950">
        {/* Top bar with title and pipeline progress */}
        <header className="flex items-center justify-between border-b border-zinc-800 px-6 py-3">
          <div className="flex items-center gap-3">
            <svg width="36" height="36" viewBox="20 30 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M 28 38 C 40 55, 60 70, 92 95" stroke="#c49a6c" strokeWidth="2.5" strokeLinecap="round" fill="none" opacity="0.6"/>
              <path d="M 172 32 C 155 52, 130 72, 108 94" stroke="#d4a574" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.6"/>
              <path d="M 18 118 C 38 112, 62 106, 90 100" stroke="#b87333" strokeWidth="2.8" strokeLinecap="round" fill="none" opacity="0.6"/>
              <path d="M 182 128 C 160 120, 134 110, 110 102" stroke="#c49a6c" strokeWidth="2.2" strokeLinecap="round" fill="none" opacity="0.6"/>
              <path d="M 52 178 C 62 158, 78 132, 95 108" stroke="#6aaa9c" strokeWidth="1.8" strokeLinecap="round" fill="none" opacity="0.5"/>
              <path d="M 152 182 C 142 160, 124 134, 106 108" stroke="#c47a7a" strokeWidth="1.8" strokeLinecap="round" fill="none" opacity="0.5"/>
              <path d="M 100 82 L 114 100 L 100 118 L 86 100 Z" fill="#c49a6c"/>
              <circle cx="28" cy="38" r="5" fill="#c49a6c" opacity="0.7"/>
              <circle cx="172" cy="32" r="4.5" fill="#d4a574" opacity="0.6"/>
              <circle cx="18" cy="118" r="5.5" fill="#b87333" opacity="0.7"/>
              <circle cx="182" cy="128" r="4.5" fill="#c49a6c" opacity="0.6"/>
              <circle cx="52" cy="178" r="4.5" fill="#6aaa9c" opacity="0.6"/>
            </svg>
            <div>
              <h1 className="text-lg text-zinc-100" style={{ fontFamily: "'Instrument Serif', serif", letterSpacing: '0.03em' }}>
                Spindle
              </h1>
              <p className="text-[10px] text-zinc-500 tracking-widest uppercase" style={{ fontWeight: 300 }}>
                Structure from chaos
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs text-zinc-500">
            {documents.length > 0 && (
              <span>
                {documents.filter((d) => d.processed_at).length}/
                {documents.length} processed
              </span>
            )}
          </div>
        </header>

        {/* Pipeline progress bar */}
        <TopBar pipelineStatus={pipelineStatus} isProcessing={isProcessing} />

        {/* Main content: three-panel layout */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left panel: Documents */}
          <DocumentPanel
            documents={documents}
            selectedDocId={selectedDocId}
            onSelectDoc={setSelectedDocId}
            onUploadAndProcess={handleUploadAndProcess}
            onClearAll={handleClearAll}
            onDeleteDocument={handleDeleteDocument}
            isProcessing={isProcessing}
          />

          {/* Main panel: Taxonomy Dashboard / Templates */}
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Tab switcher */}
            <div className="flex border-b border-zinc-800 bg-zinc-900/30">
              <button
                onClick={() => setCenterTab("taxonomy")}
                className={`px-4 py-2 text-xs font-medium transition-colors ${
                  centerTab === "taxonomy"
                    ? "text-zinc-200 border-b-2 border-indigo-500"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Taxonomy
              </button>
              <button
                onClick={() => setCenterTab("templates")}
                className={`px-4 py-2 text-xs font-medium transition-colors ${
                  centerTab === "templates"
                    ? "text-zinc-200 border-b-2 border-indigo-500"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Templates
                {templates.length > 0 && (
                  <span className="ml-1.5 rounded-full bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                    {templates.length}
                  </span>
                )}
              </button>
            </div>

            {centerTab === "taxonomy" ? (
              <TaxonomyPanel
                documents={documents}
                taxonomy={taxonomy}
                extractions={extractions}
                contradictions={contradictions}
                entities={entities}
                selectedDocId={selectedDocId}
                onDataRefresh={fetchAllData}
              />
            ) : (
              <TemplatesPanel
                templates={templates}
                onRefresh={fetchAllData}
              />
            )}
          </div>

          {/* Right panel: Chat */}
          <ChatPanel hasTaxonomy={!!taxonomy} />
        </div>
      </div>
    </TooltipProvider>
  )
}

function App() {
  return (
    <NotificationProvider>
      <NotificationDisplay />
      <AppContent />
    </NotificationProvider>
  )
}

export default App
