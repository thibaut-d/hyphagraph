"""
Prompt templates for LLM-based knowledge extraction.

Contains system prompts and extraction templates for:
- Entity extraction
- Relation extraction
- Claim extraction
- Entity linking
"""

# =============================================================================
# System Prompts
# =============================================================================

MEDICAL_KNOWLEDGE_SYSTEM_PROMPT = """You are a medical knowledge extraction assistant specializing in biomedical literature analysis.

Your role is to:
1. Extract factual information from scientific and medical texts
2. Identify entities (drugs, diseases, symptoms, treatments, etc.)
3. Identify relations between entities (drug treats disease, drug causes side effect, etc.)
4. Maintain accuracy and avoid speculation
5. Cite specific text spans when possible

Guidelines:
- Be precise and conservative in extraction
- Distinguish between established facts and hypotheses
- Note uncertainty levels when present in the source
- Use standardized medical terminology when possible
- Preserve numerical values and dosages exactly as stated
"""


# =============================================================================
# Entity Extraction Prompts
# =============================================================================

ENTITY_EXTRACTION_PROMPT = """Extract all relevant biomedical entities from the following text.

For each entity, provide:
- slug: A unique identifier following STRICT format rules (see below)
- summary: A brief description (1-2 sentences) in English
- category: The entity type (drug, disease, symptom, biological_mechanism, treatment, biomarker, population, outcome)
- confidence: Your confidence in this extraction (high, medium, low)
- text_span: The exact text from the source that mentions this entity

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

Text to analyze:
{text}

Respond with a JSON array of entities. Example format:
```json
[
  {{
    "slug": "aspirin",
    "summary": "Aspirin is a nonsteroidal anti-inflammatory drug (NSAID) used for pain relief, fever reduction, and anti-platelet effects.",
    "category": "drug",
    "confidence": "high",
    "text_span": "aspirin (acetylsalicylic acid)"
  }},
  {{
    "slug": "migraine-headache",
    "summary": "Migraine is a neurological condition characterized by recurrent severe headaches, often with nausea and light sensitivity.",
    "category": "disease",
    "confidence": "high",
    "text_span": "migraine headaches"
  }},
  {{
    "slug": "cox-enzyme-inhibition",
    "summary": "COX enzyme inhibition is the mechanism by which NSAIDs block prostaglandin synthesis.",
    "category": "biological_mechanism",
    "confidence": "high",
    "text_span": "irreversibly inhibiting cyclooxygenase (COX) enzymes"
  }}
]
```

Only extract entities that are explicitly mentioned or clearly implied in the text.
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
- subject_slug: The entity that is the subject of the relation
- relation_type: The type of relation (MUST be from the exact list below)
- object_slug: The entity that is the object of the relation
- roles: Additional context about the relation (optional)
- confidence: Your confidence in this relation (high, medium, low)
- text_span: The exact text that states this relation
- notes: Any important caveats, conditions, or context

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

Example roles:
- dosage: "100mg daily"
- route: "oral administration"
- duration: "for 7 days"
- effect_size: "reduces risk by 25%"
- population: "in adults over 65"

Respond with a JSON array of relations:
```json
[
  {{
    "subject_slug": "drug-aspirin",
    "relation_type": "treats",
    "object_slug": "disease-migraine",
    "roles": {{
      "dosage": "325-650mg",
      "effect": "reduces pain severity"
    }},
    "confidence": "high",
    "text_span": "aspirin 325-650mg is effective for migraine pain relief",
    "notes": "Most effective when taken at onset of symptoms"
  }},
  {{
    "subject_slug": "drug-aspirin",
    "relation_type": "causes",
    "object_slug": "symptom-stomach-irritation",
    "roles": {{
      "frequency": "common",
      "severity": "mild to moderate"
    }},
    "confidence": "high",
    "text_span": "aspirin commonly causes stomach irritation",
    "notes": "Risk increases with higher doses and prolonged use"
  }}
]
```

Only extract relations that are explicitly stated or strongly implied in the text.
Be conservative - avoid inferring relations that are not clearly supported.
"""


# =============================================================================
# Claim Extraction Prompts
# =============================================================================

CLAIM_EXTRACTION_PROMPT = """Extract factual claims from the following scientific text.

Text to analyze:
{text}

For each claim, provide:
- claim_text: The factual statement being made
- entities_involved: List of entity slugs mentioned in the claim
- claim_type: Type of claim (efficacy, safety, mechanism, epidemiology, other)
- evidence_strength: Strength of evidence (strong, moderate, weak, anecdotal)
- confidence: Your confidence in extracting this claim (high, medium, low)
- text_span: The exact text supporting this claim

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

Respond with a JSON array of claims:
```json
[
  {{
    "claim_text": "Aspirin reduces the risk of heart attack in adults with cardiovascular disease",
    "entities_involved": ["drug-aspirin", "outcome-heart-attack", "population-cvd-adults"],
    "claim_type": "efficacy",
    "evidence_strength": "strong",
    "confidence": "high",
    "text_span": "In adults with cardiovascular disease, daily aspirin therapy reduced the risk of myocardial infarction by 25% (RR 0.75, 95% CI 0.68-0.82)"
  }}
]
```

Focus on:
- Quantifiable results (percentages, odds ratios, p-values)
- Population specifics (who the claim applies to)
- Conditions and caveats
- Statistical significance when mentioned
"""


# =============================================================================
# Batch Extraction Prompt (All-in-One)
# =============================================================================

BATCH_EXTRACTION_PROMPT = """Analyze the following biomedical text and extract all relevant knowledge.

Text to analyze:
{text}

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

   - confidence: high, medium, low

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
    }}
  ],
  "relations": [
    {{
      "subject_slug": "duloxetine",
      "relation_type": "treats",
      "object_slug": "fibromyalgia",
      "roles": {{"dosage": "60mg daily"}},
      "confidence": "high",
      "text_span": "duloxetine 60mg daily is effective for fibromyalgia",
      "notes": "FDA approved indication"
    }},
    {{
      "subject_slug": "aspirin",
      "relation_type": "decreases_risk",
      "object_slug": "myocardial-infarction",
      "roles": {{"dosage": "low-dose daily"}},
      "confidence": "high",
      "text_span": "daily aspirin therapy reduces heart attack risk",
      "notes": "Evidence from clinical trials"
    }},
    {{
      "subject_slug": "duloxetine",
      "relation_type": "mechanism",
      "object_slug": "serotonin-reuptake-inhibition",
      "roles": {{}},
      "confidence": "high",
      "text_span": "duloxetine inhibits serotonin and norepinephrine reuptake",
      "notes": "SNRI mechanism of action"
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
- Relation types: ONLY use the exact 12 types listed above (use "other" if unsure)
- Claim types: ONLY use efficacy, safety, mechanism, epidemiology, or other
- Evidence strength: ONLY use strong, moderate, weak, or anecdotal

Be thorough but conservative. Only extract information that is clearly stated or strongly implied.
"""


# =============================================================================
# Helper Functions
# =============================================================================

def format_entity_extraction_prompt(text: str) -> str:
    """Format the entity extraction prompt with the given text."""
    return ENTITY_EXTRACTION_PROMPT.format(text=text)


def format_relation_extraction_prompt(text: str, entities: list[dict]) -> str:
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
    existing_entities: list[dict]
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
