"""
Prompt templates for LLM-based knowledge extraction.

Contains system prompts and extraction templates for:
- Entity extraction
- Relation extraction
- Entity linking
- Batch extraction (entities + relations in one pass)
- Batch gleaning (append-only second-pass quality recovery)
"""
import json
from typing import TypedDict

from app.schemas.common_types import I18nText

# =============================================================================
# System Prompts
# =============================================================================

MEDICAL_KNOWLEDGE_SYSTEM_PROMPT = """You are a biomedical extraction worker for HyphaGraph.

Your role is to:
1. Extract source-grounded information from scientific and medical texts
2. Identify entities (drugs, diseases, symptoms, treatments, etc.)
3. Identify relations between entities (drug treats disease, drug causes side effect, etc.)
4. Preserve uncertainty, negation, and contradictions exactly as stated
5. Cite specific text spans when possible

Guidelines:
- You are not an author, reviewer, or reasoner. Do not add outside medical knowledge.
- Extract only what is explicitly supported by the provided text.
- If support is missing or ambiguous, omit the item instead of guessing.
- Work sentence-by-sentence or claim-span-by-claim-span. A relation is valid only when you can
  anchor it to a short local supporting span in the source text.
- Before finalizing output, do one silent second pass over the text to check for missed
  claim-bearing spans, missed relation participants, and missed null or contradictory findings.
- If you would need to combine distant hints, broad document themes, or outside knowledge to make
  the statement work, omit it.
- Be precise and conservative in extraction
- Exception: for entity summaries only, you may use brief general biomedical knowledge to say what the entity is, as long as the summary stays neutral and does not add source-specific efficacy, safety, or evidence claims
- Do not collapse combination therapy, adjunct therapy, or co-administration language into a single-agent finding unless the source explicitly attributes the effect to one component
- Keep entity summaries minimal when the source gives only a bare mention or list membership
- Prefer relation-bearing biomedical entities and reusable study context over generic document nouns
  or paper artifacts such as "study", "authors", "results", "table", or "figure"
- Distinguish between established facts, hypotheses, and reported findings
- Treat a study finding, a background statement, and a hypothesis as different statement kinds
- Treat null findings, no-difference findings, and contradictory findings as extractable evidence
  when the tested relation and core participants are explicit in the source span
- Treat modal or hedged language such as "may", "might", "could", "suggests", "potential", or
  "appears to" as uncertainty unless the source also reports direct measured evidence
- Note uncertainty levels when present in the source
- Preserve relation applicability context when present, including population, dosage, comparator, timeframe, and study conditions
- Preserve evidence-context details when present, including source type, study design, sample size, and statistical support
- Never merge or reconcile conflicting statements into a single output item
- Use standardized medical terminology only when it is already present in the text or is a direct surface-form normalization of the same mention
- Preserve numerical values and dosages exactly as stated
- Keep normalized identity separate from source wording: slug and summary may normalize surface
  forms, but text_span, sample_size_text, and statistical_support must stay source-faithful
"""


# =============================================================================
# Entity Extraction Prompts
# =============================================================================

ENTITY_EXTRACTION_PROMPT = """Extract all relevant biomedical entities from the following text.

For each entity, provide:
- slug: A unique identifier following STRICT format rules (see below)
- summary: A brief neutral description in English of what the entity is (prefer a short phrase or single sentence)
- category: The entity type (MUST be one of the values listed in the category section below)
- confidence: Your confidence in this extraction (high, medium, low)
  high   → the entity is explicitly and unambiguously named in the source span with no interpretation needed
  medium → the entity requires minor surface-form normalization or is named with light qualification
  low    → the entity is heavily implied, named only indirectly, or requires meaningful inference
- text_span: The exact text from the source that mentions this entity

SUMMARY RULES:
- Summaries should describe the entity itself, not what this specific source claims about it
- You may use brief general biomedical knowledge to say what the entity is
- Do NOT add source-specific efficacy, safety, recommendation, or evidence claims unless they are part of the entity's core definition
- Do NOT turn a sparse mention into a source-specific use statement
- Prefer a generic definitional summary like "Nonsteroidal anti-inflammatory drug class." over a context-bound summary like "Used in this study to treat chronic pain."
- Keep the summary short and neutral; do not expand it into a long encyclopedia entry
- Do not create standalone entities for dosage, duration, timeframe, sample size, or study design metadata. Keep those as relation scope or evidence context instead.
- Emit each real-world entity only once per extraction batch. Merge repeated mentions under one canonical slug instead of duplicating near-identical entities.
- text_span should be the shortest exact mention that identifies the entity in the source text.
- Prefer entities that participate in an explicit relation or provide reusable study context such as
  population, comparator, control group, biomarker, condition, or outcome.
- Omit generic document nouns or paper artifacts unless the source clearly uses them as real
  biomedical participants in a relation. Usually omit items like "study", "trial", "authors",
  "results", "table", "figure", "intervention group", or "control group" when they do not denote
  a reusable entity page.
- Do not create intervention-arm wrapper entities like "chemotherapy arm", "treatment arm", or
  "high-dose group" when the reusable entity is the intervention itself. Extract the underlying
  intervention entity and keep the arm/group wording only in relation text_span or source_mention.
- Keep normalized identity separate from source wording: slug may normalize the mention, but
  text_span must remain the exact shortest source phrase.

CRITICAL SLUG FORMAT REQUIREMENTS:
- MUST start with a lowercase letter (a-z)
- Can only contain: lowercase letters (a-z), numbers (0-9), hyphens (-)
- MUST be at least 3 characters long
- NO underscores, NO uppercase, NO spaces, NO special characters
- Valid examples: "aspirin", "migraine-headache", "cox-2-inhibition", "vitamin-d3"
- INVALID examples: "2mg" (starts with number), "COX" (uppercase), "α" (too short), "cox_inhibition" (underscore)

{entity_categories}

Text to analyze:
{text}

Respond with a JSON object containing an "entities" key. Example format:
```json
{{
  "entities": [
  {{
    "slug": "aspirin",
    "summary": "Nonsteroidal anti-inflammatory drug and antiplatelet medicine.",
    "category": "drug",
    "confidence": "high",
    "text_span": "aspirin (acetylsalicylic acid)"
  }},
  {{
    "slug": "migraine-headache",
    "summary": "Neurological headache disorder.",
    "category": "disease",
    "confidence": "high",
    "text_span": "migraine headaches"
  }},
  {{
    "slug": "cox-enzyme-inhibition",
    "summary": "Biological process involving inhibition of cyclooxygenase enzymes.",
    "category": "biological_mechanism",
    "confidence": "high",
    "text_span": "irreversibly inhibiting cyclooxygenase (COX) enzymes"
  }},
  {{
    "slug": "placebo",
    "summary": "Inactive comparator or control intervention.",
    "category": "other",
    "confidence": "high",
    "text_span": "placebo"
  }}
  ]
}}
```

Only extract entities that are explicitly mentioned in the text.
Do not create entities purely from implication, world knowledge, or inferred study context.
Do NOT create contextual entities for dosage, duration, timeframe, sample size, or study design. Keep them in relation scope or evidence_context instead.
Do NOT create vague contextual entities like "duration-short-term", "duration-long-term", "dose-high", or "dose-standard". If the source only gives a vague qualifier, keep it in notes or methodology_text instead of turning it into an entity.
"""


