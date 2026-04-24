import { useState, useEffect } from "react"
import type {
  EntityType,
  EntityTimelineType,
  TimelineNode,
  TimelineDiff,
} from "@/lib/types"
import { getEntityTimeline } from "@/lib/api"
import { cn } from "@/lib/utils"
import { Badge } from "./ui/badge"
import { Card, CardContent } from "./ui/card"
import { ScrollArea } from "./ui/scroll-area"
import {
  GitCommitHorizontal,
  FileText,
  ArrowRight,
  Plus,
  RefreshCw,
  AlertTriangle,
  ChevronLeft,
  Loader2,
} from "lucide-react"

interface ChangeFeedProps {
  entities: EntityType[]
  initialEntityId?: string
  onClose?: () => void
}

const CHANGE_CONFIG = {
  new: {
    icon: Plus,
    label: "New",
    dotColor: "bg-emerald-500",
    textColor: "text-emerald-600 dark:text-emerald-400",
    badgeVariant: "success" as const,
  },
  updated: {
    icon: RefreshCw,
    label: "Updated",
    dotColor: "bg-amber-500",
    textColor: "text-amber-600 dark:text-amber-400",
    badgeVariant: "warning" as const,
  },
  contradiction: {
    icon: AlertTriangle,
    label: "Contradiction",
    dotColor: "bg-rose-500",
    textColor: "text-rose-600 dark:text-rose-400",
    badgeVariant: "destructive" as const,
  },
} as const

function formatDate(date: string | null, isApproximate: boolean): string {
  if (!date) return "Unknown date"
  try {
    const d = new Date(date)
    const formatted = d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
    return isApproximate ? `uploaded ${formatted}` : formatted
  } catch {
    return date
  }
}

function DiffItem({ diff }: { diff: TimelineDiff }) {
  const config = CHANGE_CONFIG[diff.change_type]
  const Icon = config.icon

  return (
    <div className="flex items-start gap-2 py-1">
      <div
        className={cn(
          "mt-1.5 h-2 w-2 flex-shrink-0 rounded-full",
          config.dotColor
        )}
      />
      <div className="flex flex-wrap items-center gap-1 text-sm min-w-0">
        <Badge variant={config.badgeVariant} className="text-[10px] gap-0.5">
          <Icon className="h-2.5 w-2.5" />
          {config.label}
        </Badge>
        <span className="font-medium text-foreground">
          {diff.dimension_name}
        </span>
        {diff.change_type === "new" ? (
          <span className="text-muted-foreground">
            = <span className={config.textColor}>{diff.new_value}</span>
          </span>
        ) : (
          <span className="text-muted-foreground flex items-center gap-1 flex-wrap">
            <span className="line-through opacity-60">{diff.old_value}</span>
            <ArrowRight className="h-3 w-3 flex-shrink-0" />
            <span className={config.textColor}>{diff.new_value}</span>
          </span>
        )}
      </div>
    </div>
  )
}

