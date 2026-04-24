import type {
  DocumentType,
  TaxonomyType,
  TaxonomyTemplateType,
  ExtractionType,
  EntityType,
  ContradictionType,
  ChatResponseType,
  PipelineStatus,
  InsightsType,
  EntityTimelineType,
} from "./types";

const API_BASE = "/api";

async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "Unknown error");
    throw new Error(`API error ${response.status}: ${errorBody}`);
  }

  return response.json();
}

export async function uploadDocuments(
  files: File[],
  companyContext?: string,
  splitRows?: boolean
): Promise<{ document_ids: string[]; message: string }> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  if (companyContext) {
    formData.append("company_context", companyContext);
  }
  if (splitRows) {
    formData.append("split_rows", "true");
  }

  const response = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "Unknown error");
    throw new Error(`Upload error ${response.status}: ${errorBody}`);
  }

  return response.json();
}

export async function processDocuments(
  documentIds: string[],
  companyContext?: string
): Promise<{ message: string; corpus_id: string }> {
  return request("/process", {
    method: "POST",
    body: JSON.stringify({
      document_ids: documentIds,
      company_context: companyContext,
    }),
  });
}

export async function getStatus(): Promise<PipelineStatus> {
  return request("/status");
}

export async function getDocuments(): Promise<DocumentType[]> {
  return request("/documents");
}

export async function clearAllDocuments(): Promise<void> {
  await fetch(`${API_BASE}/documents`, { method: "DELETE" });
}

export async function deleteDocument(documentId: string): Promise<void> {
  await fetch(`${API_BASE}/documents/${documentId}`, { method: "DELETE" });
}

export async function getTaxonomy(): Promise<TaxonomyType | null> {
  return request("/taxonomy");
}

export async function getExtractions(
  documentId?: string
): Promise<ExtractionType[]> {
  const params = documentId ? `?document_id=${documentId}` : "";
  return request(`/extractions${params}`);
}

export async function getEntities(): Promise<EntityType[]> {
  return request("/entities");
}

export async function getContradictions(): Promise<ContradictionType[]> {
  return request("/contradictions");
}

export async function updateEntity(
  id: string,
  canonicalName: string
): Promise<EntityType> {
  return request(`/entities/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ canonical_name: canonicalName }),
  });
}

export async function updateResolution(
  id: string,
  approved: boolean,
  overrideValue?: string
): Promise<void> {
  return request(`/entity-resolutions/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ approved, override_value: overrideValue }),
  });
}

// Taxonomy Templates
export async function getTaxonomyTemplates(): Promise<TaxonomyTemplateType[]> {
  return request("/taxonomy-templates");
}

export async function createTaxonomyTemplate(
  data: { label: string; description: string; dimensions: { name: string; description: string; expected_type: string }[] }
): Promise<TaxonomyTemplateType> {
  return request("/taxonomy-templates", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTaxonomyTemplate(
  id: string,
  data: { label?: string; description?: string; dimensions?: { name: string; description: string; expected_type: string }[] }
): Promise<TaxonomyTemplateType> {
  return request(`/taxonomy-templates/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteTaxonomyTemplate(id: string): Promise<void> {
  await fetch(`${API_BASE}/taxonomy-templates/${id}`, { method: "DELETE" });
}

export async function sendChatMessage(
  message: string,
  sessionId?: string
): Promise<ChatResponseType> {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

export async function getInsights(): Promise<InsightsType> {
  return request("/insights");
}

export async function getEntityTimeline(
  entityId: string
): Promise<EntityTimelineType> {
  return request(`/entities/${entityId}/timeline`);
}