ENTITY_LINKING_PROMPT = """Given a list of extracted entity mentions and a list of existing entities in the knowledge base, identify which mentions refer to the same entity.

Extracted mentions:
{mentions}

Existing entities in knowledge base:
{existing_entities}

For each mention, determine:
1. Does it match an existing entity? (exact match, synonym, or abbreviation)
2. If yes, which entity ID does it link to?
3. If no, is it a new entity?

Respond with a JSON object with a "links" key mapping each mention to either an existing entity_id or "NEW":
```json
{{
  "links": {{
    "aspirin": "entity-uuid-123",
    "acetylsalicylic acid": "entity-uuid-123",
    "ibuprofen": "NEW",
    "NSAIDs": "NEW"
  }}
}}
```

Consider:
- Synonyms (aspirin = acetylsalicylic acid)
- Abbreviations (NSAID = nonsteroidal anti-inflammatory drug)
- Generic vs brand names (Tylenol → acetaminophen if the existing entity summary confirms the generic)
- Spelling variations

Hard cases — worked examples:
- Abbreviation to full name: "NSAID" matches an existing "nonsteroidal-anti-inflammatory-drug" entity only if
  the existing entity summary confirms it is the same concept. If the summary is absent or ambiguous, return "NEW".
- Brand to generic: "Tylenol" matches "acetaminophen" if the existing entity summary identifies acetaminophen
  as the active ingredient or generic. If uncertain, return "NEW".
- Class membership is NOT a match: "antibiotic" does NOT match "amoxicillin" even if amoxicillin is an
  antibiotic. Do not merge a class-level mention to a specific drug or disease entity.
- Partial acronym ambiguity: "MS" does NOT match "multiple-sclerosis" or "metabolic-syndrome" unless one
  existing entity clearly and uniquely corresponds to the acronym in this clinical context.

Be conservative:
- If the match is uncertain, return "NEW"
- Do not merge mentions based only on broad class membership or relatedness
- Do not use external knowledge beyond the provided mentions and existing-entity summaries
"""


# =============================================================================
# Relation Extraction Prompts
# =============================================================================

