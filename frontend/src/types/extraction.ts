/**
 * TypeScript types for knowledge extraction from documents.
 *
 * Matches backend schemas from:
 * - app/llm/schemas.py (ExtractedEntity, ExtractedRelation)
 * - app/schemas/source.py (DocumentExtractionPreview, EntityLinkMatch)
 */

// =============================================================================
// Entity Extraction
// =============================================================================

export type EntityCategory =
  | "drug"
  | "disease"
  | "symptom"
  | "biological_mechanism"
  | "treatment"
  | "biomarker"
  | "population"
  | "outcome"
  | "other";

export type ConfidenceLevel = "high" | "medium" | "low";

export interface ExtractedEntity {
  slug: string;
  summary: string;
  category: EntityCategory;
  confidence: ConfidenceLevel;
  text_span: string;
}

// =============================================================================
// Relation Extraction
// =============================================================================

export type RelationType =
  | "treats"
  | "causes"
  | "prevents"
  | "increases_risk"
  | "decreases_risk"
  | "associated_with"
  | "prevalence_in"
  | "mechanism"
  | "contraindicated"
  | "interacts_with"
  | "metabolized_by"
  | "biomarker_for"
  | "affects_population"
  | "measures"
  | "diagnoses"
  | "predicts"
  | "other";

export const ALL_RELATION_TYPES: RelationType[] = [
  "treats",
  "causes",
  "prevents",
  "increases_risk",
  "decreases_risk",
  "associated_with",
  "prevalence_in",
  "mechanism",
  "contraindicated",
  "interacts_with",
  "metabolized_by",
  "biomarker_for",
  "affects_population",
  "measures",
  "diagnoses",
  "predicts",
  "other",
];

export type StatementKind =
  | "finding"
  | "background"
  | "hypothesis"
  | "methodology";

export type FindingPolarity =
  | "supports"
  | "contradicts"
  | "mixed"
  | "neutral"
  | "uncertain";

export type StudyDesign =
  | "meta_analysis"
  | "systematic_review"
  | "randomized_controlled_trial"
  | "nonrandomized_trial"
  | "cohort_study"
  | "case_control_study"
  | "cross_sectional_study"
  | "case_series"
  | "case_report"
  | "guideline"
  | "review"
  | "animal_study"
  | "in_vitro"
  | "background"
  | "unknown";

export interface ExtractedRole {
  entity_slug: string;
  role_type: string;
  source_mention?: string | null;
}

export interface ExtractedRelationEvidenceContext {
  statement_kind: StatementKind;
  finding_polarity?: FindingPolarity | null;
  evidence_strength?: EvidenceStrength | null;
  study_design?: StudyDesign | null;
  sample_size?: number | null;
  sample_size_text?: string | null;
  assertion_text?: string | null;
  methodology_text?: string | null;
  statistical_support?: string | null;
}

export type RelationScopeValue = string | number | boolean | null;

export interface ExtractedRelation {
  relation_type: RelationType;
  /** Set by the backend when the model proposed an unknown type that was coerced to "other". */
  model_proposed_type?: string | null;
  roles: ExtractedRole[];
  confidence: ConfidenceLevel;
  text_span: string;
  notes?: string | null;
  scope?: Record<string, RelationScopeValue> | null;
  evidence_context?: ExtractedRelationEvidenceContext | null;
  study_context?: ExtractedRelationEvidenceContext | null;
}

export type EvidenceStrength =
  | "strong"      // RCTs, meta-analyses
  | "moderate"    // Observational studies
  | "weak"        // Case reports, small studies
  | "anecdotal";  // Individual experiences

// =============================================================================
// Entity Linking
// =============================================================================

export type MatchType = "exact" | "synonym" | "similar" | "none";

export interface EntityLinkMatch {
  extracted_slug: string;
  matched_entity_id: string | null;
  matched_entity_slug: string | null;
  confidence: number;  // 0.0 - 1.0
  match_type: MatchType;
}

// =============================================================================
// Document Upload & Extraction
// =============================================================================

export interface DocumentUploadResponse {
  source_id: string;
  document_text_preview: string;
  document_format: string;
  character_count: number;
  truncated: boolean;
  warnings: string[];
}

export interface DocumentExtractionPreview {
  source_id: string;
  entities: ExtractedEntity[];
  relations: ExtractedRelation[];
  entity_count: number;
  relation_count: number;
  link_suggestions: EntityLinkMatch[];
  needs_review_count?: number | null;
  auto_verified_count?: number | null;
  avg_validation_score?: number | null;
}

export interface BulkSourceExtractionRequest {
  search: string;
  study_budget: number;
}

export interface BulkSourceExtractionItem {
  source_id: string;
  title: string;
  status: "extracted" | "failed";
  entity_count: number;
  relation_count: number;
  needs_review_count: number;
  auto_verified_count: number;
  error?: string | null;
}

export interface BulkSourceExtractionResponse {
  search: string;
  study_budget: number;
  matched_count: number;
  selected_count: number;
  extracted_count: number;
  failed_count: number;
  skipped_count: number;
  results: BulkSourceExtractionItem[];
}

// =============================================================================
// Save Extraction
// =============================================================================

export interface SaveExtractionRequest {
  entities_to_create: ExtractedEntity[];
  entity_links: Record<string, string>;  // extracted_slug -> existing_entity_id
  relations_to_create: ExtractedRelation[];
  user_language?: string;
}

export interface SkippedRelationDetail {
  extraction_id: string;
  relation_type?: string | null;
  text_span?: string | null;
  error: string;
}

export interface SaveExtractionResult {
  entities_created: number;
  entities_linked: number;
  relations_created: number;
  created_entity_ids: string[];
  created_relation_ids: string[];
  warnings: string[];
  skipped_relations: SkippedRelationDetail[];
}

// =============================================================================
// Batch Extraction (All-in-One)
// =============================================================================

export interface BatchExtractionResponse {
  entities: ExtractedEntity[];
  relations: ExtractedRelation[];
}

// =============================================================================
// UI Helper Types
// =============================================================================

/**
 * User decisions for each extracted entity (UI state).
 */
export interface EntityLinkingDecision {
  extracted_slug: string;
  action: "create" | "link" | "skip";
  linked_entity_id?: string;  // If action === "link"
}

/**
 * Combined extraction preview with UI state.
 */
export interface ExtractionWorkflowState {
  preview: DocumentExtractionPreview;
  entity_decisions: Record<string, EntityLinkingDecision>;  // slug -> decision
  selected_relations: Set<string>;  // slugs of relations to create
}
