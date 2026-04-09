"""
Prompt templates for LLM-based knowledge extraction.

Contains system prompts and extraction templates for:
- Entity extraction
- Relation extraction
- Claim extraction
- Entity linking
"""
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
- Be precise and conservative in extraction
- Distinguish between established facts, hypotheses, and reported findings
- Treat a study finding, a background statement, and a hypothesis as different statement kinds
- Note uncertainty levels when present in the source
- Preserve relation applicability context when present, including population, dosage, comparator, timeframe, and study conditions
- Preserve evidence-context details when present, including source type, study design, sample size, and statistical support
- Never merge or reconcile conflicting statements into a single output item
- Use standardized medical terminology only when it is already present in the text or is a direct surface-form normalization of the same mention
- Preserve numerical values and dosages exactly as stated
"""


# =============================================================================
# Entity Extraction Prompts
# =============================================================================

ENTITY_EXTRACTION_PROMPT = """Extract all relevant biomedical entities from the following text.

For each entity, provide:
- slug: A unique identifier following STRICT format rules (see below)
- summary: A brief source-bounded description in English (prefer a short phrase or single sentence)
- category: The entity type (drug, disease, symptom, biological_mechanism, treatment, biomarker, population, outcome, other)
- confidence: Your confidence in this extraction (high, medium, low)
- text_span: The exact text from the source that mentions this entity

SUMMARY RULES:
- Keep the summary grounded in the source mention and its immediate local context
- Do NOT add background medical facts that are not stated in the provided text
- Do NOT expand the summary into a general encyclopedia definition
- If the text gives only the entity name with no local description, use a minimal summary closely matching the mention
- Do not create standalone entities for dosage, duration, timeframe, sample size, or study design metadata. Keep those as relation scope or evidence context instead.

CRITICAL SLUG FORMAT REQUIREMENTS:
- MUST start with a lowercase letter (a-z)
- Can only contain: lowercase letters (a-z), numbers (0-9), hyphens (-)
- MUST be at least 3 characters long
- NO underscores, NO uppercase, NO spaces, NO special characters
- Valid examples: "aspirin", "migraine-headache", "cox-2-inhibition", "vitamin-d3"
- INVALID examples: "2mg" (starts with number), "COX" (uppercase), "α" (too short), "cox_inhibition" (underscore)

Categories:
- drug: Medications, pharmaceuticals, active ingredients
- disease: Medical conditions, disorders, illnesses
- symptom: Observable signs or symptoms of conditions
- biological_mechanism: Pathways, mechanisms, physiological processes
- treatment: Therapeutic interventions (non-drug)
- biomarker: Measurable indicators (lab values, proteins, genes)
- population: Patient groups, demographics (e.g., "adults over 65")
- outcome: Clinical outcomes, endpoints (e.g., "mortality", "quality of life")
- other: Source-stated entities that can participate in relations but do not fit another category, such as comparator/control groups, study arms, or named conditions explicitly mentioned in the source

Text to analyze:
{text}