RELATION_EXTRACTION_PROMPT = """Extract relations between entities from the following text.

Entities identified:
{entities}

Text to analyze:
{text}

For each relation, provide:
- relation_type: The type of relation (MUST be from the exact list below)
- roles: Array of entities with their semantic roles (CRITICAL - see semantic roles below)
  For each role include:
  - entity_slug: normalized entity slug
  - role_type: semantic role type
  - source_mention: shortest exact mention for that participant inside this relation's text_span
- confidence: Your confidence in this relation (high, medium, low)
  high   → the relation is explicitly and unambiguously stated in the source span with no interpretation needed
  medium → the relation requires minor interpretation, is stated with light hedging, or involves a surface-form normalization
  low    → the relation is heavily hedged, implicit, or requires meaningful inference to extract
- text_span: The exact text that states this relation
- notes: Any important caveats, conditions, or context
- scope: Applicability qualifiers when explicitly stated. Use only these keys:
  dosage        → exact dose as stated (e.g. "60mg daily", "325-650mg")
  duration      → treatment or observation period (e.g. "12 weeks", "6 months")
  route         → administration route when stated (e.g. "oral", "intravenous")
  frequency     → dosing frequency when stated (e.g. "twice daily", "once weekly")
  comparator    → named comparator arm (e.g. "placebo", "standard care") when not already a role
  condition     → qualifying clinical context (e.g. "refractory cases", "acute phase")
  timeframe     → measurement or follow-up window (e.g. "at week 12", "after 3 months")
  Only include a scope key when the source span states its value explicitly.
  Do not invent or infer scope values. Do not use vague labels like "short-term" or "high dose".
- evidence_context: Structured metadata with:
  - statement_kind: one of finding, background, hypothesis, methodology
  - finding_polarity: one of supports, contradicts, mixed, neutral, uncertain
  - evidence_strength: one of strong, moderate, weak, anecdotal when support level is stated or directly signaled
    Assignment rule — use the strongest level warranted by the source, never inflate it:
    strong   → meta-analysis or systematic review with clear outcomes, or RCT with significant result
    moderate → non-randomized trial, cohort study, case-control study, or cross-sectional study
    weak     → case series, small pilot study, animal study, or in-vitro finding
    anecdotal → single case report or expert opinion without measured data
    Omit evidence_strength entirely when the source does not state or directly signal the study type.
  - study_design: one of meta_analysis, systematic_review, randomized_controlled_trial, nonrandomized_trial, cohort_study, case_control_study, cross_sectional_study, case_series, case_report, guideline, review, animal_study, in_vitro, background, unknown
  - sample_size: integer when the source gives a participant count
  - sample_size_text: exact participant-count wording when present
  - assertion_text: faithful source-bounded statement for this relation
  - methodology_text: short methodology/applicability note when explicitly stated
  - statistical_support: exact p-value / CI / RR / effect-size wording when explicitly stated

RELATION EXTRACTION RULES:
- Extract only relations that are explicitly stated in the text
- Do not create a relation from background knowledge or weak implication alone
- First identify the minimal claim-bearing sentence or local span that states the relation, then extract from that span only.
- Each relation text_span should usually be 1-3 sentences and should be sufficient on its own to justify the relation.
- Do not build one relation by stitching together separate hints from distant paragraphs unless one local span explicitly states the relation.
- Before finalizing JSON, do one silent second pass over the text and check whether each
  claim-bearing span with extracted entities was either captured as a relation or intentionally
  omitted because the source span lacks the required core roles.
- Preserve negation, uncertainty, study conditions, dosage, timeframe, comparator, and population in scope or notes when relevant
- Prefer one relation per explicit study statement or finding span
- If the same entities appear in multiple source spans with different polarity, certainty, population, comparator, or outcome, emit separate relations rather than one merged relation.
- If one source span reports two distinct outcomes or claims, emit separate relations when that preserves the source meaning more faithfully.
- If the text says an intervention did not work, was inconclusive, or had mixed results, still extract the relation but set evidence_context.finding_polarity accordingly instead of rewriting it as a positive effect
- For null efficacy findings such as "did not significantly improve", "no significant difference",
  or "similar to placebo", use finding_polarity "neutral" unless the span explicitly reports worse
  outcomes than the comparator. Do not mark those therapeutic no-difference findings as
  "contradicts".
- For side-effect or safety findings where no significant difference is found versus a control or placebo, use "causes" with finding_polarity "contradicts" — do NOT use "other". Example: "no significant increase in nausea compared to placebo" → relation_type "causes", finding_polarity "contradicts". This captures that the study tested whether the drug causes the effect and found no evidence it does more than control.
- Do NOT use relation_type "other" for ordinary efficacy findings or adverse-event findings when
  the span already makes "treats" or "causes" explicit.
- Use relation_type "associated_with" for explicit non-causal association, correlation, co-occurrence, or comorbidity findings when the source does not claim mechanism or causation.
- Do NOT use "associated_with" when a study reports an intervention/exposure with
  reduced odds, lower risk, increased odds, or higher risk of a measured outcome.
  Use "decreases_risk" for reduced/lower odds or risk and "increases_risk" for
  increased/higher odds or risk, while preserving observational study design and
  comparator context in evidence_context/scope.
- Use relation_type "prevalence_in" for source-stated prevalence or incidence findings tied to a population, condition, study group, or control group.
- Do NOT materialize baseline characteristics, post-matching covariate imbalances,
  or cohort descriptors as intervention relations. Examples: "BMI was higher in
  the treatment cohort at baseline" and "HbA1c remained higher in users" are
  study context/confounding notes, not evidence that the intervention changes BMI
  or HbA1c.
- Do NOT create a separate relation from speculative summary language such as
  "potentially reflecting lower symptom burden" unless the same local span reports
  a direct measured outcome with clear core roles.
- Recommendation-only or screening-only language should usually NOT become a relation unless the same span explicitly states a diagnosis, measurement, prevalence, risk, treatment, or association finding with clear core participants.
- If the text gives only a mechanistic assumption, background rationale, or methodology note, mark evidence_context.statement_kind accordingly
- If the text presents competing or contradictory findings, output separate relations rather than merging them
- HyphaGraph relations are hyperedges: when one source statement includes reusable semantic participants such as population, comparator, outcome, mechanism, or study condition, keep that context as additional roles in the SAME relation instead of decomposing the statement into multiple binary relations
- When a source reports combination therapy, adjunct therapy, co-administration, or "X with Y", include every explicitly named active intervention in the SAME relation as separate agent roles if the finding applies to the combination
- Do not add contextual roles that are not explicitly stated in the same source span
- Put dosage, duration, timeframe, study_design, sample_size, and statistical_support into scope or evidence_context instead of inventing standalone entities for them
- Do not create duration or dosage roles from vague qualifiers alone. Prefer exact values like "12 weeks" or "60mg daily". If the source only says "short-term", "long-term", "high dose", or similar vague language, keep that in notes or methodology_text instead of a role entity.
- Every role entity_slug used in a relation must be present in the identified entity list above
- Every role should include source_mention when the participant is explicitly named in the relation span.
- source_mention must be copied exactly from the local relation text_span, not normalized or paraphrased.
- assertion_text should be a faithful, source-bounded paraphrase of the local finding. Do not strengthen certainty, magnitude, or clinical importance beyond what the text states.
- Keep source wording separate from normalized fields: text_span, sample_size_text, and
  statistical_support should copy or minimally trim the source wording, while assertion_text may
  paraphrase conservatively.
- If the source uses modal or hedged language such as "may", "might", "could", "suggests",
  "potential", or "appears to", prefer evidence_context.statement_kind "hypothesis" or
  finding_polarity "uncertain" unless the same span reports direct measured findings.
- Core role requirements:
  - treats MUST include agent and target
  - causes MUST include the thing causing the effect as agent, plus the adverse event/effect as target or outcome
  - prevents MUST include agent and target or outcome
  - associated_with MUST include target plus condition, population, or study_group
  - prevalence_in MUST include target plus condition, population, study_group, or control_group
  - biomarker_for MUST include biomarker and target or condition
  - measures MUST include measured_by and target or outcome
- control_group, population, and comparator context NEVER replace a missing core role
- In therapeutic findings, a measured clinical outcome like "overall survival", "blood pressure", or
  "quality of life" should usually be the relation's target, even if the sentence also frames it
  as an outcome or endpoint.
- If the source mentions an adverse event like nausea but does not explicitly identify what caused it in the same source span, omit the relation instead of guessing
- If the source only says adverse events were similar to placebo or not serious, do not invent a causes relation unless the active intervention and the adverse event are both explicit in the same span
- If the source says "combined X with Y", "X plus Y", "adjunctive Y", or similar combination language, do NOT emit a single-agent treats relation for only X or only Y unless the text explicitly attributes the effect to that one component
- For combination findings, comparator/control groups are not active agents; include named active interventions as agent roles and keep placebo only as control_group

SEMANTIC ROLES — use ONLY these exact values (no others):
Core roles:
- agent: Entity performing action or causing effect (drug, treatment)
- target: Entity receiving action or being affected (disease, symptom)
- outcome: Result or effect produced (overall-survival, hba1c-reduction)
- mechanism: Biological mechanism involved (gluconeogenesis-inhibition, cox-inhibition)
- population: Patient population or demographic group (adults, older-adults, women)
- condition: Clinical condition or qualifying context (refractory-disease, acute-phase)

Measurement roles:
- biomarker: Diagnostic or prognostic marker (crp, hba1c)
- measured_by: Assessment tool or instrument (mmse, ecog-score)
- control_group: Comparison or control group in study (healthy-controls, placebo)
- study_group: Experimental or named patient group (high-dose-arm, intervention-group)

Contextual roles (only when the participant is a real entity, not a vague label):
- location: Anatomical site (brain, lymph-nodes, lumbar-spine)

CRITICAL: Do NOT invent role types. In particular:
- "comparator_detail" is NOT a valid role — use control_group for comparison arms
- "comparator" is NOT a valid role — use control_group
- Never use role names not listed above

{relation_types}

Example roles in output:
- {{"entity_slug": "aspirin", "role_type": "agent", "source_mention": "aspirin"}}
- {{"entity_slug": "migraine", "role_type": "target", "source_mention": "migraine"}}
- {{"entity_slug": "placebo", "role_type": "control_group", "source_mention": "placebo"}}

Respond with a JSON object containing a "relations" key:
```json
{{
  "relations": [
  {{
    "relation_type": "treats",
    "roles": [
      {{"entity_slug": "aspirin", "role_type": "agent", "source_mention": "aspirin"}},
      {{"entity_slug": "migraine", "role_type": "target", "source_mention": "migraine"}},
      {{"entity_slug": "placebo", "role_type": "control_group", "source_mention": "placebo"}}
    ],
    "confidence": "high",
    "text_span": "aspirin 325-650mg is effective for migraine pain relief",
    "notes": "Most effective when taken at onset of symptoms",
    "scope": {{
      "dosage": "325-650mg"
    }},
    "evidence_context": {{
      "statement_kind": "finding",
      "finding_polarity": "supports",
      "evidence_strength": "moderate",
      "study_design": "unknown",
      "assertion_text": "Aspirin 325-650mg was reported as effective for migraine pain relief.",
      "methodology_text": "Applies when taken at symptom onset."
    }}
  }},
  {{
    "relation_type": "causes",
    "roles": [
      {{"entity_slug": "aspirin", "role_type": "agent", "source_mention": "aspirin"}},
      {{"entity_slug": "stomach-irritation", "role_type": "target", "source_mention": "stomach irritation"}}
    ],
    "confidence": "high",
    "text_span": "aspirin commonly causes stomach irritation",
    "notes": "Risk increases with higher doses and prolonged use",
    "scope": {{
      "dosage": "higher doses"
    }},
    "evidence_context": {{
      "statement_kind": "finding",
      "finding_polarity": "supports",
      "evidence_strength": "moderate",
      "study_design": "unknown",
      "assertion_text": "Aspirin was reported to cause stomach irritation.",
      "methodology_text": "Risk increases with higher doses and prolonged use."
    }}
  }}
  ]
}}
```

Invalid example to OMIT:
- Text span: "adverse events experienced by participants were not serious"
- Wrong extraction: causes(target=nausea, control_group=placebo)
- Reason: the span does not explicitly identify what causes nausea, so the relation is structurally incomplete and should not be emitted

Combination-therapy example:
- Text span: "carboplatin combined with paclitaxel improved progression-free survival compared with carboplatin alone in patients with advanced ovarian cancer"
- Correct extraction shape: treats(agent=carboplatin, agent=paclitaxel, target=advanced-ovarian-cancer, control_group=carboplatin)
- Wrong extraction to avoid: treats(agent=carboplatin, target=advanced-ovarian-cancer, control_group=carboplatin)
- Reason: the finding is about the combination regimen, not carboplatin alone

Only extract relations that are explicitly stated in the text.
Be conservative - avoid inferring relations that are not clearly supported.
"""


