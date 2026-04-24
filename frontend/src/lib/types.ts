export interface DocumentType {
  id: string;
  original_filename: string;
  file_type: string;
  detected_doc_type: string | null;
  page_count: number | null;
  report_date: string | null;
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
  reason: string | null;
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

// Insights Dashboard types
export interface InsightContradiction {
  id: string;
  dimension_name: string;
  entity_name: string | null;
  doc_a_id: string;
  doc_a_filename: string;
  doc_a_value: string;
  doc_a_date: string | null;
  doc_b_id: string;
  doc_b_filename: string;
  doc_b_value: string;
  doc_b_date: string | null;
  newer_doc: "a" | "b" | null;
  reason: string | null;
  resolution_status: string;
}

export interface InsightEntityReview {
  entity_id: string;
  canonical_name: string;
  entity_type: string;
  review_count: number;
  aliases: string[];
}

export interface InsightStaleness {
  dimension_name: string;
  entity_name: string | null;
  newest_value: string;
  newest_doc_filename: string;
  newest_doc_date: string | null;
  older_value: string;
  older_doc_filename: string;
  older_doc_date: string | null;
}

export interface InsightsType {
  total_contradictions: number;
  total_entities_needing_review: number;
  total_staleness_items: number;
  contradictions: InsightContradiction[];
  entities_needing_review: InsightEntityReview[];
  staleness_items: InsightStaleness[];
}

// Entity Timeline types
export interface TimelineDimensionValue {
  dimension_name: string;
  value: string;
  confidence: number;
  source_pages: number[] | null;
}

export interface TimelineDiff {
  dimension_name: string;
  old_value: string;
  new_value: string;
  change_type: "new" | "updated" | "contradiction";
}

export interface TimelineNode {
  document_id: string;
  document_filename: string;
  document_date: string | null;
  is_approximate_date: boolean;
  dimensions: TimelineDimensionValue[];
  diffs_from_previous: TimelineDiff[];
}

export interface EntityTimelineType {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  timeline: TimelineNode[];
}
