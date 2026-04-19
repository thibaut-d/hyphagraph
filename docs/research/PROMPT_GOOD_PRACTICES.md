# Prompt Engineering Good Practices for Hypergraph Knowledge Extraction

Distilled from the HyphaGraph production prompts (`backend/app/llm/prompts.py`) and from
examining the design choices of the most relevant external implementations:
`HyperGraphRAG`, `Hyper-RAG`, `GraphRAG`, `SciFact`, `SciClaim`, `EvidenceNet`,
`evidencegraph`, and `TruthFinder / CRH`.

Last reviewed: `2026-04-19`

---

## 1. What the External Implementations Teach Us

Before cataloguing rules, it is worth noting what each adjacent system does that is
transferable — and what gap HyphaGraph is filling that they leave open.

### HyperGraphRAG and Hyper-RAG

Both systems construct hyperedges from text via LLM prompts, then retrieve over those
hyperedges at query time.

Key observable prompt choices in their published code and papers:

- **Typed relation extraction over raw embedding.** They do not rely only on vector
  similarity; they prompt the LLM to name a relation type explicitly. This makes
  retrieval interpretable.
- **Atomic relation-per-claim.** Each extracted hyperedge corresponds to one claim span,
  not a document summary. This makes the provenance chain short and direct.
- **No explicit contradiction modeling.** Neither system prompts for polarity, negation,
  or null findings. A contradictory result is silently omitted or overwritten.
  HyphaGraph must do better here.
- **No evidence metadata.** Neither system captures study design, sample size, or
  statistical support. This is acceptable for general RAG but insufficient for scientific
  or medical evidence curation.
- **Minimal role vocabulary.** Both use generic subject/predicate/object or small fixed
  tag sets. HyphaGraph's semantic role vocabulary (agent, target, mechanism, population,
  control_group, etc.) is significantly richer and more precise.

### GraphRAG (Microsoft)

GraphRAG is the most mature open-source pipeline and worth studying as a reference for
what a production extraction prompt looks like at scale.

Key choices:

- **Separate community reports from raw extraction.** Prompts are specialized: entity
  extraction, relationship extraction, and report generation are distinct steps. This is
  the right architecture for quality — avoid asking one prompt to do everything.
- **Claim extraction is optional and off by default.** The docs note that claim prompts
  require domain-specific tuning. This validates HyphaGraph's investment in detailed
  system prompts: generic prompts produce generic evidence.
- **Output validation is explicit.** GraphRAG uses Pydantic-like output parsing with
  retry logic on format errors. Prompt format constraints must be strict and examples
  must be provided.
- **Binary graph, not hyperedges.** GraphRAG only models pairwise relationships.
  This is its structural ceiling: it cannot represent combination therapy, multi-arm
  studies, or n-ary evidence without decomposing them into binary edges and losing
  context.

### SciFact and SciClaim

Both are dataset-and-model projects, not RAG systems, but their annotation schemas are
excellent references for what a well-specified evidence prompt should produce.

Key choices:

- **SciFact** prompts for `SUPPORTS / REFUTES / NOT ENOUGH INFO` at the claim-abstract
  level, with rationale spans. This directly maps to HyphaGraph's `finding_polarity` and
  `text_span`.
- **SciClaim** annotates fine-grained qualifiers: negation, uncertainty, subject, object,
  attribute, value, and evidence type. This is the closest published schema to what
  HyphaGraph captures in `scope`, `notes`, and `evidence_context`.
- Both projects show that **rationale or span anchoring is necessary for reliability**.
  Prompts that do not require the model to identify the specific source span produce
  hallucinated or un-auditable outputs.

### EvidenceNet

The most structurally similar project to HyphaGraph in intent. Key design choices:

- **Evidence quality is first-class.** Prompts assign an evidence quality score based on
  study design, sample size, and statistical support — not just confidence from the
  model's perspective.
- **Entity normalization is separated from extraction.** The LLM extracts surface forms;
  normalization to standard identifiers happens downstream. HyphaGraph follows this same
  separation via `text_span` (source-faithful) vs `slug` (normalized).
- **Source type is captured.** Knowing whether a statement comes from a review, an RCT,
  or a case report changes how it should be weighted. This maps to `study_design` in
  HyphaGraph's `evidence_context`.

### TruthFinder and CRH

These are algorithmic truth-discovery systems, not LLM-based, but they inform what
information extraction prompts must preserve for downstream use.

Key lesson: **conflict resolution requires clean input.** TruthFinder and CRH assume
that each extracted claim is a self-contained, source-attributed tuple. If claims are
merged or paraphrased across sources during extraction, source reliability estimation
breaks. Prompts must therefore never reconcile contradictions and must always preserve
the source attribution for each extracted claim.

