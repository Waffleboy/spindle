import { useState, useEffect } from "react"
import type {
  InsightsType,
  InsightContradiction,
  InsightEntityReview,
  InsightStaleness,
} from "@/lib/types"
import { getInsights } from "@/lib/api"
import { cn } from "@/lib/utils"
import { Badge } from "./ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card"
import { ScrollArea } from "./ui/scroll-area"
import {
  AlertTriangle,
  Clock,
  Users,
  ArrowRight,
  FileText,
  Shield,
  Loader2,
  Inbox,
  Download,
} from "lucide-react"

interface InsightsDashboardProps {
  onSelectEntity?: (entityId: string) => void
  refreshKey?: number
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Unknown date"
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return "Unknown date"
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function SummaryBanner({ data }: { data: InsightsType }) {
  const items = [
    {
      count: data.total_contradictions,
      label: "Contradictions",
      icon: AlertTriangle,
      activeColor: "text-rose-500 dark:text-rose-400",
      activeBg: "bg-rose-500/10",
      activeBorder: "border-rose-500/30",
    },
    {
      count: data.total_entities_needing_review,
      label: "Entities to Review",
      icon: Users,
      activeColor: "text-amber-500 dark:text-amber-400",
      activeBg: "bg-amber-500/10",
      activeBorder: "border-amber-500/30",
    },
    {
      count: data.total_staleness_items,
      label: "Temporal Updates",
      icon: Clock,
      activeColor: "text-blue-500 dark:text-blue-400",
      activeBg: "bg-blue-500/10",
      activeBorder: "border-blue-500/30",
    },
  ]

  return (
    <div className="flex gap-3">
      {items.map((item) => {
        const isActive = item.count > 0
        const Icon = item.icon
        return (
          <div
            key={item.label}
            className={cn(
              "flex flex-1 items-center gap-3 rounded-xl border p-3 transition-colors",
              isActive
                ? `${item.activeBg} ${item.activeBorder}`
                : "border-border bg-card"
            )}
          >
            <Icon
              className={cn(
                "h-5 w-5 flex-shrink-0",
                isActive ? item.activeColor : "text-muted-foreground"
              )}
            />
            <div>
              <div
                className={cn(
                  "text-lg font-semibold leading-none",
                  isActive ? item.activeColor : "text-muted-foreground"
                )}
              >
                {item.count}
              </div>
              <div className="mt-0.5 text-xs text-muted-foreground">
                {item.label}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ContradictionCard({
  contradiction,
}: {
  contradiction: InsightContradiction
}) {
  const newerSide = contradiction.newer_doc

  return (
    <Card className="border-rose-500/20">
      <CardContent className="p-3 space-y-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-3.5 w-3.5 text-rose-400 flex-shrink-0" />
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground truncate">
            {contradiction.dimension_name}
          </span>
          {contradiction.entity_name && (
            <Badge variant="outline" className="text-[10px] ml-auto">
              {contradiction.entity_name}
            </Badge>
          )}
        </div>

        <div className="flex items-stretch gap-2">
          {/* Doc A side */}
          <div
            className={cn(
              "flex-1 rounded-md p-2 text-xs min-w-0",
              newerSide === "a"
                ? "bg-emerald-500/10 border border-emerald-500/20"
                : "bg-muted/50"
            )}
          >
            <div className="font-medium text-sm text-foreground truncate">
              {contradiction.doc_a_value}
            </div>
            <div className="mt-1.5 flex items-center gap-1 text-[10px] text-muted-foreground">
              <FileText className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">{contradiction.doc_a_filename}</span>
            </div>
            <div className="text-[10px] text-muted-foreground/70">
              {formatDate(contradiction.doc_a_date)}
            </div>
            {newerSide === "a" && (
              <Badge
                variant="success"
                className="mt-1.5 text-[10px]"
              >
                More recent
              </Badge>
            )}
          </div>

          <div className="flex items-center">
            <span className="text-muted-foreground text-xs font-medium">vs</span>
          </div>

          {/* Doc B side */}
          <div
            className={cn(
              "flex-1 rounded-md p-2 text-xs min-w-0",
              newerSide === "b"
                ? "bg-emerald-500/10 border border-emerald-500/20"
                : "bg-muted/50"
            )}
          >
            <div className="font-medium text-sm text-foreground truncate">
              {contradiction.doc_b_value}
            </div>
            <div className="mt-1.5 flex items-center gap-1 text-[10px] text-muted-foreground">
              <FileText className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">{contradiction.doc_b_filename}</span>
            </div>
            <div className="text-[10px] text-muted-foreground/70">
              {formatDate(contradiction.doc_b_date)}
            </div>
            {newerSide === "b" && (
              <Badge
                variant="success"
                className="mt-1.5 text-[10px]"
              >
                More recent
              </Badge>
            )}
          </div>
        </div>

        {contradiction.reason && (
          <div className="rounded-md bg-muted/50 p-2 text-[11px] text-muted-foreground leading-relaxed">
            {contradiction.reason}
          </div>
        )}

        <div className="flex items-center justify-between pt-1">
          <Badge
            variant={
              contradiction.resolution_status === "resolved"
                ? "success"
                : "destructive"
            }
            className="text-[10px]"
          >
            {contradiction.resolution_status}
          </Badge>
        </div>
      </CardContent>
    </Card>
  )
}

function EntityReviewItem({
  entity,
  onSelect,
}: {
  entity: InsightEntityReview
  onSelect?: (entityId: string) => void
}) {
  return (
    <button
      onClick={() => onSelect?.(entity.entity_id)}
      className="flex w-full items-center gap-3 rounded-lg border border-border bg-card p-3 text-left transition-colors hover:bg-accent/50"
    >
      <Users className="h-4 w-4 text-amber-400 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground truncate">
            {entity.canonical_name}
          </span>
          <Badge variant="secondary" className="text-[10px] flex-shrink-0">
            {entity.entity_type}
          </Badge>
        </div>
        <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
          <Shield className="h-3 w-3 flex-shrink-0" />
          <span>
            {entity.review_count} review{entity.review_count !== 1 ? "s" : ""} needed
          </span>
        </div>
        {entity.aliases.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {entity.aliases.map((alias) => (
              <Badge key={alias} variant="outline" className="text-[10px]">
                {alias}
              </Badge>
            ))}
          </div>
        )}
      </div>
      <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
    </button>
  )
}

function StalenessCard({ item }: { item: InsightStaleness }) {
  const hasNewerDate = item.newest_doc_date !== null
  const label = hasNewerDate ? "Updated" : "Superseded"

  return (
    <Card className="border-blue-500/20">
      <CardContent className="p-3 space-y-2">
        <div className="flex items-center gap-2">
          <Clock className="h-3.5 w-3.5 text-blue-400 flex-shrink-0" />
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground truncate">
            {item.dimension_name}
          </span>
          {item.entity_name && (
            <Badge variant="outline" className="text-[10px] ml-auto">
              {item.entity_name}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Older value */}
          <div className="flex-1 rounded-md bg-muted/50 p-2 min-w-0">
            <div className="text-sm text-muted-foreground line-through truncate">
              {item.older_value}
            </div>
            <div className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground">
              <FileText className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">{item.older_doc_filename}</span>
            </div>
            <div className="text-[10px] text-muted-foreground/70">
              {formatDate(item.older_doc_date)}
            </div>
          </div>

          <ArrowRight className="h-4 w-4 text-blue-400 flex-shrink-0" />

          {/* Newer value */}
          <div className="flex-1 rounded-md bg-blue-500/10 border border-blue-500/20 p-2 min-w-0">
            <div className="text-sm font-medium text-foreground truncate">
              {item.newest_value}
            </div>
            <div className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground">
              <FileText className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">{item.newest_doc_filename}</span>
            </div>
            <div className="text-[10px] text-muted-foreground/70">
              {formatDate(item.newest_doc_date)}
            </div>
          </div>
        </div>

        <Badge
          variant="default"
          className="text-[10px]"
        >
          {label}
        </Badge>
      </CardContent>
    </Card>
  )
}

function csvEscape(val: string): string {
  if (val.includes(",") || val.includes('"') || val.includes("\n")) {
    return `"${val.replace(/"/g, '""')}"`
  }
  return val
}

function exportInsightsCSV(data: InsightsType) {
  const lines: string[] = []
  const row = (...vals: (string | number)[]) => vals.map(v => csvEscape(String(v))).join(",")

  if (data.contradictions.length > 0) {
    lines.push("CONTRADICTIONS")
    lines.push("Dimension,Entity,Doc A,Value A,Date A,Doc B,Value B,Date B,Newer,Reason,Status")
    for (const c of data.contradictions) {
      lines.push(row(c.dimension_name, c.entity_name ?? "", c.doc_a_filename, c.doc_a_value, formatDate(c.doc_a_date), c.doc_b_filename, c.doc_b_value, formatDate(c.doc_b_date), c.newer_doc ?? "", c.reason ?? "", c.resolution_status))
    }
    lines.push("")
  }

  if (data.entities_needing_review.length > 0) {
    lines.push("ENTITIES NEEDING REVIEW")
    lines.push("Name,Type,Reviews Needed,Aliases")
    for (const e of data.entities_needing_review) {
      lines.push(row(e.canonical_name, e.entity_type, e.review_count, e.aliases.join("; ")))
    }
    lines.push("")
  }

  if (data.staleness_items.length > 0) {
    lines.push("TEMPORAL UPDATES")
    lines.push("Dimension,Entity,Older Value,Older Doc,Older Date,Newer Value,Newer Doc,Newer Date")
    for (const s of data.staleness_items) {
      lines.push(row(s.dimension_name, s.entity_name ?? "", s.older_value, s.older_doc_filename, formatDate(s.older_doc_date), s.newest_value, s.newest_doc_filename, formatDate(s.newest_doc_date)))
    }
  }

  const blob = new Blob([lines.join("\n")], { type: "text/csv" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = "insights-export.csv"
  a.click()
  URL.revokeObjectURL(url)
}

export function InsightsDashboard({ onSelectEntity, refreshKey }: InsightsDashboardProps) {
  const [data, setData] = useState<InsightsType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function fetchInsights() {
      try {
        setLoading(true)
        setError(null)
        const insights = await getInsights()
        if (!cancelled) setData(insights)
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load insights"
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchInsights()
    return () => {
      cancelled = true
    }
  }, [refreshKey])

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">
            Loading insights...
          </span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertTriangle className="h-6 w-6 text-rose-400" />
          <span className="text-sm text-rose-500 dark:text-rose-400">
            {error}
          </span>
        </div>
      </div>
    )
  }

  if (
    !data ||
    (data.total_contradictions === 0 &&
      data.total_entities_needing_review === 0 &&
      data.total_staleness_items === 0)
  ) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3 text-center max-w-sm">
          <Inbox className="h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            No insights yet — process some documents to see contradictions,
            entity reviews, and temporal updates.
          </p>
        </div>
      </div>
    )
  }

  return (
    <ScrollArea className="flex-1">
      <div className="space-y-6 p-4">
        <div className="flex items-center justify-between">
          <SummaryBanner data={data} />
          <button
            onClick={() => exportInsightsCSV(data)}
            className="ml-3 flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground flex-shrink-0"
          >
            <Download className="h-3.5 w-3.5" />
            Export
          </button>
        </div>

        {data.contradictions.length > 0 && (
          <section>
            <CardHeader className="px-0 pt-0 pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <AlertTriangle className="h-4 w-4 text-rose-400" />
                Contradictions
              </CardTitle>
            </CardHeader>
            <div className="grid gap-3 sm:grid-cols-1 lg:grid-cols-2">
              {data.contradictions.map((c) => (
                <ContradictionCard key={c.id} contradiction={c} />
              ))}
            </div>
          </section>
        )}

        {data.entities_needing_review.length > 0 && (
          <section>
            <CardHeader className="px-0 pt-0 pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Users className="h-4 w-4 text-amber-400" />
                Entities to Review
              </CardTitle>
            </CardHeader>
            <div className="space-y-2">
              {data.entities_needing_review.map((e) => (
                <EntityReviewItem
                  key={e.entity_id}
                  entity={e}
                  onSelect={onSelectEntity}
                />
              ))}
            </div>
          </section>
        )}

        {data.staleness_items.length > 0 && (
          <section>
            <CardHeader className="px-0 pt-0 pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-blue-400" />
                Temporal Updates
              </CardTitle>
            </CardHeader>
            <div className="grid gap-3 sm:grid-cols-1 lg:grid-cols-2">
              {data.staleness_items.map((s, i) => (
                <StalenessCard key={`${s.dimension_name}-${s.entity_name ?? "global"}-${i}`} item={s} />
              ))}
            </div>
          </section>
        )}
      </div>
    </ScrollArea>
  )
}
