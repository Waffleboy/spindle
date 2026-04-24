import { cn } from "@/lib/utils"
import type { PipelineStatus } from "@/lib/types"
import { Activity } from "lucide-react"

const PIPELINE_STEPS = [
  { key: "type_detection", label: "Type Detection" },
  { key: "taxonomy", label: "Taxonomy" },
  { key: "extraction", label: "Extraction" },
  { key: "entities", label: "Entities" },
  { key: "contradictions", label: "Contradictions" },
]

interface TopBarProps {
  pipelineStatus: PipelineStatus | null
  isProcessing: boolean
}

export function TopBar({ pipelineStatus, isProcessing }: TopBarProps) {
  if (!isProcessing && !pipelineStatus) return null

  const completedSteps = pipelineStatus?.steps_completed ?? []
  const currentStep = pipelineStatus?.current_step ?? null

  return (
    <div className="border-b border-border bg-card/50 px-6 py-3">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Activity className="h-4 w-4 text-primary animate-pulse" />
          <span>Pipeline Progress</span>
        </div>
        <div className="flex flex-1 items-center gap-1">
          {PIPELINE_STEPS.map((step, index) => {
            const isCompleted = completedSteps.includes(step.key)
            const isCurrent = currentStep === step.key
            return (
              <div key={step.key} className="flex flex-1 items-center gap-1">
                <div className="flex flex-1 flex-col gap-1">
                  <span
                    className={cn(
                      "text-[10px] font-medium uppercase tracking-wider",
                      isCompleted
                        ? "text-emerald-400"
                        : isCurrent
                        ? "text-primary"
                        : "text-muted-foreground"
                    )}
                  >
                    {step.label}
                  </span>
                  <div className="h-1.5 w-full rounded-full bg-muted">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-700 ease-out",
                        isCompleted
                          ? "bg-emerald-500 w-full"
                          : isCurrent
                          ? "bg-primary w-1/2 animate-pulse"
                          : "w-0"
                      )}
                    />
                  </div>
                </div>
                {index < PIPELINE_STEPS.length - 1 && (
                  <div
                    className={cn(
                      "mx-1 mt-4 h-px w-4",
                      isCompleted ? "bg-emerald-500/50" : "bg-muted"
                    )}
                  />
                )}
              </div>
            )
          })}
        </div>
        {pipelineStatus && (
          <span className="text-xs text-muted-foreground">
            {pipelineStatus.processed_documents}/{pipelineStatus.total_documents} docs
          </span>
        )}
      </div>
    </div>
  )
}