# =============================================================================
# Batch Extraction Prompt (All-in-One)
# =============================================================================

BATCH_EXTRACTION_PROMPT = """Analyze the following biomedical text and extract source-grounded knowledge only.

Text to analyze:
{text}

GLOBAL RULES:
- Extract only information explicitly supported by the provided text
- Do not use outside medical knowledge
- Work locally: first identify claim-bearing spans, then extract only from those spans
- A relation is valid only if you can point to a short local text span that is sufficient to justify it
- Do not synthesize one relation from scattered hints across the document unless the source itself states that relation in one local span
- Do not reconcile contradictions or competing findings; keep them as separate items
- Before finalizing JSON, do one silent second pass to catch missed claim-bearing spans, missed
  relation participants, and missed null/contradictory findings
- Preserve uncertainty, negation, dosage, population, comparator, timeframe, and study conditions
- Preserve proof-level details when explicitly stated, including study design, participant count, and statistical support
- Keep study findings separate from background statements, hypotheses, and methodology notes
- If an item is not clearly supported, omit it instead of guessing
- Prefer precise measurable context. Do not create vague duration/dosage/timeframe entities such as "duration-short-term" when the source does not state an exact value.
- Do not flatten combination therapy, adjunct therapy, or co-administration findings into single-agent relations unless the text explicitly attributes the effect to one component
- Prefer relation-bearing biomedical entities and reusable study context over generic document nouns
  or paper artifacts such as "study", "authors", "results", "table", or "figure"
- Keep normalized identity separate from source wording: slug and summary may normalize surface
  forms, but text_span, sample_size_text, and statistical_support must stay source-faithful

Extract:
1. **Entities**: All drugs, diseases, symptoms, treatments, biomarkers, and other relevant entities

   CRITICAL SLUG FORMAT REQUIREMENTS:
   - slug MUST start with a lowercase letter (a-z)
   - slug can only contain: lowercase letters (a-z), numbers (0-9), and hyphens (-)
   - slug MUST be at least 3 characters long
   - NO underscores, NO uppercase, NO spaces, NO special characters
   - Examples: "aspirin", "cox-2-inhibition", "vitamin-d3", "type-2-diabetes"
   - INVALID examples: "2-diabetes" (starts with number), "COX" (uppercase), "α" (too short), "cox_inhibition" (underscore)

   - category: MUST be one of the values in the entity category list below
   - confidence: high, medium, low
     high   → explicitly and unambiguously named in the source span with no interpretation needed
     medium → minor surface-form normalization required, or named with light qualification
     low    → heavily implied, named only indirectly, or requires meaningful inference
   - summaries should describe what the entity is, not what this source claims about it
   - brief general biomedical knowledge is allowed for entity summaries only
   - do not add source-specific efficacy, safety, or recommendation claims to entity summaries
   - if an entity is only named in a list or sparse mention, keep the summary short, generic, and non-interpretive
   - extract reusable relation participants as entities, including comparator/control groups, study arms, populations, outcomes, and explicitly named conditions
   - prefer entities that participate in an explicit relation or provide reusable study context such as population, comparator, control_group, biomarker, condition, or outcome
   - omit generic document nouns or paper artifacts unless the source clearly uses them as real biomedical participants in a relation
   - do NOT create entities for dosage, duration, timeframe, sample size, or study design metadata; keep them in relation scope or evidence_context
   - emit each real-world entity only once per batch; merge repeated mentions into one canonical entity record
   - do not create intervention-arm wrapper entities like "chemotherapy arm" or "treatment group" when the reusable entity is the intervention itself; use the underlying intervention entity and keep the arm/group wording only in source_mention if needed
   - text_span should be the shortest exact source mention for that entity

{entity_categories}

2. **Relations**: Relationships between entities

{relation_types}

   SEMANTIC ROLES — use ONLY these exact values (no others):
   Core roles:
   - agent: Entity performing action or causing effect (drug, treatment)
   - target: Entity receiving action or being affected (disease, symptom)
   - outcome: Result or effect produced (overall-survival, hba1c-reduction)
   - mechanism: Biological mechanism involved (gluconeogenesis-inhibition, cox-inhibition)
   - population: Patient population or demographic group (adults, older-adults, women)
   - condition: Clinical condition or qualifying context (refractory-disease, acute-phase)

   Measurement roles:
   - biomarker: Diagnostic or prognostic marker (crp, hba1c)
   - measured_by: Assessment tool or instrument (mmse, ecog-score)
   - control_group: Comparison or control group in study (healthy-controls, placebo)
   - study_group: Experimental or named patient group (high-dose-arm, intervention-group)

   Contextual roles (only when the participant is a real entity, not a vague label):
   - location: Anatomical site (brain, joints, lumbar-spine)

   CRITICAL: Do NOT invent role types. In particular:
   - "comparator_detail" is NOT a valid role — use control_group for comparison arms
   - "comparator" is NOT a valid role — use control_group
   - Never use role names not listed above

   HYPERGRAPH ROLE RULE:
   - HyphaGraph relations are n-ary hyperedges, not only binary subject/object pairs.
   - When a single source statement includes population, comparator, outcome, mechanism, or condition, include those explicitly stated items as additional roles in the SAME relation.
   - When a single source statement reports combination therapy or co-administration, include every explicitly named active intervention as agent roles in the SAME relation if the finding applies to the combination.
   - Do not split one contextual statement into several binary relations when one n-ary relation can preserve the source context.
   - Do not add contextual roles that are not explicitly stated in the same source span.

   CRITICAL GUIDELINES FOR RELATION DIRECTION:
   - treats: agent is the treatment/drug, target is the disease/symptom
     Example: "metformin treats type-2-diabetes" (NOT "type-2-diabetes treats metformin")
   - causes: agent is the cause, target/outcome is the effect/outcome
     Example: "smoking causes lung-cancer" (NOT "lung-cancer causes smoking")
   - associated_with: target is the focal phenomenon and condition/population is the explicit non-causal associate
     Example: "dysautonomia associated_with fibromyalgia" (NOT "fibromyalgia associated_with dysautonomia" when dysautonomia is the measured finding)
     Use associated_with for explicit source-stated association, correlation, or co-occurrence without causal or mechanistic language.
   - prevalence_in: target is the measured phenomenon and population/condition is where that prevalence is reported
     Example: "dysautonomia prevalence_in chronic-musculoskeletal-pain" (NOT "chronic-musculoskeletal-pain prevalence_in dysautonomia")
     Use prevalence_in for source-stated prevalence or incidence findings.
   - biomarker_for: biomarker is the biomarker/test, target is the disease/condition
     Example: "hba1c biomarker_for type-2-diabetes" (NOT "type-2-diabetes biomarker_for hba1c")
   - affects_population: condition is disease/condition, population is the population group
     Example: "type-2-diabetes affects_population adults-over-65" (NOT "adults-over-65 affects_population type-2-diabetes")
     SPECIAL CASE: "healthy controls" are NOT affected by the disease - they are comparison groups
     Do NOT create: "disease affects healthy-controls" - this is illogical
   - measures: measured_by is the assessment tool, target/outcome is what it measures (yields a score/value)
     Example: "mmse measures cognitive-function" (NOT "cognitive-function measures mmse")
   - diagnoses: measured_by is the test/procedure, target/condition is the diagnosed condition (binary verdict)
     Example: "pcr diagnoses covid-19" (NOT "covid-19 diagnoses pcr")
     Use diagnoses when the source says the test CONFIRMS or IDENTIFIES the condition, not merely quantifies it.
   - predicts: agent/biomarker is the predictor, target/outcome is the future event being forecast
     Example: "brca1-mutation predicts breast-cancer-recurrence" (NOT "breast-cancer-recurrence predicts brca1-mutation")
     Use predicts for PROGNOSTIC findings; use biomarker_for for DIAGNOSTIC associations.

   - confidence: high, medium, low
     high   → explicitly and unambiguously stated in the source span with no interpretation needed
     medium → requires minor interpretation, stated with light hedging, or involves surface-form normalization
     low    → heavily hedged, implicit, or requires meaningful inference to extract
   - extract only explicitly stated relations and preserve caveats in notes
   - first identify the local claim-bearing span; relation extraction should stay anchored to that span
   - relation text_span should usually be 1-3 sentences and should be sufficient on its own to justify the relation
   - every role entity_slug used in a relation MUST also appear in the entities array
   - each role should include source_mention as the shortest exact local phrase for that participant inside text_span whenever the participant is explicitly named
   - source_mention must stay source-faithful; do not paraphrase or normalize it
   - include evidence_context for every relation
   - use scope for applicability qualifiers that are stated but do not deserve their own entity page;
     valid scope keys: dosage, duration, route, frequency, comparator, condition, timeframe;
     only include a scope key when the source span states its value explicitly;
     do not use vague labels like "short-term", "long-term", "high dose", or "standard dose" as scope values
   - statement_kind should usually be "finding" for explicit study results and should only be "background", "hypothesis", or "methodology" when the text clearly frames it that way
   - finding_polarity should reflect whether the source supports, contradicts, or leaves the relation mixed/uncertain
   - null findings and no-difference findings should still be extracted when the tested relation and core participants are explicit
   - for null efficacy findings such as "did not significantly improve", "no significant difference", or "similar to placebo", use finding_polarity "neutral" unless the source explicitly says the intervention performed worse than the comparator
   - if the same entities appear in multiple contradictory or differently qualified spans, emit separate relations instead of merging them
   - if the source uses modal or hedged language such as "may", "might", "could", "suggests", "potential", or "appears to", prefer statement_kind "hypothesis" or finding_polarity "uncertain" unless the same span reports direct measured findings
   - For side-effect or safety findings where no significant difference is found versus a control or placebo, use relation_type "causes" with finding_polarity "contradicts" — do NOT use "other". Example: "no significant increase in nausea vs placebo" → relation_type "causes", finding_polarity "contradicts".
   - Use relation_type "associated_with" for explicit non-causal association, correlation, co-occurrence, or comorbidity findings when the source does not claim mechanism or causation.
   - Do NOT use "associated_with" for intervention/exposure findings that report
     reduced odds, lower risk, increased odds, or higher risk of a measured
     outcome. Use "decreases_risk" for reduced/lower odds or risk and
     "increases_risk" for increased/higher odds or risk, while preserving
     observational study design and comparator context.
   - Use relation_type "prevalence_in" for source-stated prevalence or incidence findings tied to a population, condition, study group, or control group.
   - Do NOT materialize baseline characteristics, post-matching covariate
     imbalances, or cohort descriptors as intervention relations. Examples:
     "BMI was higher in the treatment cohort at baseline" and "HbA1c remained
     higher in users" are study context/confounding notes, not evidence that the
     intervention changes BMI or HbA1c.
   - Do NOT create a separate relation from speculative summary language such as
     "potentially reflecting lower symptom burden" unless the same local span
     reports a direct measured outcome with clear core roles.
   - do NOT use relation_type "other" for ordinary efficacy findings or adverse-event findings when the span already makes "treats" or "causes" explicit
   - Recommendation-only or screening-only language should usually NOT become a relation unless the same span explicitly states a diagnosis, measurement, prevalence, risk, treatment, or association finding with clear core participants.
   - in therapeutic findings, a measured clinical outcome like overall survival, blood pressure, or quality of life should usually be the relation target even if the sentence also frames it as an endpoint or outcome
   - evidence_strength assignment — use the strongest level warranted by the source, never inflate it:
     strong   → meta-analysis or systematic review with clear outcomes, or RCT with significant result
     moderate → non-randomized trial, cohort study, case-control study, or cross-sectional study
     weak     → case series, small pilot study, animal study, or in-vitro finding
     anecdotal → single case report or expert opinion without measured data
     Omit evidence_strength entirely when the source does not state or directly signal the study type.
   - study_design, sample_size, and statistical_support should only be included when the source text states them or directly signals them
   - do not create vague duration or dosage role entities from labels like "short-term", "long-term", "high dose", or "standard dose"
   - assertion_text should be a faithful, source-bounded paraphrase; do not upgrade certainty, magnitude, or recommendation strength
   - text_span, sample_size_text, and statistical_support should copy or minimally trim the source wording; assertion_text may paraphrase conservatively
   - If the text says "combined X with Y", "X plus Y", "co-administered", or similar combination language, do NOT emit a clean single-agent treats relation for only one component unless the text explicitly isolates that component's effect
   - For combination findings, placebo or other comparison arms stay as control_group; they never replace named active intervention agents

Respond with JSON containing two arrays:
```json
{{
  "entities": [
    {{
      "slug": "metformin",
      "summary": "Biguanide antidiabetic agent that reduces hepatic glucose production.",
      "category": "drug",
      "confidence": "high",
      "text_span": "metformin"
    }},
    {{
      "slug": "type-2-diabetes",
      "summary": "Chronic metabolic disorder characterized by insulin resistance and impaired glucose regulation.",
      "category": "disease",
      "confidence": "high",
      "text_span": "type 2 diabetes"
    }},
    {{
      "slug": "adults-over-65",
      "summary": "Adult population aged 65 years or above.",
      "category": "population",
      "confidence": "high",
      "text_span": "adults over 65"
    }},
    {{
      "slug": "placebo",
      "summary": "Inactive comparator or control intervention.",
      "category": "other",
      "confidence": "high",
      "text_span": "placebo"
    }},
    {{
      "slug": "hba1c",
      "summary": "Glycated haemoglobin biomarker reflecting average blood glucose over the preceding 2–3 months.",
      "category": "biomarker",
      "confidence": "high",
      "text_span": "HbA1c"
    }},
    {{
      "slug": "gastrointestinal-adverse-events",
      "summary": "Adverse effects of gastrointestinal origin such as nausea or diarrhoea.",
      "category": "symptom",
      "confidence": "medium",
      "text_span": "gastrointestinal adverse events"
    }},
    {{
      "slug": "hepatic-gluconeogenesis",
      "summary": "Hepatic synthesis of glucose from non-carbohydrate substrates.",
      "category": "biological_mechanism",
      "confidence": "high",
      "text_span": "hepatic gluconeogenesis"
    }},
    {{
      "slug": "carboplatin",
      "summary": "Platinum-based chemotherapy agent used in several solid tumours.",
      "category": "drug",
      "confidence": "high",
      "text_span": "carboplatin"
    }},
    {{
      "slug": "paclitaxel",
      "summary": "Taxane chemotherapy agent that stabilizes microtubules.",
      "category": "drug",
      "confidence": "high",
      "text_span": "paclitaxel"
    }},
    {{
      "slug": "advanced-ovarian-cancer",
      "summary": "Ovarian cancer at an advanced stage with regional or distant spread.",
      "category": "disease",
      "confidence": "high",
      "text_span": "advanced ovarian cancer"
    }},
    {{
      "slug": "carboplatin-monotherapy",
      "summary": "Carboplatin administered as a single agent without combination chemotherapy.",
      "category": "treatment",
      "confidence": "high",
      "text_span": "carboplatin alone"
    }},
    {{
      "slug": "mmse",
      "summary": "Mini-Mental State Examination, a brief standardized cognitive screening instrument.",
      "category": "other",
      "confidence": "high",
      "text_span": "Mini-Mental State Examination (MMSE)"
    }},
    {{
      "slug": "cognitive-function",
      "summary": "Capacity for mental processes including memory, attention, and executive function.",
      "category": "outcome",
      "confidence": "high",
      "text_span": "cognitive function"
    }}
  ],
  "relations": [
    {{
      "relation_type": "treats",
      "roles": [
        {{"entity_slug": "metformin", "role_type": "agent", "source_mention": "metformin"}},
        {{"entity_slug": "type-2-diabetes", "role_type": "target", "source_mention": "type 2 diabetes"}},
        {{"entity_slug": "adults-over-65", "role_type": "population", "source_mention": "adults over 65"}},
        {{"entity_slug": "placebo", "role_type": "control_group", "source_mention": "placebo"}}
      ],
      "confidence": "high",
      "text_span": "metformin 500mg twice daily significantly reduced HbA1c compared with placebo in adults over 65 with type 2 diabetes (p < 0.001)",
      "notes": "Dose-specific finding in an older adult population",
      "scope": {{
        "dosage": "500mg twice daily"
      }},
      "evidence_context": {{
        "statement_kind": "finding",
        "finding_polarity": "supports",
        "evidence_strength": "strong",
        "study_design": "meta_analysis",
        "sample_size": 1240,
        "sample_size_text": "1,240 participants",
        "assertion_text": "Metformin 500mg twice daily significantly reduced HbA1c compared with placebo in adults over 65 with type 2 diabetes.",
        "statistical_support": "p < 0.001"
      }}
    }},
    {{
      "relation_type": "biomarker_for",
      "roles": [
        {{"entity_slug": "hba1c", "role_type": "biomarker", "source_mention": "HbA1c"}},
        {{"entity_slug": "type-2-diabetes", "role_type": "target", "source_mention": "type 2 diabetes"}}
      ],
      "confidence": "high",
      "text_span": "HbA1c levels were used to monitor glycaemic control in participants with type 2 diabetes",
      "evidence_context": {{
        "statement_kind": "background",
        "finding_polarity": "neutral",
        "study_design": "background",
        "assertion_text": "HbA1c was used as a glycaemic control marker in type 2 diabetes participants."
      }}
    }},
    {{
      "relation_type": "mechanism",
      "roles": [
        {{"entity_slug": "metformin", "role_type": "agent", "source_mention": "metformin"}},
        {{"entity_slug": "hepatic-gluconeogenesis", "role_type": "mechanism", "source_mention": "hepatic gluconeogenesis"}}
      ],
      "confidence": "high",
      "text_span": "metformin reduces fasting glucose primarily by inhibiting hepatic gluconeogenesis",
      "evidence_context": {{
        "statement_kind": "background",
        "finding_polarity": "neutral",
        "study_design": "background",
        "assertion_text": "Metformin reduces fasting glucose primarily by inhibiting hepatic gluconeogenesis."
      }}
    }},
    {{
      "relation_type": "measures",
      "roles": [
        {{"entity_slug": "mmse", "role_type": "measured_by", "source_mention": "Mini-Mental State Examination (MMSE)"}},
        {{"entity_slug": "cognitive-function", "role_type": "outcome", "source_mention": "cognitive function"}}
      ],
      "confidence": "high",
      "text_span": "Cognitive function was assessed using the Mini-Mental State Examination (MMSE) at baseline and month 6",
      "notes": "Cognitive screening instrument used as secondary endpoint",
      "evidence_context": {{
        "statement_kind": "methodology",
        "finding_polarity": "neutral",
        "assertion_text": "MMSE was used to assess cognitive function at baseline and month 6.",
        "methodology_text": "Assessment conducted at baseline and month 6."
      }}
    }},
    {{
      "relation_type": "causes",
      "roles": [
        {{"entity_slug": "metformin", "role_type": "agent", "source_mention": "metformin"}},
        {{"entity_slug": "gastrointestinal-adverse-events", "role_type": "target", "source_mention": "gastrointestinal adverse events"}},
        {{"entity_slug": "placebo", "role_type": "control_group", "source_mention": "placebo"}}
      ],
      "confidence": "medium",
      "text_span": "no significant difference in gastrointestinal adverse events was observed between metformin and placebo groups",
      "notes": "Null safety finding: metformin did not cause significantly more gastrointestinal adverse events than placebo",
      "evidence_context": {{
        "statement_kind": "finding",
        "finding_polarity": "contradicts",
        "evidence_strength": "strong",
        "study_design": "meta_analysis",
        "assertion_text": "No significant difference in gastrointestinal adverse events was found between metformin and placebo."
      }}
    }},
    {{
      "relation_type": "treats",
      "roles": [
        {{"entity_slug": "carboplatin", "role_type": "agent", "source_mention": "carboplatin"}},
        {{"entity_slug": "paclitaxel", "role_type": "agent", "source_mention": "paclitaxel"}},
        {{"entity_slug": "advanced-ovarian-cancer", "role_type": "target", "source_mention": "advanced ovarian cancer"}},
        {{"entity_slug": "carboplatin-monotherapy", "role_type": "control_group", "source_mention": "carboplatin alone"}}
      ],
      "confidence": "high",
      "text_span": "carboplatin combined with paclitaxel improved progression-free survival compared with carboplatin alone in patients with advanced ovarian cancer",
      "notes": "Combination finding; effect is attributed to the carboplatin-paclitaxel regimen, not either agent alone.",
      "evidence_context": {{
        "statement_kind": "finding",
        "finding_polarity": "supports",
        "evidence_strength": "strong",
        "study_design": "randomized_controlled_trial",
        "assertion_text": "Carboplatin combined with paclitaxel improved progression-free survival versus carboplatin alone in advanced ovarian cancer."
      }}
    }}
  ]
}}
```

CRITICAL REMINDERS:
- Entity slugs: Must start with letter, only lowercase letters/numbers/hyphens, minimum 3 chars
- Relation types: ONLY use the exact relation types listed above (use "other" only when none fit)
- Evidence strength: ONLY use strong, moderate, weak, or anecdotal

Be thorough but conservative. Only extract information that is clearly and explicitly stated in the text.
"""


