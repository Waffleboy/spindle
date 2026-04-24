import { useState } from "react"
import type { EntityType } from "@/lib/types"
import { Button } from "./ui/button"
import { Badge } from "./ui/badge"
import { Card, CardContent } from "./ui/card"
import { updateResolution } from "@/lib/api"
import { Check, X, Users } from "lucide-react"

interface EntityReviewCardProps {
  entity: EntityType
  resolutionId?: string
  confidence?: number
  onReviewed: () => void
  onClose: () => void
}

export function EntityReviewCard({
  entity,
  resolutionId,
  confidence,
  onReviewed,
  onClose,
}: EntityReviewCardProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleAction = async (approved: boolean) => {
    if (!resolutionId) return
    setIsSubmitting(true)
    try {
      await updateResolution(resolutionId, approved)
      onReviewed()
    } catch (err) {
      console.error("Failed to update resolution:", err)
    } finally {
      setIsSubmitting(false)
    }
  }

  const confidencePercent = confidence ? Math.round(confidence * 100) : null

  return (
    <Card className="border-amber-500/30 bg-zinc-900/80 animate-slide-in">
      <CardContent className="p-3 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-amber-400" />
            <span className="text-sm font-semibold text-amber-300">
              Entity Review
            </span>
          </div>
          <button onClick={onClose} className="text-zinc-600 hover:text-zinc-400">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div>
          <div className="text-xs text-zinc-500 mb-1">Canonical Name</div>
          <div className="text-sm font-medium text-zinc-200">
            {entity.canonical_name}
          </div>
        </div>

        {entity.aliases.length > 0 && (
          <div>
            <div className="text-xs text-zinc-500 mb-1.5">Aliases</div>
            <div className="flex flex-wrap gap-1">
              {entity.aliases.map((alias) => (
                <Badge key={alias} variant="secondary" className="text-[10px]">
                  {alias}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {confidencePercent !== null && (
          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-zinc-500">Confidence</span>
              <span
                className={
                  confidencePercent >= 80
                    ? "text-emerald-400"
                    : confidencePercent >= 50
                    ? "text-amber-400"
                    : "text-rose-400"
                }
              >
                {confidencePercent}%
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-zinc-800">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  confidencePercent >= 80
                    ? "bg-emerald-500"
                    : confidencePercent >= 50
                    ? "bg-amber-500"
                    : "bg-rose-500"
                }`}
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
          </div>
        )}

        {resolutionId && (
          <div className="flex gap-2 pt-1">
            <Button
              size="sm"
              variant="outline"
              className="flex-1 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
              onClick={() => handleAction(true)}
              disabled={isSubmitting}
            >
              <Check className="mr-1 h-3 w-3" />
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="flex-1 border-rose-500/30 text-rose-400 hover:bg-rose-500/10"
              onClick={() => handleAction(false)}
              disabled={isSubmitting}
            >
              <X className="mr-1 h-3 w-3" />
              Reject
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
