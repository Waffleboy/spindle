import { useState, useMemo } from "react"
import { cn } from "@/lib/utils"
import type {
  DocumentType,
  TaxonomyType,
  TaxonomyDimension,
  ExtractionType,
  ContradictionType,
  EntityType,
} from "@/lib/types"
import { ContradictionPopover } from "./contradiction-popover"
import { EntityReviewCard } from "./entity-review-card"
import { Badge } from "./ui/badge"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./ui/popover"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "./ui/tooltip"
import { Database, Layers, Info, FileText, Gauge, BookOpen } from "lucide-react"

interface TaxonomyPanelProps {
  documents: DocumentType[]
  taxonomy: TaxonomyType | null
  extractions: ExtractionType[]
  contradictions: ContradictionType[]
  entities: EntityType[]
  selectedDocId: string | null
  onSelectDoc: (id: string | null) => void
  onDataRefresh: () => void
}

function findEntityForExtraction(extraction: ExtractionType, entities: EntityType[]): EntityType | null {
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

function findResolvedEntity(extraction: ExtractionType, entities: EntityType[]): EntityType | null {
  const val = (extraction.resolved_value ?? extraction.raw_value).toLowerCase()
  for (const entity of entities) {
    if (entity.canonical_name.toLowerCase() === val) return entity
    if (entity.aliases.some((a) => a.toLowerCase() === val)) return entity
  }
  return null
}

function CellDetailPopover({
  extraction,
  dim,
  entity,
  isConfirmed,
}: {
  extraction: ExtractionType
  dim: TaxonomyDimension
  entity: EntityType | null
  isConfirmed: boolean
}) {
  const confidenceColor =
    extraction.confidence >= 0.9
      ? "text-emerald-400"
      : extraction.confidence >= 0.7
      ? "text-amber-400"
      : "text-rose-400"

  return (
    <PopoverContent className="w-80" side="bottom">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            {dim.name}
          </span>
          <Badge variant="secondary" className="text-[10px]">
            {dim.expected_type}
          </Badge>
        </div>

        <div className="rounded-md bg-muted/50 p-2.5">
          <div className="text-sm text-foreground font-medium">
            {extraction.resolved_value ?? extraction.raw_value}
          </div>
          {extraction.resolved_value &&
            extraction.resolved_value !== extraction.raw_value && (
              <div className="text-xs text-muted-foreground line-through mt-1">
                Raw: {extraction.raw_value}
              </div>
            )}
        </div>

        {entity && entity.aliases.length > 0 && (
          <div>
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
              Also known as
            </span>
            <div className="flex flex-wrap gap-1 mt-1">
              {entity.aliases.map((alias) => (
                <span
                  key={alias}
                  className="inline-block rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground"
                >
                  {alias}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex items-center gap-1.5">
            <Gauge className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground">Confidence</span>
          </div>
          <div className={cn("text-right font-medium", confidenceColor)}>
            {Math.round(extraction.confidence * 100)}%
          </div>

          {extraction.source_pages && extraction.source_pages.length > 0 && (
            <>
              <div className="flex items-center gap-1.5">
                <BookOpen className="h-3 w-3 text-muted-foreground" />
                <span className="text-muted-foreground">Source</span>
              </div>
              <div className="text-right text-foreground">
                Page {extraction.source_pages.join(", ")}
              </div>
            </>
          )}

          <div className="flex items-center gap-1.5">
            <FileText className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground">Document</span>
          </div>
          <div className="text-right text-foreground truncate" title={extraction.document_filename}>
            {extraction.document_filename}
          </div>
        </div>

        {isConfirmed && (
          <div className="flex items-center gap-1.5 text-xs text-emerald-400">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Confirmed — no contradictions or review needed
          </div>
        )}

        {dim.description && (
          <div className="border-t border-border pt-2 text-[11px] text-muted-foreground">
            {dim.description}
          </div>
        )}
      </div>
    </PopoverContent>
  )
}

export function TaxonomyPanel({
  documents,
  taxonomy,
  extractions,
  contradictions,
  entities,
  selectedDocId,
  onSelectDoc,
  onDataRefresh,
}: TaxonomyPanelProps) {
  const [reviewingCell, setReviewingCell] = useState<string | null>(null)

  const dimensions = taxonomy?.dimensions ?? []

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

  const unresolvedContradictions = contradictions.filter(
    (c) => c.resolution_status !== "resolved"
  )
  const entitiesNeedingReview = entities.filter((e) => e.needs_review_count > 0)

  if (!taxonomy || dimensions.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center p-8">
        <div className="rounded-full bg-muted/50 p-4 mb-4">
          <Database className="h-10 w-10 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-medium text-muted-foreground mb-2">
          No Taxonomy Discovered Yet
        </h3>
        <p className="text-sm text-muted-foreground/70 max-w-md">
          Drop your analyst reports here — we&apos;ll find the facts, flag the
          conflicts, and answer your questions. The extraction grid will appear
          once documents are processed.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold text-foreground">
            Taxonomy Dashboard
          </h2>
          <Badge variant="secondary" className="ml-2">
            {taxonomy.doc_type}
          </Badge>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>{documents.length} documents</span>
          <span>{dimensions.length} dimensions</span>
          {unresolvedContradictions.length > 0 && (
            <Badge variant="destructive">
              {unresolvedContradictions.length} contradictions
            </Badge>
          )}
          {entitiesNeedingReview.length > 0 && (
            <Badge variant="warning">
              {entitiesNeedingReview.length} needs review
            </Badge>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <div className="min-w-max">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="sticky left-0 bg-card px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground z-10">
                  Document
                </th>
                {dimensions.map((dim) => (
                  <th
                    key={dim.name}
                    className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground min-w-[160px]"
                  >
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="flex items-center gap-1.5 cursor-help">
                          <div className="flex flex-col gap-0.5">
                            <span>{dim.name}</span>
                            <span className="text-[10px] font-normal normal-case text-muted-foreground/70">
                              {dim.expected_type}
                            </span>
                          </div>
                          <Info className="h-3 w-3 text-muted-foreground/70 flex-shrink-0" />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="max-w-xs">
                        <div className="space-y-1.5">
                          <div className="font-medium text-foreground">{dim.name}</div>
                          {dim.description && (
                            <div className="text-muted-foreground text-xs">{dim.description}</div>
                          )}
                          <div className="text-muted-foreground/70 text-[11px]">Type: {dim.expected_type}</div>
                        </div>
                      </TooltipContent>
                    </Tooltip>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {documents.map((doc, rowIndex) => {
                const docExtractions = extractionMap.get(doc.id)
                const isSelected = selectedDocId === doc.id
                return (
                  <tr
                    key={doc.id}
                    className={cn(
                      "border-b border-border/50 transition-all animate-slide-in",
                      isSelected
                        ? "bg-primary/5 ring-1 ring-inset ring-primary/30"
                        : "hover:bg-muted/30"
                    )}
                    style={{
                      animationDelay: `${rowIndex * 50}ms`,
                      opacity: 0,
                    }}
                  >
                    <td className={cn(
                      "sticky left-0 px-4 py-3 z-10",
                      isSelected ? "bg-background/90" : "bg-background"
                    )}>
                      <button
                        type="button"
                        onClick={() => onSelectDoc(isSelected ? null : doc.id)}
                        className={cn(
                          "text-left w-full rounded-md px-2 py-1 -mx-2 -my-1 transition-colors cursor-pointer",
                          isSelected
                            ? "bg-primary/10"
                            : "hover:bg-muted/50"
                        )}
                      >
                        <div className="flex items-center gap-1.5">
                          <FileText className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                          <span className={cn(
                            "font-medium truncate max-w-[120px]",
                            isSelected ? "text-primary" : "text-foreground"
                          )}>
                            {doc.original_filename}
                          </span>
                        </div>
                        <div className="text-[10px] text-muted-foreground pl-[18px]">
                          {doc.detected_doc_type ?? doc.file_type}
                        </div>
                      </button>
                    </td>
                    {dimensions.map((dim) => {
                      const extraction = docExtractions?.get(dim.name)
                      const contradictionKey = `${doc.id}::${dim.name}`
                      const contradiction = contradictionMap.get(contradictionKey)
                      const entityForReview = extraction
                        ? findEntityForExtraction(extraction, entities)
                        : null
                      const resolvedEntity = extraction
                        ? findResolvedEntity(extraction, entities)
                        : null
                      const cellKey = `${doc.id}::${dim.name}`
                      const isReviewing = reviewingCell === cellKey

                      const hasContradiction = !!contradiction
                      const hasEntityReview = !!entityForReview
                      const isConfirmed =
                        !!extraction?.resolved_value &&
                        !hasContradiction &&
                        !hasEntityReview

                      const cellValue = (
                        <div>
                          <div
                            className={cn(
                              "text-foreground",
                              hasContradiction && "text-rose-300",
                              hasEntityReview && !hasContradiction && "text-amber-300"
                            )}
                          >
                            {extraction
                              ? (extraction.resolved_value ?? extraction.raw_value)
                              : null}
                          </div>
                          {extraction?.resolved_value &&
                            extraction.resolved_value !== extraction.raw_value && (
                              <div className="text-[10px] text-muted-foreground line-through mt-0.5">
                                {extraction.raw_value}
                              </div>
                            )}
                          {extraction?.source_pages &&
                            extraction.source_pages.length > 0 && (
                              <div className="text-[10px] text-muted-foreground mt-0.5">
                                p.{extraction.source_pages.join(", ")}
                              </div>
                            )}
                        </div>
                      )

                      if (hasContradiction && contradiction) {
                        return (
                          <td
                            key={dim.name}
                            className="px-4 py-3 relative bg-rose-500/5 cursor-pointer hover:bg-rose-500/10 transition-colors"
                          >
                            <ContradictionPopover contradiction={contradiction}>
                              <button type="button" className="w-full text-left cursor-pointer">
                                {cellValue}
                              </button>
                            </ContradictionPopover>
                          </td>
                        )
                      }

                      if (hasEntityReview) {
                        return (
                          <td
                            key={dim.name}
                            className="px-4 py-3 relative bg-amber-500/5 cursor-pointer hover:bg-amber-500/10 transition-colors"
                            onClick={() => {
                              setReviewingCell(isReviewing ? null : cellKey)
                            }}
                          >
                            {cellValue}
                            {isReviewing && entityForReview && (
                              <div className="absolute left-0 top-full z-20 w-72 mt-1">
                                <EntityReviewCard
                                  entity={entityForReview}
                                  confidence={extraction!.confidence}
                                  onReviewed={() => {
                                    setReviewingCell(null)
                                    onDataRefresh()
                                  }}
                                  onClose={() => setReviewingCell(null)}
                                />
                              </div>
                            )}
                          </td>
                        )
                      }

                      if (extraction) {
                        return (
                          <td
                            key={dim.name}
                            className={cn(
                              "px-4 py-3 relative cursor-pointer hover:bg-muted/40 transition-colors",
                              isConfirmed && "border-l-2 border-l-emerald-500/30"
                            )}
                          >
                            <Popover>
                              <PopoverTrigger asChild>
                                <button type="button" className="w-full text-left">
                                  {cellValue}
                                </button>
                              </PopoverTrigger>
                              <CellDetailPopover
                                extraction={extraction}
                                dim={dim}
                                entity={resolvedEntity}
                                isConfirmed={isConfirmed}
                              />
                            </Popover>
                          </td>
                        )
                      }

                      return (
                        <td
                          key={dim.name}
                          className="px-4 py-3 relative text-muted-foreground/40"
                        >
                          -
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