BATCH_EXTRACTION_GLEANING_PROMPT = """Review the biomedical source text and the existing extraction JSON below.

Your task is append-only quality recovery:
- Return ONLY entities and relations that were genuinely missed in the existing extraction
- Do NOT repeat existing items
- Do NOT rewrite, "improve", rename, merge, split, or correct existing items
- If an existing item looks imperfect, leave it alone and only add clearly missing items
- If nothing important is missing, return empty arrays for both "entities" and "relations"

Focus on missed:
- claim-bearing spans
- relation participants needed by an explicit relation
- null findings, no-difference findings, and contradictory findings
- comparator, population, outcome, and condition entities explicitly needed by a new relation

Follow the same extraction rules as the main batch prompt:
- Extract only information explicitly supported by the text
- Keep findings, background, hypotheses, and methodology separate
- Keep relation scope and evidence context source-faithful
- Every relation role entity_slug must already exist in the prior extraction or be included as a NEW entity in this response
- Keep output append-only; never modify prior extraction content

Original text:
{text}

Existing extraction JSON:
```json
{existing_extraction_json}
```

Return JSON with exactly this shape:
```json
{{
  "entities": [],
  "relations": []
}}
```
"""


# =============================================================================
# Static fallbacks — used when the database is unavailable
# =============================================================================

