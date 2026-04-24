import { useMemo } from "react"
import type { TaxonomyType, ExtractionType } from "@/lib/types"
import { ScrollArea } from "./ui/scroll-area"
import { Badge } from "./ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "./ui/tooltip"
import { Layers, Hash, Calendar, Type, Users, List, DollarSign, ArrowLeftRight } from "lucide-react"

const TYPE_ICONS: Record<string, typeof Type> = {
  text: Type,
  number: Hash,
  date: Calendar,
  currency: DollarSign,
  entity: Users,
  entity_list: Users,
  text_list: List,
  date_range: ArrowLeftRight,
}

interface TaxonomySchemaPanelProps {
  taxonomy: TaxonomyType | null
  extractions: ExtractionType[]
}

export function TaxonomySchemaPanel({ taxonomy, extractions }: TaxonomySchemaPanelProps) {
  const coverageMap = useMemo(() => {
    const map = new Map<string, number>()
    for (const ext of extractions) {
      map.set(ext.dimension_name, (map.get(ext.dimension_name) ?? 0) + 1)
    }
    return map
  }, [extractions])

  const totalDocs = useMemo(() => {
    const docIds = new Set<string>()
    for (const ext of extractions) docIds.add(ext.document_id)
    return docIds.size
  }, [extractions])

  if (!taxonomy) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center p-6 text-center">
        <Layers className="h-8 w-8 text-muted-foreground/50 mb-3" />
        <p className="text-sm text-muted-foreground">No taxonomy yet</p>
        <p className="text-xs text-muted-foreground/70 mt-1">
          Process documents to discover the schema
        </p>
      </div>
    )
  }

  const dimensions = taxonomy.dimensions

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Schema</h2>
        </div>
        <div className="flex items-center gap-2 mt-1.5">
          <Badge variant="secondary" className="text-[10px]">
            {taxonomy.doc_type}
          </Badge>
          <span className="text-[10px] text-muted-foreground">
            {dimensions.length} dimension{dimensions.length !== 1 && "s"}
          </span>
        </div>
        {taxonomy.company_context && (
          <p className="text-[10px] text-muted-foreground/70 mt-1 truncate" title={taxonomy.company_context}>
            {taxonomy.company_context}
          </p>
        )}
      </div>

      <ScrollArea className="flex-1">
        <div className="p-3 space-y-1.5">
          {dimensions.map((dim) => {
            const Icon = TYPE_ICONS[dim.expected_type] ?? Type
            const count = coverageMap.get(dim.name) ?? 0
            const coveragePct = totalDocs > 0 ? Math.round((count / totalDocs) * 100) : 0

            return (
              <Tooltip key={dim.name}>
                <TooltipTrigger asChild>
                  <div className="group rounded-md border border-border/50 bg-muted/20 px-3 py-2.5 transition-colors hover:bg-muted/40 hover:border-border cursor-default">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <Icon className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                        <span className="text-sm font-medium text-foreground truncate">
                          {dim.name}
                        </span>
                      </div>
                      <Badge variant="outline" className="text-[9px] flex-shrink-0 font-normal">
                        {dim.expected_type}
                      </Badge>
                    </div>
                    {dim.description && (
                      <p className="text-[11px] text-muted-foreground mt-1 pl-[22px] line-clamp-2">
                        {dim.description}
                      </p>
                    )}
                    {totalDocs > 0 && (
                      <div className="flex items-center gap-2 mt-1.5 pl-[22px]">
                        <div className="flex-1 h-1 rounded-full bg-border overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary/40 transition-all"
                            style={{ width: `${coveragePct}%` }}
                          />
                        </div>
                        <span className="text-[9px] text-muted-foreground/70 flex-shrink-0">
                          {count}/{totalDocs}
                        </span>
                      </div>
                    )}
                  </div>
                </TooltipTrigger>
                <TooltipContent side="left" className="max-w-xs">
                  <div className="space-y-1">
                    <div className="font-medium">{dim.name}</div>
                    {dim.description && (
                      <div className="text-xs text-muted-foreground">{dim.description}</div>
                    )}
                    <div className="text-[11px] text-muted-foreground/70">
                      Type: {dim.expected_type} · Extracted in {count} of {totalDocs} docs ({coveragePct}%)
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            )
          })}
        </div>
      </ScrollArea>
    </div>
  )
}
