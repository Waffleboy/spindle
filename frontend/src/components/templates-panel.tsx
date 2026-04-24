import { useState } from "react"
import type { TaxonomyTemplateType } from "@/lib/types"
import {
  createTaxonomyTemplate,
  updateTaxonomyTemplate,
  deleteTaxonomyTemplate,
} from "@/lib/api"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { ScrollArea } from "./ui/scroll-area"
import { Badge } from "./ui/badge"
import { Plus, Trash2, Save, X, Pencil } from "lucide-react"

const EXPECTED_TYPES = [
  "text",
  "number",
  "date",
  "currency",
  "entity",
  "entity_list",
  "text_list",
  "date_range",
] as const

interface DimensionDraft {
  name: string
  description: string
  expected_type: string
}

interface TemplatesPanelProps {
  templates: TaxonomyTemplateType[]
  onRefresh: () => void
}

export function TemplatesPanel({ templates, onRefresh }: TemplatesPanelProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  // Form state
  const [label, setLabel] = useState("")
  const [description, setDescription] = useState("")
  const [dimensions, setDimensions] = useState<DimensionDraft[]>([])

  const resetForm = () => {
    setLabel("")
    setDescription("")
    setDimensions([])
    setEditingId(null)
    setIsCreating(false)
  }

  const startCreate = () => {
    resetForm()
    setIsCreating(true)
  }

  const startEdit = (t: TaxonomyTemplateType) => {
    setLabel(t.label)
    setDescription(t.description)
    setDimensions(
      t.dimensions.map((d) => ({
        name: d.name,
        description: d.description || "",
        expected_type: d.expected_type || "text",
      }))
    )
    setEditingId(t.id)
    setIsCreating(false)
  }

  const addDimension = () => {
    setDimensions((prev) => [
      ...prev,
      { name: "", description: "", expected_type: "text" },
    ])
  }

  const updateDimension = (
    idx: number,
    field: keyof DimensionDraft,
    value: string
  ) => {
    setDimensions((prev) =>
      prev.map((d, i) => (i === idx ? { ...d, [field]: value } : d))
    )
  }

  const removeDimension = (idx: number) => {
    setDimensions((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleSave = async () => {
    if (!label.trim() || !description.trim()) return
    const validDims = dimensions.filter((d) => d.name.trim())

    if (editingId) {
      await updateTaxonomyTemplate(editingId, {
        label: label.trim(),
        description: description.trim(),
        dimensions: validDims,
      })
    } else {
      await createTaxonomyTemplate({
        label: label.trim(),
        description: description.trim(),
        dimensions: validDims,
      })
    }
    resetForm()
    onRefresh()
  }

  const handleDelete = async (id: string) => {
    await deleteTaxonomyTemplate(id)
    if (editingId === id) resetForm()
    onRefresh()
  }

  const isFormActive = isCreating || editingId !== null

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-zinc-800 p-4">
        <h2 className="text-sm font-semibold text-zinc-200">
          Taxonomy Templates
        </h2>
        {!isFormActive && (
          <Button
            variant="ghost"
            size="sm"
            onClick={startCreate}
            className="h-7 gap-1 text-xs text-zinc-400 hover:text-zinc-200"
          >
            <Plus className="h-3.5 w-3.5" />
            New
          </Button>
        )}
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* Create / Edit form */}
          {isFormActive && (
            <div className="rounded-lg border border-zinc-700 bg-zinc-800/50 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-zinc-300">
                  {editingId ? "Edit Template" : "New Template"}
                </span>
                <button
                  onClick={resetForm}
                  className="text-zinc-500 hover:text-zinc-300"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-2">
                <Input
                  placeholder="Label (e.g. Investor Reports)"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  className="h-8 text-xs bg-zinc-900/50 border-zinc-600"
                />
                <Input
                  placeholder="Description — helps LLM match documents to this template"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="h-8 text-xs bg-zinc-900/50 border-zinc-600"
                />
              </div>

              {/* Dimensions */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
                    Required Dimensions ({dimensions.length})
                  </span>
                  <button
                    onClick={addDimension}
                    className="flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300"
                  >
                    <Plus className="h-3 w-3" />
                    Add
                  </button>
                </div>

                {dimensions.map((dim, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-1.5 rounded-md bg-zinc-900/50 p-2"
                  >
                    <div className="flex-1 space-y-1">
                      <Input
                        placeholder="Field name (snake_case)"
                        value={dim.name}
                        onChange={(e) =>
                          updateDimension(idx, "name", e.target.value)
                        }
                        className="h-7 text-xs bg-transparent border-zinc-700"
                      />
                      <Input
                        placeholder="Description"
                        value={dim.description}
                        onChange={(e) =>
                          updateDimension(idx, "description", e.target.value)
                        }
                        className="h-7 text-xs bg-transparent border-zinc-700"
                      />
                      <select
                        value={dim.expected_type}
                        onChange={(e) =>
                          updateDimension(idx, "expected_type", e.target.value)
                        }
                        className="h-7 w-full rounded-md border border-zinc-700 bg-transparent px-2 text-xs text-zinc-300"
                      >
                        {EXPECTED_TYPES.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </div>
                    <button
                      onClick={() => removeDimension(idx)}
                      className="mt-1 text-zinc-600 hover:text-red-400"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              <Button
                onClick={handleSave}
                disabled={!label.trim() || !description.trim()}
                className="w-full h-8 text-xs"
              >
                <Save className="mr-1.5 h-3.5 w-3.5" />
                {editingId ? "Update Template" : "Create Template"}
              </Button>
            </div>
          )}

          {/* Template list */}
          {templates.length === 0 && !isFormActive && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-xs text-zinc-500 mb-1">
                No templates configured
              </p>
              <p className="text-[10px] text-zinc-600 max-w-[200px]">
                Templates define fixed dimensions that the LLM must extract when
                it detects matching document types
              </p>
            </div>
          )}

          {templates.map((t) => (
            <div
              key={t.id}
              className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-3 space-y-2"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-xs font-medium text-zinc-200">
                    {t.label}
                  </h3>
                  <p className="text-[10px] text-zinc-500 mt-0.5">
                    {t.description}
                  </p>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => startEdit(t)}
                    className="text-zinc-600 hover:text-zinc-300 p-1"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(t.id)}
                    className="text-zinc-600 hover:text-red-400 p-1"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {t.dimensions.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {t.dimensions.map((dim, idx) => (
                    <Badge
                      key={idx}
                      variant="secondary"
                      className="text-[10px] bg-zinc-800 text-zinc-400 border-zinc-700"
                    >
                      {dim.name}
                      <span className="ml-1 text-zinc-600">
                        {dim.expected_type}
                      </span>
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
