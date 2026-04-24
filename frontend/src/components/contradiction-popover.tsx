import type { ContradictionType } from "@/lib/types"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./ui/popover"
import { Badge } from "./ui/badge"
import { ArrowRight, AlertTriangle } from "lucide-react"

interface ContradictionPopoverProps {
  contradiction: ContradictionType
  children: React.ReactNode
}

export function ContradictionPopover({
  contradiction,
  children,
}: ContradictionPopoverProps) {
  const aDate = contradiction.doc_a_date
    ? new Date(contradiction.doc_a_date)
    : null
  const bDate = contradiction.doc_b_date
    ? new Date(contradiction.doc_b_date)
    : null
  const aIsNewer = aDate && bDate ? aDate > bDate : null

  return (
    <Popover>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-400" />
            <span className="text-sm font-semibold text-rose-300">
              Contradiction Detected
            </span>
          </div>
          <div className="text-xs text-zinc-500 uppercase tracking-wider font-medium">
            {contradiction.dimension_name}
          </div>

          <div className="flex items-center gap-2">
            <div
              className={`flex-1 rounded-md p-2 text-xs ${
                aIsNewer === false
                  ? "bg-zinc-800/50 text-zinc-400"
                  : "bg-rose-500/10 border border-rose-500/20 text-rose-300"
              }`}
            >
              <div className="font-medium truncate">
                {contradiction.value_a}
              </div>
              <div className="mt-1 text-[10px] text-zinc-500 truncate">
                {contradiction.doc_a_filename}
              </div>
              {contradiction.doc_a_date && (
                <div className="text-[10px] text-zinc-600">
                  {new Date(contradiction.doc_a_date).toLocaleDateString()}
                </div>
              )}
            </div>

            <ArrowRight className="h-4 w-4 text-zinc-600 flex-shrink-0" />

            <div
              className={`flex-1 rounded-md p-2 text-xs ${
                aIsNewer === true
                  ? "bg-zinc-800/50 text-zinc-400"
                  : "bg-rose-500/10 border border-rose-500/20 text-rose-300"
              }`}
            >
              <div className="font-medium truncate">
                {contradiction.value_b}
              </div>
              <div className="mt-1 text-[10px] text-zinc-500 truncate">
                {contradiction.doc_b_filename}
              </div>
              {contradiction.doc_b_date && (
                <div className="text-[10px] text-zinc-600">
                  {new Date(contradiction.doc_b_date).toLocaleDateString()}
                </div>
              )}
            </div>
          </div>

          {aIsNewer !== null && (
            <div className="flex items-center gap-1.5">
              <ArrowRight className="h-3 w-3 text-emerald-400" />
              <span className="text-[10px] text-emerald-400">
                Newer:{" "}
                {aIsNewer
                  ? contradiction.doc_a_filename
                  : contradiction.doc_b_filename}
              </span>
            </div>
          )}

          <Badge
            variant={
              contradiction.resolution_status === "resolved"
                ? "success"
                : "destructive"
            }
          >
            {contradiction.resolution_status}
          </Badge>
        </div>
      </PopoverContent>
    </Popover>
  )
}