---

## 2. Foundational Principles

### 2.1 Conservative extraction beats recall

**Rule:** When in doubt, omit. Do not extract an item that requires outside knowledge,
multi-paragraph synthesis, or inference to justify.

**Why:** A false positive pollutes the knowledge graph permanently. A false negative can
be added later from the same source with a better prompt or a human review pass. The
asymmetry favors omission.

**Implementation pattern in HyphaGraph:**
```
If support is missing or ambiguous, omit the item instead of guessing.
```

**Contrast with naive approaches:** GraphRAG's default claim extraction tends to
over-extract background statements as findings because it does not require a local
span anchor. HyperGraphRAG similarly does not distinguish background from finding.

---

### 2.2 Local span anchoring

**Rule:** Every extracted relation must be justifiable from a short, contiguous source
span — typically 1–3 sentences. Do not build one relation by stitching hints from
distant paragraphs.

**Why:** This is the structural guarantee of provenance. If the model must combine
paragraph 2 and paragraph 8 to form a claim, neither paragraph alone is sufficient
evidence for that claim.

**Implementation pattern:**
```
First identify the minimal claim-bearing sentence or local span that states the
relation, then extract from that span only.
```

**When multi-paragraph synthesis is appropriate:** Only when the source text itself
explicitly states the combined claim in a summary or conclusion sentence that can be
used as the `text_span`.

---

### 2.3 Separate the extraction pass from the reasoning pass

**Rule:** Prompts that extract structured facts must not also reason, synthesize, or
generate recommendations. These are separate tasks with separate prompts.

**Why:** GraphRAG learned this and formalized it. Mixing extraction with synthesis
causes the model to upgrade hedged findings into confident claims, and to merge
contradictory findings into a "balanced" summary that loses the contradiction.

**HyphaGraph pattern:** The system prompt defines the worker role explicitly:
```
You are a biomedical extraction worker for HyphaGraph.
You are not an author, reviewer, or reasoner. Do not add outside medical knowledge.
```

**Entity summaries are the one exception:** Brief general biomedical knowledge is
allowed for entity summaries only (to say what an entity *is*), as long as no
source-specific efficacy or safety claims are added.

---

## 3. Output Format Constraints

### 3.1 Use strict enumerations for all typed fields

Closed-vocabulary fields must be enforced in the prompt with an explicit list and a
fallback.

**Pattern:**
```
relation_type MUST be EXACTLY one of these values (no variations):
- treats
- causes
- prevents
...
If the relationship doesn't fit, use "other".
Do NOT invent new relation types like "has", "correlated_with", etc.
```

**Why:** LLMs will invent variants (`negatively-correlates-with`, `associated_with`)
that break downstream parsing. An explicit list plus a safe fallback (`other`) prevents
this without losing information.

**Applies to:** `relation_type`, `confidence`, `statement_kind`, `finding_polarity`,
`evidence_strength`, `study_design`, `category`, `role_type`.

---

### 3.2 Enforce identifier format constraints explicitly

**Rule:** Slug or identifier format constraints must be stated as a block with valid and
invalid examples, not as a sentence.

**Pattern:**
```
CRITICAL SLUG FORMAT REQUIREMENTS:
- MUST start with a lowercase letter (a-z)
- Can only contain: lowercase letters (a-z), numbers (0-9), hyphens (-)
- MUST be at least 3 characters long
- NO underscores, NO uppercase, NO spaces, NO special characters
- Valid: "aspirin", "cox-2-inhibition", "vitamin-d3"
- INVALID: "2mg" (starts with number), "COX" (uppercase), "α" (too short)
```

**Why:** Models learn from negative examples as effectively as from positive ones when
the failure mode is format-level. Stating only the rule without invalid examples leads
to frequent `_underscore` and `UPPERCASE` outputs.

---

### 3.3 Provide at least two few-shot examples per task

**Rule:** One example teaches a format. Two examples teach a pattern. Use examples that
cover distinct cases — not two instances of the same case.

**Good example pair:**
- A positive finding with `finding_polarity: supports`
- A null or negative finding with `finding_polarity: contradicts`

**What external implementations do:** HyperGraphRAG and Hyper-RAG use minimal examples
(often one). GraphRAG uses slightly richer examples but focuses on format rather than
edge cases. HyphaGraph's batch prompt is notable for covering:
- Combination therapy (two agents in one relation)
- A null finding (`contradicts` polarity with a `causes` relation type)
- A mechanism/background statement (`statement_kind: background`)
- A hypothesis (`finding_polarity: uncertain`)

