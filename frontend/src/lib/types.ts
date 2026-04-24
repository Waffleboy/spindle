export interface DocumentType {
  id: string;
  original_filename: string;
  file_type: string;
  detected_doc_type: string | null;
  page_count: number | null;
  uploaded_at: string;
  processed_at: string | null;
}

export interface TaxonomyDimension {
  name: string;
  description: string;
  expected_type: string;
}

export interface TaxonomyType {
  id: string;
  corpus_id: string;
  dimensions: TaxonomyDimension[];
  doc_type: string;
  company_context: string | null;
  created_at: string;
}

export interface ExtractionType {
  id: string;
  document_id: string;
  taxonomy_schema_id: string;
  dimension_name: string;
  raw_value: string;
  resolved_value: string | null;
  source_pages: number[] | null;
  confidence: number;
  document_filename: string;
}

export interface EntityType {
  id: string;
  canonical_name: string;
  entity_type: string;
  aliases: string[];
  needs_review_count: number;
}

export interface ContradictionType {
  id: string;
  dimension_name: string;
  entity_id: string | null;
  doc_a_id: string;
  doc_b_id: string;
  value_a: string;
  value_b: string;
  doc_a_date: string | null;
  doc_b_date: string | null;
  doc_a_filename: string;
  doc_b_filename: string;
  resolution_status: string;
}

export interface CitationType {
  type: "taxonomy" | "document";
  source: string;
  page: number | null;
  detail: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: CitationType[];
  suggested_queries?: string[];
}

export interface ChatResponseType {
  response: string;
  citations: CitationType[];
  query_type: string;
  suggested_queries: string[];
}

export interface PipelineStatus {
  status: string;
  current_step: string | null;
  steps_completed: string[];
  total_documents: number;
  processed_documents: number;
  error?: string | null;
}

export interface TaxonomyTemplateType {
  id: string;
  label: string;
  description: string;
  dimensions: TaxonomyDimension[];
  created_at: string;
}

export interface EntityResolution {
  id: string;
  entity_id: string;
  extraction_id: string;
  original_value: string;
  resolved_value: string;
  confidence: number;
  approved: boolean | null;
}