Respond with a JSON object containing an "entities" key. Example format:
```json
{{
  "entities": [
  {{
    "slug": "aspirin",
    "summary": "Aspirin (acetylsalicylic acid), as named in the source text.",
    "category": "drug",
    "confidence": "high",
    "text_span": "aspirin (acetylsalicylic acid)"
  }},
  {{
    "slug": "migraine-headache",
    "summary": "Migraine headaches mentioned as the treated condition.",
    "category": "disease",
    "confidence": "high",
    "text_span": "migraine headaches"
  }},
  {{
    "slug": "cox-enzyme-inhibition",
    "summary": "Cyclooxygenase (COX) enzyme inhibition described in the source.",
    "category": "biological_mechanism",
    "confidence": "high",
    "text_span": "irreversibly inhibiting cyclooxygenase (COX) enzymes"
  }},
  {{
    "slug": "placebo",
    "summary": "The comparator group explicitly stated in the source.",
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

Respond with JSON mapping each mention to either an existing entity_id or "NEW":
```json
{{
  "aspirin": "entity-uuid-123",
  "acetylsalicylic acid": "entity-uuid-123",
  "ibuprofen": "NEW",
  "NSAIDs": "NEW"
}}
```

Consider:
- Synonyms (aspirin = acetylsalicylic acid)
- Abbreviations (NSAID = nonsteroidal anti-inflammatory drug)
- Generic vs brand names
- Spelling variations

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
- confidence: Your confidence in this relation (high, medium, low)
- text_span: The exact text that states this relation
- notes: Any important caveats, conditions, or context
- scope: Applicability qualifiers when explicitly stated, such as population, dosage, duration, comparator, or condition
- evidence_context: Structured metadata with:
  - statement_kind: one of finding, background, hypothesis, methodology
  - finding_polarity: one of supports, contradicts, mixed, neutral, uncertain
  - evidence_strength: one of strong, moderate, weak, anecdotal when support level is stated or directly signaled
  - study_design: one of meta_analysis, systematic_review, randomized_controlled_trial, nonrandomized_trial, cohort_study, case_control_study, cross_sectional_study, case_series, case_report, guideline, review, animal_study, in_vitro, background, unknown
  - sample_size: integer when the source gives a participant count
  - sample_size_text: exact participant-count wording when present
  - assertion_text: faithful source-bounded statement for this relation
  - methodology_text: short methodology/applicability note when explicitly stated
  - statistical_support: exact p-value / CI / RR / effect-size wording when explicitly stated

RELATION EXTRACTION RULES:
- Extract only relations that are explicitly stated in the text
- Do not create a relation from background knowledge or weak implication alone
- Preserve negation, uncertainty, study conditions, dosage, timeframe, comparator, and population in scope or notes when relevant
- Prefer one relation per explicit study statement or finding span
- If the text says an intervention did not work, was inconclusive, or had mixed results, still extract the relation but set evidence_context.finding_polarity accordingly instead of rewriting it as a positive effect
- For side-effect or safety findings where no significant difference is found versus a control or placebo, use "causes" with finding_polarity "contradicts" — do NOT use "other". Example: "no significant increase in nausea compared to placebo" → relation_type "causes", finding_polarity "contradicts". This captures that the study tested whether the drug causes the effect and found no evidence it does more than control.
- If the text gives only a mechanistic assumption, background rationale, or methodology note, mark evidence_context.statement_kind accordingly
- If the text presents competing or contradictory findings, output separate relations rather than merging them
- HyphaGraph relations are hyperedges: when one source statement includes reusable semantic participants such as population, comparator, outcome, mechanism, or study condition, keep that context as additional roles in the SAME relation instead of decomposing the statement into multiple binary relations
- Do not add contextual roles that are not explicitly stated in the same source span
- Put dosage, duration, timeframe, study_design, sample_size, and statistical_support into scope or evidence_context instead of inventing standalone entities for them
- Do not create duration or dosage roles from vague qualifiers alone. Prefer exact values like "12 weeks" or "60mg daily". If the source only says "short-term", "long-term", "high dose", or similar vague language, keep that in notes or methodology_text instead of a role entity.
- Every role entity_slug used in a relation must be present in the identified entity list above

SEMANTIC ROLES (use these instead of subject/object):
- agent: Entity performing action (drug, treatment)
- target: Entity being treated/affected (disease, symptom)
- outcome: Result produced (pain-relief, mortality-reduction)
- mechanism: Biological mechanism (serotonin-reuptake, cox-inhibition)
- population: Patient group (adults, women, elderly)
- condition: Clinical context (chronic-pain, depression)
- biomarker: Diagnostic marker (crp, mirna-223-3p)
- measured_by: Assessment tool (vas, moca)
- control_group: Comparison group (healthy-controls, placebo)
- location: Anatomical site (brain, joints)

CRITICAL: relation_type MUST be EXACTLY one of these values (no variations):
- treats: Drug/treatment treats disease/symptom
- causes: Drug/disease causes symptom/outcome
- prevents: Drug/treatment prevents disease/outcome
- increases_risk: Factor increases risk of disease/outcome
- decreases_risk: Factor decreases risk of disease/outcome
- mechanism: Biological mechanism underlying an effect
- contraindicated: Drug/treatment should not be used with disease/drug
- interacts_with: Drug interacts with another drug
- metabolized_by: Drug is metabolized by enzyme/pathway
- biomarker_for: Biomarker indicates disease/condition
- affects_population: Treatment affects specific population
- measures: Assessment tool/test measures condition/symptom (e.g., "VAS measures pain", "MoCA measures cognition")
- other: Any other type of relationship

IMPORTANT: Do NOT create new relation types. If a relationship doesn't fit the above categories, use "other".
Do NOT use types like: "has", "integrates_with", "diagnosed_by", "correlates_with", "associated_with", etc.

Example roles in output:
- {{"entity_slug": "aspirin", "role_type": "agent"}}
- {{"entity_slug": "migraine", "role_type": "target"}}
- {{"entity_slug": "placebo", "role_type": "control_group"}}

Respond with a JSON object containing a "relations" key:
```json
{{
  "relations": [
  {{
    "relation_type": "treats",
    "roles": [
      {{"entity_slug": "aspirin", "role_type": "agent"}},
      {{"entity_slug": "migraine", "role_type": "target"}},
      {{"entity_slug": "placebo", "role_type": "control_group"}}
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
      {{"entity_slug": "aspirin", "role_type": "agent"}},
      {{"entity_slug": "stomach-irritation", "role_type": "target"}}
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

Only extract relations that are explicitly stated in the text.
Be conservative - avoid inferring relations that are not clearly supported.
"""


# =============================================================================
# Claim Extraction Prompts
# =============================================================================

CLAIM_EXTRACTION_PROMPT = """Extract factual claims from the following scientific text.

Text to analyze:
{text}

For each claim, provide:
- claim_text: The statement being reported, written as a faithful source-bounded paraphrase
- entities_involved: List of entity slugs mentioned in the claim
- claim_type: Type of claim (efficacy, safety, mechanism, epidemiology, other)
- evidence_strength: Strength of evidence (strong, moderate, weak, anecdotal)
- confidence: Your confidence in extracting this claim (high, medium, low)
- text_span: The exact text supporting this claim

CLAIM RULES:
- Preserve uncertainty, negation, modality, and qualifiers from the source
- Keep claim_text close to the source; do not strengthen or generalize it
- Do not collapse multiple competing claims into one synthesized claim
- Assign evidence_strength conservatively based on what the text explicitly indicates about study design or evidence quality
- If evidence quality is unclear, prefer a lower evidence_strength rather than upgrading it

Claim types:
- efficacy: Claims about treatment effectiveness
- safety: Claims about safety, side effects, risks
- mechanism: Claims about biological mechanisms
- epidemiology: Claims about disease prevalence, risk factors
- other: Other factual claims

Evidence strength indicators:
- strong: Randomized controlled trials, meta-analyses, systematic reviews
- moderate: Observational studies, case-control studies
- weak: Case reports, small studies, expert opinion
- anecdotal: Individual experiences, isolated reports

Respond with a JSON object containing a "claims" key:
```json
{{
  "claims": [
  {{
    "claim_text": "Aspirin reduces the risk of heart attack in adults with cardiovascular disease",
    "entities_involved": ["drug-aspirin", "outcome-heart-attack", "population-cvd-adults"],
    "claim_type": "efficacy",
    "evidence_strength": "strong",
    "confidence": "high",
    "text_span": "In adults with cardiovascular disease, daily aspirin therapy reduced the risk of myocardial infarction by 25% (RR 0.75, 95% CI 0.68-0.82)"
  }}
  ]
}}
```

Focus on:
- Quantifiable results (percentages, odds ratios, p-values)
- Population specifics (who the claim applies to)
- Conditions and caveats
- Statistical significance when mentioned

Only extract claims that are explicitly stated in the text.
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
- Do not reconcile contradictions or competing findings; keep them as separate items
- Preserve uncertainty, negation, dosage, population, comparator, timeframe, and study conditions
- Preserve proof-level details when explicitly stated, including study design, participant count, and statistical support
- Keep study findings separate from background statements, hypotheses, and methodology notes
- If an item is not clearly supported, omit it instead of guessing
- Prefer precise measurable context. Do not create vague duration/dosage/timeframe entities such as "duration-short-term" when the source does not state an exact value.

Extract:
1. **Entities**: All drugs, diseases, symptoms, treatments, biomarkers, and other relevant entities

   CRITICAL SLUG FORMAT REQUIREMENTS:
   - slug MUST start with a lowercase letter (a-z)
   - slug can only contain: lowercase letters (a-z), numbers (0-9), and hyphens (-)
   - slug MUST be at least 3 characters long
   - NO underscores, NO uppercase, NO spaces, NO special characters
   - Examples: "aspirin", "cox-2-inhibition", "vitamin-d3", "type-2-diabetes"
   - INVALID examples: "2-diabetes" (starts with number), "COX" (uppercase), "α" (too short), "cox_inhibition" (underscore)

   - category: drug, disease, symptom, biological_mechanism, treatment, biomarker, population, outcome, other
   - confidence: high, medium, low
   - summaries must stay source-bounded and must not add background facts not present in the text
   - extract reusable relation participants as entities, including comparator/control groups, study arms, populations, outcomes, and explicitly named conditions
   - do NOT create entities for dosage, duration, timeframe, sample size, or study design metadata; keep them in relation scope or evidence_context

2. **Relations**: Relationships between entities

   CRITICAL: relation_type MUST be EXACTLY one of these values (no variations allowed):
   - treats
   - causes
   - prevents
   - increases_risk
   - decreases_risk
   - mechanism
   - contraindicated
   - interacts_with
   - metabolized_by
   - biomarker_for
   - affects_population
   - measures
   - other

   IMPORTANT: If the relationship doesn't clearly fit one of the specific types above, use "other".
   Do NOT invent new relation types like "has", "integrates_with", "diagnosed_by", "negatively-correlates-with", etc.

   HYPERGRAPH ROLE RULE:
   - HyphaGraph relations are n-ary hyperedges, not only binary subject/object pairs.
   - When a single source statement includes population, comparator, outcome, mechanism, or condition, include those explicitly stated items as additional roles in the SAME relation.
   - Do not split one contextual statement into several binary relations when one n-ary relation can preserve the source context.
   - Do not add contextual roles that are not explicitly stated in the same source span.

   CRITICAL GUIDELINES FOR RELATION DIRECTION:
   - treats: agent is the treatment/drug, target is the disease/symptom
     Example: "duloxetine treats fibromyalgia" (NOT "fibromyalgia treats duloxetine")
   - causes: agent is the cause, target/outcome is the effect/outcome
     Example: "smoking causes cancer" (NOT "cancer causes smoking")
   - biomarker_for: biomarker is the biomarker/test, target is the disease/condition
     Example: "crp biomarker_for inflammation" (NOT "inflammation biomarker_for crp")
   - affects_population: condition is disease/condition, population is the population group
     Example: "fibromyalgia affects_population women" (NOT "women affects_population fibromyalgia")
     SPECIAL CASE: "healthy controls" are NOT affected by the disease - they are comparison groups
     Do NOT create: "disease affects healthy-controls" - this is illogical
   - measures: measured_by is the assessment tool, target/outcome is what it measures
     Example: "vas measures pain" (NOT "pain measures vas")

   - confidence: high, medium, low
   - extract only explicitly stated relations and preserve caveats in notes
   - every role entity_slug used in a relation MUST also appear in the entities array
   - include evidence_context for every relation
   - use scope for applicability qualifiers such as dosage, duration, comparator, and condition when they are stated but do not deserve their own entity page
   - statement_kind should usually be "finding" for explicit study results and should only be "background", "hypothesis", or "methodology" when the text clearly frames it that way
   - finding_polarity should reflect whether the source supports, contradicts, or leaves the relation mixed/uncertain
   - For side-effect or safety findings where no significant difference is found versus a control or placebo, use relation_type "causes" with finding_polarity "contradicts" — do NOT use "other". Example: "no significant increase in nausea vs placebo" → relation_type "causes", finding_polarity "contradicts".
   - study_design, sample_size, and statistical_support should only be included when the source text states them or directly signals them
   - do not create vague duration or dosage role entities from labels like "short-term", "long-term", "high dose", or "standard dose"

3. **Claims**: Factual statements with evidence

   CRITICAL: claim_type MUST be EXACTLY one of these values (no variations allowed):
   - efficacy
   - safety
   - mechanism
   - epidemiology
   - other

   Do NOT use types like "outcome" - use "efficacy" for outcome claims or "other" if unclear.

   CRITICAL: evidence_strength MUST be EXACTLY one of these values:
   - strong
   - moderate
   - weak
   - anecdotal

   - confidence: high, medium, low
   - claim_text must remain a faithful source-bounded paraphrase, not a stronger synthesis

Respond with JSON containing three arrays:
```json
{{
  "entities": [
    {{
      "slug": "aspirin",
      "summary": "Aspirin is a nonsteroidal anti-inflammatory drug...",
      "category": "drug",
      "confidence": "high",
      "text_span": "aspirin"
    }},
    {{
      "slug": "duloxetine",
      "summary": "Duloxetine is an SNRI antidepressant used for depression and pain conditions",
      "category": "drug",
      "confidence": "high",
      "text_span": "duloxetine"
    }},
    {{
      "slug": "fibromyalgia",
      "summary": "Fibromyalgia is a chronic pain disorder characterized by widespread musculoskeletal pain",
      "category": "disease",
      "confidence": "high",
      "text_span": "fibromyalgia"
    }},
    {{
      "slug": "adults",
      "summary": "The adult population explicitly stated in the source.",
      "category": "population",
      "confidence": "high",
      "text_span": "adults"
    }},
    {{
      "slug": "placebo",
      "summary": "The comparator group explicitly stated in the source.",
      "category": "other",
      "confidence": "high",
      "text_span": "placebo"
    }}
  ],
  "relations": [
    {{
      "relation_type": "treats",
      "roles": [
        {{"entity_slug": "duloxetine", "role_type": "agent"}},
        {{"entity_slug": "fibromyalgia", "role_type": "target"}},
        {{"entity_slug": "adults", "role_type": "population"}},
        {{"entity_slug": "placebo", "role_type": "control_group"}}
      ],
      "confidence": "high",
      "text_span": "duloxetine 60mg daily is effective for fibromyalgia in adults compared with placebo",
      "notes": "Context includes adult population, daily dose, and placebo comparator",
      "scope": {{
        "dosage": "60mg daily"
      }},
      "evidence_context": {{
        "statement_kind": "finding",
        "finding_polarity": "supports",
        "evidence_strength": "strong",
        "study_design": "randomized_controlled_trial",
        "assertion_text": "Duloxetine 60mg daily was reported as effective for fibromyalgia in adults compared with placebo.",
        "methodology_text": "Randomized placebo-controlled comparison in adults.",
        "statistical_support": "p<0.001"
      }}
    }},
    {{
      "relation_type": "biomarker_for",
      "roles": [
        {{"entity_slug": "mirna-223-3p", "role_type": "biomarker"}},
        {{"entity_slug": "fibromyalgia", "role_type": "target"}},
        {{"entity_slug": "women", "role_type": "population"}}
      ],
      "confidence": "high",
      "text_span": "miRNA-223-3p levels correlate with pain severity in women with fibromyalgia",
      "notes": "Potential diagnostic biomarker",
      "evidence_context": {{
        "statement_kind": "hypothesis",
        "finding_polarity": "uncertain",
        "evidence_strength": "weak",
        "study_design": "unknown",
        "assertion_text": "miRNA-223-3p was proposed as a potential biomarker in women with fibromyalgia."
      }}
    }},
    {{
      "relation_type": "mechanism",
      "roles": [
        {{"entity_slug": "duloxetine", "role_type": "agent"}},
        {{"entity_slug": "serotonin-reuptake-inhibition", "role_type": "mechanism"}}
      ],
      "confidence": "high",
      "text_span": "duloxetine inhibits serotonin and norepinephrine reuptake",
      "notes": "SNRI mechanism of action",
      "evidence_context": {{
        "statement_kind": "background",
        "finding_polarity": "neutral",
        "study_design": "background",
        "assertion_text": "Duloxetine inhibits serotonin and norepinephrine reuptake."
      }}
    }},
    {{
      "relation_type": "causes",
      "roles": [
        {{"entity_slug": "duloxetine", "role_type": "agent"}},
        {{"entity_slug": "nausea", "role_type": "target"}},
        {{"entity_slug": "placebo", "role_type": "control_group"}}
      ],
      "confidence": "medium",
      "text_span": "no significant difference in nausea rates compared to placebo",
      "notes": "Null finding: duloxetine did not cause significantly more nausea than placebo",
      "evidence_context": {{
        "statement_kind": "finding",
        "finding_polarity": "contradicts",
        "evidence_strength": "weak",
        "study_design": "randomized_controlled_trial",
        "assertion_text": "No significant difference in nausea rates was found between duloxetine and placebo."
      }}
    }}
  ],
  "claims": [
    {{
      "claim_text": "Duloxetine significantly reduced pain scores in fibromyalgia patients compared to placebo",
      "entities_involved": ["duloxetine", "fibromyalgia"],
      "claim_type": "efficacy",
      "evidence_strength": "strong",
      "confidence": "high",
      "text_span": "In randomized controlled trials, duloxetine significantly reduced pain scores in fibromyalgia patients compared to placebo (p<0.001)"
    }},
    {{
      "claim_text": "Daily aspirin therapy reduces myocardial infarction risk by 25% in adults with coronary artery disease",
      "entities_involved": ["aspirin", "myocardial-infarction", "coronary-artery-disease"],
      "claim_type": "efficacy",
      "evidence_strength": "strong",
      "confidence": "high",
      "text_span": "Clinical studies have shown that daily aspirin therapy reduces the risk of myocardial infarction by approximately 25% in adults with coronary artery disease"
    }}
  ]
}}
```

CRITICAL REMINDERS:
- Entity slugs: Must start with letter, only lowercase letters/numbers/hyphens, minimum 3 chars
- Relation types: ONLY use the exact 13 types listed above (use "other" if unsure)
- Claim types: ONLY use efficacy, safety, mechanism, epidemiology, or other
- Evidence strength: ONLY use strong, moderate, weak, or anecdotal

Be thorough but conservative. Only extract information that is clearly and explicitly stated in the text.
"""


# =============================================================================
# Helper Functions
# =============================================================================

def format_entity_extraction_prompt(text: str) -> str:
    """Format the entity extraction prompt with the given text."""
    return ENTITY_EXTRACTION_PROMPT.format(text=text)


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
) -> str:
    """Format the relation extraction prompt with text and extracted entities."""
    entities_str = "\n".join([
        f"- {e['slug']}: {e.get('summary', 'No description')}"
        for e in entities
    ])
    return RELATION_EXTRACTION_PROMPT.format(text=text, entities=entities_str)


def format_claim_extraction_prompt(text: str) -> str:
    """Format the claim extraction prompt with the given text."""
    return CLAIM_EXTRACTION_PROMPT.format(text=text)


def format_batch_extraction_prompt(text: str) -> str:
    """Format the batch extraction prompt with the given text."""
    return BATCH_EXTRACTION_PROMPT.format(text=text)


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
