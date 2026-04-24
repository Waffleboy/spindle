import { useState, useMemo } from "react"
import { cn } from "@/lib/utils"
import type {
  DocumentType,
  TaxonomyType,
  ExtractionType,
  ContradictionType,
  EntityType,
} from "@/lib/types"
import { ContradictionPopover } from "./contradiction-popover"
import { EntityReviewCard } from "./entity-review-card"
import { ScrollArea } from "./ui/scroll-area"
import { Badge } from "./ui/badge"
import { Database, Layers } from "lucide-react"

interface TaxonomyPanelProps {
  documents: DocumentType[]
  taxonomy: TaxonomyType | null
  extractions: ExtractionType[]
  contradictions: ContradictionType[]
  entities: EntityType[]
  selectedDocId: string | null
  onDataRefresh: () => void
}

export function TaxonomyPanel({
  documents,
  taxonomy,
  extractions,
  contradictions,
  entities,
  selectedDocId,
  onDataRefresh,
}: TaxonomyPanelProps) {
  const [reviewingCell, setReviewingCell] = useState<string | null>(null)

  const dimensions = taxonomy?.dimensions ?? []

  // Build a map: docId -> dimensionName -> extraction
  const extractionMap = useMemo(() => {
    const map = new Map<string, Map<string, ExtractionType>>()
    for (const ext of extractions) {
      if (!map.has(ext.document_id)) {
        map.set(ext.document_id, new Map())
      }
      map.get(ext.document_id)!.set(ext.dimension_name, ext)
    }
    return map
  }, [extractions])

  // Build a map: docId+dimensionName -> contradiction
  const contradictionMap = useMemo(() => {
    const map = new Map<string, ContradictionType>()
    for (const c of contradictions) {
      if (c.resolution_status !== "resolved") {
        map.set(`${c.doc_a_id}::${c.dimension_name}`, c)
        map.set(`${c.doc_b_id}::${c.dimension_name}`, c)
      }
    }
    return map
  }, [contradictions])

  // Determine which entities need review for a given extraction
  const needsEntityReview = (extraction: ExtractionType): EntityType | null => {
    for (const entity of entities) {
      if (entity.needs_review_count > 0) {
        const lowerAliases = entity.aliases.map((a) => a.toLowerCase())
        const rawLower = extraction.raw_value.toLowerCase()
        if (
          entity.canonical_name.toLowerCase() === rawLower ||
          lowerAliases.includes(rawLower)
        ) {
          return entity
        }
      }
    }
    return null
  }

  const filteredDocs = selectedDocId
    ? documents.filter((d) => d.id === selectedDocId)
    : documents

  if (!taxonomy || dimensions.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center p-8">
        <div className="rounded-full bg-zinc-800/50 p-4 mb-4">
          <Database className="h-10 w-10 text-zinc-600" />
        </div>
        <h3 className="text-lg font-medium text-zinc-400 mb-2">
          No Taxonomy Discovered Yet
        </h3>
        <p className="text-sm text-zinc-600 max-w-md">
          Upload and process documents to discover taxonomy dimensions. The
          engine will automatically detect document types, extract fields, and
          resolve entities.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-zinc-200">
            Taxonomy Dashboard
          </h2>
          <Badge variant="secondary" className="ml-2">
            {taxonomy.doc_type}
          </Badge>
        </div>
        <div className="flex items-center gap-3 text-xs text-zinc-500">
          <span>{filteredDocs.length} documents</span>
          <span>{dimensions.length} dimensions</span>
          {contradictions.filter((c) => c.resolution_status !== "resolved")
            .length > 0 && (
            <Badge variant="destructive">
              {
                contradictions.filter(
                  (c) => c.resolution_status !== "resolved"
                ).length
              }{" "}
              contradictions
            </Badge>
          )}
        </div>
      </div>

      {/* Table */}
      <ScrollArea className="flex-1">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="sticky left-0 bg-zinc-900 px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500 z-10">
                  Document
                </th>
                {dimensions.map((dim) => (
                  <th
                    key={dim.name}
                    className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500 min-w-[160px]"
                  >
                    <div className="flex flex-col gap-0.5">
                      <span>{dim.name}</span>
                      <span className="text-[10px] font-normal normal-case text-zinc-600">
                        {dim.expected_type}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredDocs.map((doc, rowIndex) => {
                const docExtractions = extractionMap.get(doc.id)
                return (
                  <tr
                    key={doc.id}
                    className="border-b border-zinc-800/50 hover:bg-zinc-800/20 transition-colors animate-slide-in"
                    style={{
                      animationDelay: `${rowIndex * 50}ms`,
                      opacity: 0,
                    }}
                  >
                    <td className="sticky left-0 bg-zinc-950 px-4 py-3 z-10">
                      <div className="font-medium text-zinc-300 truncate max-w-[140px]">
                        {doc.original_filename}
                      </div>
                      <div className="text-[10px] text-zinc-600">
                        {doc.detected_doc_type ?? doc.file_type}
                      </div>
                    </td>
                    {dimensions.map((dim) => {
                      const extraction = docExtractions?.get(dim.name)
                      const contradictionKey = `${doc.id}::${dim.name}`
                      const contradiction =
                        contradictionMap.get(contradictionKey)
                      const entityForReview = extraction
                        ? needsEntityReview(extraction)
                        : null
                      const cellKey = `${doc.id}::${dim.name}`
                      const isReviewing = reviewingCell === cellKey

                      const hasContradiction = !!contradiction
                      const hasEntityReview = !!entityForReview
                      const isConfirmed =
                        extraction?.resolved_value &&
                        !hasContradiction &&
                        !hasEntityReview

                      const cellInner = extraction ? (
                        <div>
                          <div
                            className={cn(
                              "text-zinc-300",
                              hasContradiction && "text-rose-300",
                              hasEntityReview &&
                                !hasContradiction &&
                                "text-amber-300"
                            )}
                          >
                            {extraction.resolved_value ??
                              extraction.raw_value}
                          </div>
                          {extraction.resolved_value &&
                            extraction.resolved_value !==
                              extraction.raw_value && (
                              <div className="text-[10px] text-zinc-600 line-through mt-0.5">
                                {extraction.raw_value}
                              </div>
                            )}
                          {extraction.source_pages &&
                            extraction.source_pages.length > 0 && (
                              <div className="text-[10px] text-zinc-600 mt-0.5">
                                p.{extraction.source_pages.join(", ")}
                              </div>
                            )}
                          {/* Entity review card inline */}
                          {isReviewing && entityForReview && (
                            <div className="absolute left-0 top-full z-20 w-72 mt-1">
                              <EntityReviewCard
                                entity={entityForReview}
                                confidence={extraction.confidence}
                                onReviewed={() => {
                                  setReviewingCell(null)
                                  onDataRefresh()
                                }}
                                onClose={() => setReviewingCell(null)}
                              />
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-zinc-700">-</span>
                      )

                      return (
                        <td
                          key={dim.name}
                          className={cn(
                            "px-4 py-3 relative",
                            hasContradiction &&
                              "bg-rose-500/5",
                            hasEntityReview &&
                              !hasContradiction &&
                              "bg-amber-500/5 cursor-pointer",
                            isConfirmed && "border-l-2 border-l-emerald-500/30"
                          )}
                          onClick={() => {
                            if (hasEntityReview) {
                              setReviewingCell(
                                isReviewing ? null : cellKey
                              )
                            }
                          }}
                        >
                          {hasContradiction && contradiction ? (
                            <ContradictionPopover contradiction={contradiction}>
                              <button type="button" className="w-full text-left cursor-pointer">
                                {cellInner}
                              </button>
                            </ContradictionPopover>
                          ) : (
                            cellInner
                          )}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </ScrollArea>
    </div>
  )
}