_STATIC_ENTITY_CATEGORIES = """CRITICAL: category MUST be EXACTLY one of these values (no others allowed):
   - drug: Medications, pharmaceuticals, active ingredients
   - disease: Medical conditions, disorders, illnesses
   - symptom: Observable signs or symptoms of conditions
   - biological_mechanism: Pathways, mechanisms, physiological processes
   - treatment: Therapeutic interventions (non-drug)
   - biomarker: Measurable indicators (lab values, proteins, genes)
   - population: Patient groups, demographics (e.g., "adults over 65")
   - outcome: Clinical outcomes, endpoints (e.g., "mortality", "quality of life")
   - other: Source-stated entities that do not fit any other category (comparator groups, study arms, etc.)

   IMPORTANT: Do NOT invent new category names. If an entity does not fit any listed category, use 'other'."""

_STATIC_RELATION_TYPES = """CRITICAL: relation_type MUST be EXACTLY one of these values (no variations):
   - treats: Drug/treatment is the active agent treating a disease or symptom
   - causes: Drug, disease, or exposure causes a symptom or outcome
   - prevents: Drug/treatment prevents disease or outcome
   - increases_risk: Factor increases risk of disease or outcome
   - decreases_risk: Factor decreases risk of disease or outcome
   - associated_with: Explicit non-causal association, correlation, co-occurrence, or comorbidity
   - prevalence_in: Source-stated prevalence or incidence of a phenomenon within a population or condition
   - mechanism: Biological mechanism underlying an effect
   - contraindicated: Drug/treatment should not be used with disease/drug
   - interacts_with: Drug interacts with another drug
   - metabolized_by: Drug is metabolized by enzyme/pathway
   - biomarker_for: Biomarker indicates disease/condition
   - affects_population: Condition or exposure affects a patient population
   - measures: Assessment tool/test QUANTIFIES a value (score, magnitude); output is a number or level
   - diagnoses: Test/tool confirms presence or absence of a condition (binary yes/no clinical verdict)
   - predicts: Variable/biomarker forecasts a FUTURE clinical outcome or prognosis
   - other: Relationship that does not fit any specific type above

   IMPORTANT: If the relationship doesn't clearly fit one of the specific types above, use "other".
   Do NOT invent new relation types like "has", "regulates", "inhibits", "activates", or "diagnosed_by".
   Use "associated_with" for explicit non-causal co-occurrence/correlation findings.
   Do NOT use "associated_with" when an intervention/exposure is linked to reduced/lower
   or increased/higher odds/risk of a measured outcome; use "decreases_risk" or
   "increases_risk" respectively.
   Use "prevalence_in" for source-stated prevalence or incidence findings.
   Do NOT create intervention relations from baseline characteristics, post-matching
   covariate imbalances, or speculative summary language.
   "other" is appropriate only when the core participants and their direction are clear but the type
   genuinely does not map to any named type. Do NOT use "other" as a catch-all for vague spans:
   if the source span is too ambiguous to identify clear core roles, omit the relation entirely."""