function TimelineNodeCard({ node, isFirst }: { node: TimelineNode; isFirst: boolean }) {
  return (
    <div className="relative pl-8">
      {/* Timeline dot */}
      <div className="absolute left-0 top-3 flex h-5 w-5 items-center justify-center rounded-full border-2 border-border bg-card z-10">
        <GitCommitHorizontal className="h-3 w-3 text-muted-foreground" />
      </div>

      <Card className="mb-0">
        <CardContent className="p-3 space-y-2">
          {/* Document header */}
          <div className="flex items-center gap-2 flex-wrap">
            <FileText className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
            <span className="text-sm font-medium text-foreground truncate">
              {node.document_filename}
            </span>
            <Badge variant="outline" className="text-[10px]">
              {formatDate(node.document_date, node.is_approximate_date)}
            </Badge>
          </div>

          {/* Diffs from previous (skip for first node since it has no predecessor) */}
          {node.diffs_from_previous.length > 0 && (
            <div className="border-t border-border pt-2 space-y-0.5">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                Changes
              </div>
              {node.diffs_from_previous.map((diff, i) => (
                <DiffItem key={`${diff.dimension_name}-${i}`} diff={diff} />
              ))}
            </div>
          )}

          {/* Dimension values */}
          {node.dimensions.length > 0 && (
            <div
              className={cn(
                "space-y-1",
                node.diffs_from_previous.length > 0 && "border-t border-border pt-2"
              )}
            >
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                {isFirst ? "Values" : "All values"}
              </div>
              <div className="grid gap-1">
                {node.dimensions.map((dim) => (
                  <div
                    key={dim.dimension_name}
                    className="flex items-baseline gap-2 text-xs"
                  >
                    <span className="text-muted-foreground min-w-0 truncate flex-shrink-0">
                      {dim.dimension_name}
                    </span>
                    <span className="text-foreground truncate">{dim.value}</span>
                    {dim.confidence < 0.8 && (
                      <span className="text-amber-500 text-[10px] flex-shrink-0">
                        {Math.round(dim.confidence * 100)}%
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export function ChangeFeed({ entities, initialEntityId, onClose }: ChangeFeedProps) {
  const [selectedEntityId, setSelectedEntityId] = useState<string>(
    initialEntityId ?? entities[0]?.id ?? ""
  )
  const [timeline, setTimeline] = useState<EntityTimelineType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedEntityId) return

    let cancelled = false

    getEntityTimeline(selectedEntityId)
      .then((data) => {
        if (!cancelled) {
          setTimeline(data)
          setError(null)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Failed to load timeline"
          setError(message)
          setTimeline(null)
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedEntityId])

  const handleEntityChange = (entityId: string) => {
    setSelectedEntityId(entityId)
    setLoading(true)
    setError(null)
  }

  // Empty state: no entities at all
  if (entities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <GitCommitHorizontal className="h-10 w-10 text-muted-foreground mb-3" />
        <p className="text-sm text-muted-foreground">
          No entities found. Process some documents to see the entity change feed.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header area */}
      <div className="flex-shrink-0 p-4 space-y-3 border-b border-border">
        {/* Back button */}
        {onClose && (
          <button
            onClick={onClose}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Back to Insights
          </button>
        )}

        {/* Title */}
        <div className="flex items-center gap-2">
          <GitCommitHorizontal className="h-5 w-5 text-primary" />
          <h2 className="text-base font-semibold text-foreground">
            Entity Change Feed
          </h2>
        </div>

        {/* Entity selector */}
        <select
          value={selectedEntityId}
          onChange={(e) => handleEntityChange(e.target.value)}
          className="w-full rounded-md border border-border bg-card text-foreground text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {entities.map((entity) => (
            <option key={entity.id} value={entity.id}>
              {entity.canonical_name} ({entity.entity_type})
            </option>
          ))}
        </select>
      </div>

      {/* Timeline content */}
      <ScrollArea className="flex-1">
        <div className="p-4">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-6 w-6 text-muted-foreground animate-spin mb-2" />
              <p className="text-sm text-muted-foreground">Loading timeline...</p>
            </div>
          )}

          {error && !loading && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertTriangle className="h-6 w-6 text-rose-500 mb-2" />
              <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>
            </div>
          )}

          {!loading && !error && timeline && timeline.timeline.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="h-8 w-8 text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground">
                No timeline data for{" "}
                <span className="font-medium text-foreground">
                  {timeline.entity_name}
                </span>
                . This entity may not appear across multiple documents yet.
              </p>
            </div>
          )}

          {!loading && !error && timeline && timeline.timeline.length > 0 && (
            <div className="space-y-0">
              {/* Entity info */}
              <div className="mb-4 flex items-center gap-2">
                <span className="text-sm font-medium text-foreground">
                  {timeline.entity_name}
                </span>
                <Badge variant="outline" className="text-[10px]">
                  {timeline.entity_type}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  across {timeline.timeline.length} document
                  {timeline.timeline.length !== 1 ? "s" : ""}
                </span>
              </div>

              {/* Vertical timeline */}
              <div className="relative">
                {/* Vertical line */}
                <div className="absolute left-[9px] top-3 bottom-3 w-0.5 bg-border" />

                <div className="space-y-4">
                  {timeline.timeline.map((node, index) => (
                    <TimelineNodeCard
                      key={node.document_id}
                      node={node}
                      isFirst={index === 0}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