This is the right coverage. Edge cases must appear in the few-shot section.

---

### 3.4 Request JSON explicitly and specify the wrapper key

**Pattern:**
```
Respond with a JSON object containing an "entities" key.
```

Not:
```
Respond with JSON.
```

**Why:** Without a wrapper key, models sometimes return arrays directly, which breaks
parsers expecting objects. The wrapper key also anchors the model to the expected root
structure.

---

## 4. Provenance and Source Fidelity

### 4.1 Keep normalized identity separate from source wording

**Rule:** Two distinct fields serve two distinct purposes:

| Field | Purpose | Rule |
|-------|---------|------|
| `slug` / `assertion_text` | Normalized, canonical | May normalize surface forms |
| `text_span` / `sample_size_text` / `statistical_support` | Source-faithful | Must copy or minimally trim the source |

**Why:** EvidenceNet's design explicitly separates these concerns. If normalization
corrupts the source text, audit trails break. If the source text prevents normalization,
cross-entity linking breaks. Both fields are necessary.

**Common mistake to avoid:** Paraphrasing the statistical result in `statistical_support`
("statistically significant" instead of "p<0.001"). The raw wording is what the reader
and downstream systems need to verify.

---

### 4.2 Require a text span for every extracted item

**Rule:** Every entity and every relation must have a `text_span` that is an exact
substring (or minimal trim) of the source text.

**Why:** SciFact and SciClaim both demonstrate that rationale spans are the most
important annotation for audit and for training. A relation without a text span is
unverifiable and untraceable — the core failing of naive RAG.

**Guidance on span length:**
- Entity `text_span`: shortest exact mention that identifies the entity.
- Relation `text_span`: the claim-bearing sentence(s), usually 1–3 sentences, sufficient
  on their own to justify the relation.

---

### 4.3 Do not merge or reconcile conflicting statements

**Rule:** If two source spans report contradictory findings, emit two separate relations
with different `finding_polarity` values. Do not average, reconcile, or omit either.

**Why:** TruthFinder and CRH require per-source, per-claim tuples as input. Merging
at extraction time destroys the information needed for source-reliability weighting.
It also hides genuine scientific controversy.

**Implementation pattern:**
```
Never merge or reconcile conflicting statements into a single output item.
If the same entities appear in multiple source spans with different polarity, certainty,
population, comparator, or outcome, emit separate relations.
```

---

## 5. Evidence Context

### 5.1 Distinguish statement kinds

Every extracted relation should carry a `statement_kind` that says what epistemic role
the source text gives it:

| Kind | When to use |
|------|------------|
| `finding` | A direct result or measurement from the study |
| `background` | General knowledge the source cites as context |
| `hypothesis` | A proposed mechanism or prediction the source has not yet tested |
| `methodology` | A description of how something was measured or designed |

**Why:** HyperGraphRAG and Hyper-RAG do not distinguish these. A background statement
about aspirin's mechanism of action has different epistemic weight than an RCT result.
Treating them identically inflates confidence in background claims.

**Common failure mode:** Extracting "aspirin inhibits COX enzymes" as a `finding` when
the source text says "aspirin, which is known to inhibit COX enzymes, was administered
to participants." The mechanism sentence is `background`.

---

### 5.2 Capture null and negative findings

**Rule:** If the source reports that a tested relation was not found, did not reach
significance, or produced mixed results, still extract the relation — set
`finding_polarity` to `contradicts` or `mixed` instead of omitting it.

**Why:** SciFact's `REFUTES` label exists precisely because negative evidence matters.
A null finding for a drug side effect is as informative as a positive one. Omitting
null findings produces a systematically optimistic knowledge graph.

**Specific pattern for safety findings:**
```
For side-effect findings where no significant difference is found versus control:
- Use relation_type "causes" with finding_polarity "contradicts"
- Do NOT use "other"
Example: "no significant increase in nausea compared to placebo"
→ causes(agent=drug, target=nausea, control_group=placebo), finding_polarity=contradicts
```

---

### 5.3 Treat modal language as uncertainty, not as fact

**Rule:** If the source uses "may", "might", "could", "suggests", "potential", or
"appears to", prefer `statement_kind: hypothesis` or `finding_polarity: uncertain`
unless the same span also reports a direct measured result.

**Why:** LLMs tend to drop hedges when paraphrasing. Explicitly instructing the model
to map hedging language to epistemic fields prevents confidence inflation.

---

## 6. N-ary Hyperedge Modeling

This is the most important structural difference between HyphaGraph and all binary-graph
RAG systems (GraphRAG, standard KG pipelines).