# =============================================================================
# Helper Functions
# =============================================================================

def format_entity_extraction_prompt(
    text: str,
    entity_categories: str | None = None,
) -> str:
    """Format the entity extraction prompt with the given text and dynamic category list."""
    return ENTITY_EXTRACTION_PROMPT.format(
        text=text,
        entity_categories=entity_categories or _STATIC_ENTITY_CATEGORIES,
    )


class RelationPromptEntity(TypedDict):
    slug: str
    summary: str | None
    category: str


class ExistingPromptEntity(TypedDict):
    id: str
    slug: str
    summary: str | I18nText | None


def format_relation_extraction_prompt(
    text: str,
    entities: list[RelationPromptEntity],
    relation_types: str | None = None,
) -> str:
    """Format the relation extraction prompt with text, entities, and dynamic type list."""
    entities_str = "\n".join([
        f"- {e['slug']}: {e.get('summary', 'No description')}"
        for e in entities
    ])
    return RELATION_EXTRACTION_PROMPT.format(
        text=text,
        entities=entities_str,
        relation_types=relation_types or _STATIC_RELATION_TYPES,
    )


def format_batch_extraction_prompt(
    text: str,
    relation_types: str | None = None,
    entity_categories: str | None = None,
) -> str:
    """Format the batch extraction prompt with dynamic relation types and entity categories."""
    return BATCH_EXTRACTION_PROMPT.format(
        text=text,
        relation_types=relation_types or _STATIC_RELATION_TYPES,
        entity_categories=entity_categories or _STATIC_ENTITY_CATEGORIES,
    )


def format_batch_gleaning_prompt(
    text: str,
    existing_extraction: dict[str, object],
) -> str:
    """Format the append-only gleaning prompt with the given text and prior extraction."""
    existing_extraction_json = json.dumps(
        existing_extraction,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
    )
    return BATCH_EXTRACTION_GLEANING_PROMPT.format(
        text=text,
        existing_extraction_json=existing_extraction_json,
    )


def format_entity_linking_prompt(
    mentions: list[str],
    existing_entities: list[ExistingPromptEntity],
) -> str:
    """Format the entity linking prompt with mentions and existing entities."""
    mentions_str = ", ".join(f'"{m}"' for m in mentions)
    entities_str = "\n".join([
        f"- ID: {e['id']}, Slug: {e['slug']}, Summary: {e.get('summary', 'No description')}"
        for e in existing_entities
    ])
    return ENTITY_LINKING_PROMPT.format(
        mentions=mentions_str,
        existing_entities=entities_str
    )
