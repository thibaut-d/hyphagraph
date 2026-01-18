/**
 * TypeScript types for knowledge extraction from documents.
 *
 * Matches backend schemas from:
 * - app/llm/schemas.py (ExtractedEntity, ExtractedRelation, ExtractedClaim)
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
  | "mechanism"
  | "contraindicated"
  | "interacts_with"
  | "metabolized_by"
  | "biomarker_for"
  | "affects_population"
  | "other";

export interface ExtractedRelation {
  subject_slug: string;
  relation_type: RelationType;
  object_slug: string;
  roles: Record<string, string>;
  confidence: ConfidenceLevel;
  text_span: string;
  notes?: string | null;
}

// =============================================================================
// Claim Extraction
// =============================================================================

export type ClaimType =
  | "efficacy"
  | "safety"
  | "mechanism"
  | "epidemiology"
  | "other";

export type EvidenceStrength =
  | "strong"      // RCTs, meta-analyses
  | "moderate"    // Observational studies
  | "weak"        // Case reports, small studies
  | "anecdotal";  // Individual experiences

export interface ExtractedClaim {
  claim_text: string;
  entities_involved: string[];
  claim_type: ClaimType;
  evidence_strength: EvidenceStrength;
  confidence: ConfidenceLevel;
  text_span: string;
}

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
  extracted_text?: string;  // Full extracted text from document (optional)
}

// =============================================================================
// Save Extraction
// =============================================================================

export interface SaveExtractionRequest {
  source_id: string;
  entities_to_create: ExtractedEntity[];
  entity_links: Record<string, string>;  // extracted_slug -> existing_entity_id
  relations_to_create: ExtractedRelation[];
}

export interface SaveExtractionResult {
  entities_created: number;
  entities_linked: number;
  relations_created: number;
  created_entity_ids: string[];
  created_relation_ids: string[];
  warnings: string[];
}

// =============================================================================
// Batch Extraction (All-in-One)
// =============================================================================

export interface BatchExtractionResponse {
  entities: ExtractedEntity[];
  relations: ExtractedRelation[];
  claims: ExtractedClaim[];
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
  selected_claims: Set<string>;  // claim_text of claims to create
}