### 6.1 Keep n-ary context in one relation, not decomposed binary edges

**Rule:** When a single source statement includes population, comparator, outcome,
mechanism, or condition alongside the core relation, include those explicitly stated
items as additional roles in the **same** relation — do not decompose into separate
binary edges.

**Why:** Decomposing destroys the joint context. "Drug A treats Disease B in elderly
patients with Condition C" becomes three separate binary edges that individually say
nothing about the population or condition specificity.

**Pattern:**
```
HyphaGraph relations are n-ary hyperedges. When one source statement includes
reusable semantic participants such as population, comparator, outcome, mechanism,
or study condition, keep that context as additional roles in the SAME relation.
```

**What binary-graph systems lose:** GraphRAG's edges are (entity, relationship, entity)
triples. A three-arm RCT with two drugs, a placebo, and a specific population cannot
be faithfully represented without decomposition. HyphaGraph's role model handles this
natively.

---

### 6.2 Combination therapy must not be collapsed to single-agent

**Rule:** If the source reports "X combined with Y improved Z", emit one relation with
two `agent` roles — not one `treats(agent=X, target=Z)` and one `treats(agent=Y, target=Z)`.

**Why:** The finding is about the combination. A single-agent relation misrepresents the
evidence and may mislead downstream synthesis.

**Pattern:**
```
"pregabalin combined with duloxetine improved fibromyalgia symptoms vs placebo"
→ treats(agent=pregabalin, agent=duloxetine, target=fibromyalgia, control_group=placebo)

NOT:
→ treats(agent=pregabalin, target=fibromyalgia)
→ treats(agent=duloxetine, target=fibromyalgia)
```

**Exception:** If the source explicitly says "the improvement was due to drug X alone",
a single-agent relation is appropriate.

---

### 6.3 Do not add roles not stated in the source span

**Rule:** Additional context roles (population, comparator, mechanism) may only be
included if they are explicitly stated in the same local span being extracted. Do not
pull context from other paragraphs to enrich a relation.

**Why:** This preserves the integrity of the local-span anchor. A role that comes from
paragraph 3 cannot be attributed to the text span from paragraph 1.

---

## 7. Entity Modeling

### 7.1 One canonical entity per real-world thing per batch

**Rule:** If the same entity appears under multiple surface forms within one extraction
batch, emit one canonical entity record under the most normalized slug and use that slug
in all relations. Do not emit near-duplicate records.

**Pattern:**
```
Emit each real-world entity only once per extraction batch. Merge repeated mentions
under one canonical slug instead of duplicating near-identical entities.
```

---

### 7.2 Entity summaries describe the entity, not the source's claim

**Rule:** Entity `summary` should describe what the entity is in neutral, general terms.
It must not add the source's efficacy, safety, or recommendation claims.

| Correct | Incorrect |
|---------|-----------|
| "Nonsteroidal anti-inflammatory drug and antiplatelet medicine." | "Used in combination therapies for fibromyalgia." |
| "Chronic pain disorder characterized by widespread pain." | "Responds well to duloxetine in adults." |

**Why:** Entity pages in a knowledge graph are shared across sources. Encoding one
source's claim in the entity summary corrupts the cross-source record.

---

### 7.3 Do not create entities for metadata

**Rule:** Dosage, duration, timeframe, sample size, and study design are not entities.
They belong in `scope` (for applicability qualifiers) or `evidence_context` (for study
metadata).

**Specific anti-patterns to suppress:**
```
Do NOT create: "duration-short-term", "dose-high", "duration-long-term"
Do NOT create entities for: "12 weeks", "60mg daily", "150 participants"
```

**Why:** These "entities" do not have their own pages in the knowledge graph. Treating
them as entities inflates the entity count with non-reusable noise and makes the
relation role list harder to read.

---

### 7.4 Prefer relation-bearing entities over document artifacts

**Rule:** Do not extract entities that are paper artifacts — "study", "authors",
"results", "table", "figure", "intervention group", "control group" — unless the source
explicitly uses them as real participants in a relation.

**Why:** These are incidental to the document format, not to the biomedical knowledge
being extracted. They produce relations like "study measures outcome" which add no
knowledge.

---

## 8. Self-Verification Patterns

### 8.1 Silent second pass

**Rule:** Instruct the model to perform a silent completeness audit before returning its
output.

**Pattern:**
```
Before finalizing output, do one silent second pass over the text to check for:
- missed claim-bearing spans
- missed relation participants
- missed null or contradictory findings
```

**Why:** LLMs tend to stop extracting when they reach the end of their working context,
which often means later paragraphs are under-extracted. A second-pass instruction
partially compensates for this.

---

### 8.2 Role integrity check

**Rule:** Require that every `entity_slug` used in a relation's `roles` array is also
present in the `entities` array.

**Pattern:**
```
Every role entity_slug used in a relation MUST be present in the identified entity list.
```

**Why:** Orphan slugs in relations indicate that the model invented a participant that
was not explicitly identified. This is a structural form of hallucination.

**Core role requirements (for specific types):**
```
treats   → MUST include agent and target
causes   → MUST include agent and target or outcome
prevents → MUST include agent and target or outcome
biomarker_for → MUST include biomarker and target or condition
measures → MUST include measured_by and target or outcome
```

---

## 9. Role Persona and Framing

### 9.1 Define the role before any rules

**Rule:** The system prompt's first statement should define who the model is in this
task, not what it should do. The role constrains the model's generative identity.

**Pattern:**
```
You are a biomedical extraction worker for HyphaGraph.
Your role is to extract source-grounded information from scientific and medical texts.
You are not an author, reviewer, or reasoner.
```

**Why:** Role framing is more durable than rule enumeration. A model told it is an
"extraction worker" will resist the pull toward synthesis and editorialization throughout
a long extraction task.

**Contrast:** A prompt that starts with "Extract entities and relations from the
following text" gives the model no identity constraint. It will naturally drift toward
summarization when the text is complex.

---

### 9.2 Separate system prompt from user-turn content

**Rule:** The system prompt contains the persona, global rules, and output schema.
The user turn contains the source text and task-specific parameters. Never mix them.

**Why:** This is the pattern GraphRAG uses and the one the Anthropic API is designed for.
It allows the system prompt to be cached for repeated calls over many documents, which
is significant at scale.

---

## 10. What to Avoid

A condensed list of anti-patterns, each validated by at least one external implementation
failure or HyphaGraph production incident:

| Anti-pattern | Consequence | Rule |
|-------------|-------------|------|
| Inventing relation types | Breaks downstream parser | Use only the fixed enum, fallback to `other` |
| Creating entities for metadata | Inflates entity count with noise | Keep dosage/duration in scope/evidence_context |
| Collapsing combination therapy to single agent | Misrepresents evidence | Two agent roles in one relation |
| Omitting null findings | Optimism bias in the graph | Extract with `finding_polarity: contradicts` |
| Merging contradictory findings | Destroys conflict signal | Always emit separate relations |
| Paraphrasing in `text_span` | Breaks audit trail | `text_span` must be exact source substring |
| Upgrading hedged language | Inflates confidence | Map modal language to `hypothesis` or `uncertain` |
| Adding context roles from other paragraphs | Breaks local span anchor | Only roles explicitly stated in the source span |
| Slugs starting with numbers or using underscores | Breaks identifier parsing | Enforce slug format with negative examples |
| One prompt for extraction + synthesis | Conflation of epistemic modes | Separate extraction prompts from generation prompts |

---

## 11. Prompt Versioning and Iteration

### 11.1 Treat prompts as code

**Rule:** Every significant change to a system prompt or extraction prompt should be
committed with a message that describes what behavior it changes and why, not just what
text was added.

**Why:** Prompts are the most impactful single point of control over output quality.
Silent drift in prompt wording accumulates into untraceable quality changes.

### 11.2 Evaluate against edge cases, not just happy paths

When iterating on extraction prompts, the test cases that matter most are:

- A null finding (did the model extract it with `contradicts` polarity?)
- A combination therapy statement (did the model emit two agent roles?)
- A background statement about mechanism (did the model mark it as `background`?)
- A hedged hypothesis (did the model mark it as `hypothesis` or `uncertain`?)
- A source span with no core role (did the model correctly omit the relation?)

These are the cases that naive LLM behavior gets wrong. A prompt that handles all five
correctly is a good extraction prompt.

---

## Appendix: Quick Reference by Decision Point

| Decision | Guidance |
|---------|---------|
| Should I extract this claim? | Only if a short local span fully supports it |
| Positive or negative finding? | Extract either; use `finding_polarity` to distinguish |
| Two similar spans? | Emit two relations; never merge |
| Combination drug finding? | One relation with two `agent` roles |
| Dosage / duration? | `scope` or `evidence_context`, not an entity |
| Hedged or modal claim? | `hypothesis` or `finding_polarity: uncertain` |
| Conflicting spans? | Separate relations, never reconcile |
| Entity appears twice? | One canonical slug, same slug in all roles |
| Context from another paragraph? | Omit — local span only |
| No matching relation type? | Use `other`, never invent a type |
