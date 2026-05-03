from app.llm.prompts import (
    BATCH_EXTRACTION_PROMPT,
    BATCH_EXTRACTION_GLEANING_PROMPT,
    ENTITY_EXTRACTION_PROMPT,
    ENTITY_LINKING_PROMPT,
    MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
    RELATION_EXTRACTION_PROMPT,
    format_batch_extraction_prompt,
    format_batch_gleaning_prompt,
)


def test_system_prompt_forbids_outside_knowledge_and_merging_conflicts():
    assert "Do not add outside medical knowledge" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "for entity summaries only" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "Never merge or reconcile conflicting statements" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "omit the item instead of guessing" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "Work sentence-by-sentence or claim-span-by-claim-span" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "do one silent second pass over the text" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "anchor it to a short local supporting span" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "Do not collapse combination therapy" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "Keep entity summaries minimal when the source gives only a bare mention" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "null findings, no-difference findings, and contradictory findings" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "Prefer relation-bearing biomedical entities" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert 'Treat modal or hedged language such as "may", "might", "could", "suggests", "potential", or' in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "Keep normalized identity separate from source wording" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT


def test_entity_prompt_requires_neutral_global_summaries_and_explicit_mentions():
    assert "brief general biomedical knowledge" in ENTITY_EXTRACTION_PROMPT
    assert "do not add source-specific efficacy, safety, recommendation, or evidence claims" in ENTITY_EXTRACTION_PROMPT.lower()
    assert "Only extract entities that are explicitly mentioned" in ENTITY_EXTRACTION_PROMPT
    assert "Do not create entities purely from implication" in ENTITY_EXTRACTION_PROMPT
    assert 'Do NOT create vague contextual entities like "duration-short-term"' in ENTITY_EXTRACTION_PROMPT
    assert "Prefer a generic definitional summary" in ENTITY_EXTRACTION_PROMPT
    assert "do not turn a sparse mention into a source-specific use statement" in ENTITY_EXTRACTION_PROMPT.lower()
    assert "Emit each real-world entity only once per extraction batch" in ENTITY_EXTRACTION_PROMPT
    assert "text_span should be the shortest exact mention" in ENTITY_EXTRACTION_PROMPT
    assert "Prefer entities that participate in an explicit relation" in ENTITY_EXTRACTION_PROMPT
    assert "Omit generic document nouns or paper artifacts" in ENTITY_EXTRACTION_PROMPT
    assert 'Do not create intervention-arm wrapper entities like "chemotherapy arm"' in ENTITY_EXTRACTION_PROMPT
    assert "text_span must remain the exact shortest source phrase" in ENTITY_EXTRACTION_PROMPT


def test_relation_prompt_requires_explicit_relations_and_separate_conflicts():
    assert "Extract only relations that are explicitly stated in the text" in (
        RELATION_EXTRACTION_PROMPT
    )
    assert "output separate relations" in RELATION_EXTRACTION_PROMPT
    assert "Do not create a relation from background knowledge" in RELATION_EXTRACTION_PROMPT
    assert "First identify the minimal claim-bearing sentence or local span" in RELATION_EXTRACTION_PROMPT
    assert "text_span should usually be 1-3 sentences" in RELATION_EXTRACTION_PROMPT
    assert "HyphaGraph relations are hyperedges" in RELATION_EXTRACTION_PROMPT
    assert "additional roles in the SAME relation" in RELATION_EXTRACTION_PROMPT
    assert "Every role entity_slug used in a relation must be present" in RELATION_EXTRACTION_PROMPT
    assert "source_mention" in RELATION_EXTRACTION_PROMPT
    assert "shortest exact mention for that participant" in RELATION_EXTRACTION_PROMPT
    assert "assertion_text should be a faithful, source-bounded paraphrase" in RELATION_EXTRACTION_PROMPT
    assert "statement_kind" in RELATION_EXTRACTION_PROMPT
    assert "finding_polarity" in RELATION_EXTRACTION_PROMPT
    assert "study_design" in RELATION_EXTRACTION_PROMPT
    assert "sample_size" in RELATION_EXTRACTION_PROMPT
    assert "Do not create duration or dosage roles from vague qualifiers alone" in RELATION_EXTRACTION_PROMPT
    assert "evidence_context" in RELATION_EXTRACTION_PROMPT
    assert '"entity_slug": "placebo"' in RELATION_EXTRACTION_PROMPT
    assert "dosage" in RELATION_EXTRACTION_PROMPT
    assert "causes MUST include the thing causing the effect as agent" in RELATION_EXTRACTION_PROMPT
    assert "control_group, population, and comparator context NEVER replace a missing core role" in RELATION_EXTRACTION_PROMPT
    assert 'For null efficacy findings such as "did not significantly improve"' in RELATION_EXTRACTION_PROMPT
    assert 'Do NOT use relation_type "other" for ordinary efficacy findings' in RELATION_EXTRACTION_PROMPT
    assert 'Use relation_type "associated_with" for explicit non-causal association' in RELATION_EXTRACTION_PROMPT
    assert 'Do NOT use "associated_with" when a study reports an intervention/exposure' in RELATION_EXTRACTION_PROMPT
    assert 'Use "decreases_risk" for reduced/lower odds or risk' in RELATION_EXTRACTION_PROMPT
    assert "Do NOT materialize baseline characteristics" in RELATION_EXTRACTION_PROMPT
    assert "potentially reflecting lower symptom burden" in RELATION_EXTRACTION_PROMPT
    assert 'Use relation_type "prevalence_in" for source-stated prevalence or incidence findings' in RELATION_EXTRACTION_PROMPT
    assert 'a measured clinical outcome like "overall survival", "blood pressure", or' in RELATION_EXTRACTION_PROMPT
    assert 'Wrong extraction: causes(target=nausea, control_group=placebo)' in RELATION_EXTRACTION_PROMPT
    assert 'When a source reports combination therapy, adjunct therapy, co-administration, or "X with Y"' in RELATION_EXTRACTION_PROMPT
    assert 'do NOT emit a single-agent treats relation for only X or only Y' in RELATION_EXTRACTION_PROMPT
    assert "Correct extraction shape: treats(agent=carboplatin, agent=paclitaxel, target=advanced-ovarian-cancer, control_group=carboplatin)" in RELATION_EXTRACTION_PROMPT
    assert "the finding is about the combination regimen, not carboplatin alone" in RELATION_EXTRACTION_PROMPT
    assert "silent second pass over the text" in RELATION_EXTRACTION_PROMPT
    assert "Keep source wording separate from normalized fields" in RELATION_EXTRACTION_PROMPT
    assert 'prefer evidence_context.statement_kind "hypothesis" or' in RELATION_EXTRACTION_PROMPT
    assert "Recommendation-only or screening-only language should usually NOT become a relation" in RELATION_EXTRACTION_PROMPT


def test_relation_and_batch_prompts_block_invented_role_names():
    for prompt, label in [
        (RELATION_EXTRACTION_PROMPT, "relation"),
        (format_batch_extraction_prompt("text"), "batch"),
    ]:
        assert "comparator_detail" in prompt, f"{label}: must name comparator_detail to block it"
        assert "is NOT a valid role" in prompt, f"{label}: must explicitly block invalid roles"
        assert "control_group" in prompt, f"{label}: control_group must be listed as valid role"
        assert "study_group" in prompt, f"{label}: study_group must be listed as valid role"


def test_entity_linking_prompt_requires_conservative_matching():
    assert 'If the match is uncertain, return "NEW"' in ENTITY_LINKING_PROMPT
    assert "Do not use external knowledge" in ENTITY_LINKING_PROMPT


def test_batch_prompt_carries_global_evidence_first_constraints():
    prompt = format_batch_extraction_prompt("Example source text.")

    assert "Extract only information explicitly supported by the provided text" in prompt
    assert "Work locally: first identify claim-bearing spans" in prompt
    assert "A relation is valid only if you can point to a short local text span" in prompt
    assert "Do not reconcile contradictions or competing findings" in prompt
    assert "Only extract information that is clearly and explicitly stated" in prompt
    assert "do one silent second pass to catch missed claim-bearing spans" in prompt
    assert "HyphaGraph relations are n-ary hyperedges" in prompt
    assert "include those explicitly stated items as additional roles in the SAME relation" in prompt
    assert "Keep study findings separate from background statements, hypotheses, and methodology notes" in prompt
    assert "emit each real-world entity only once per batch" in prompt
    assert "relation text_span should usually be 1-3 sentences" in prompt
    assert "null findings and no-difference findings should still be extracted" in prompt
    assert 'for null efficacy findings such as "did not significantly improve"' in prompt
    assert "assertion_text should be a faithful, source-bounded paraphrase" in prompt
    assert "include evidence_context for every relation" in prompt
    assert "each role should include source_mention" in prompt
    assert "participant count" in prompt
    assert 'Do not create vague duration/dosage/timeframe entities such as "duration-short-term"' in prompt
    assert "do NOT create entities for dosage, duration, timeframe, sample size, or study design metadata" in prompt
    assert "brief general biomedical knowledge is allowed for entity summaries only" in prompt
    assert "keep the summary short, generic, and non-interpretive" in prompt
    assert '"dosage": "500mg twice daily"' in prompt
    assert "placebo" in prompt
    assert '"entity_slug": "dose-60mg-daily"' not in prompt
    assert "Do not flatten combination therapy, adjunct therapy, or co-administration findings into single-agent relations" in prompt
    assert "include every explicitly named active intervention as agent roles in the SAME relation" in prompt
    assert '"entity_slug": "carboplatin", "role_type": "agent"' in prompt
    assert '"entity_slug": "paclitaxel", "role_type": "agent"' in prompt
    assert '"source_mention": "carboplatin"' in prompt
    assert "Prefer relation-bearing biomedical entities" in prompt
    assert "omit generic document nouns or paper artifacts" in prompt
    assert 'do not create intervention-arm wrapper entities like "chemotherapy arm"' in prompt
    assert 'do NOT use relation_type "other" for ordinary efficacy findings or adverse-event findings' in prompt
    assert 'Use relation_type "associated_with" for explicit non-causal association' in prompt
    assert 'Do NOT use "associated_with" for intervention/exposure findings' in prompt
    assert 'Use "decreases_risk" for reduced/lower odds or risk' in prompt
    assert "Do NOT materialize baseline characteristics" in prompt
    assert "potentially reflecting lower symptom burden" in prompt
    assert 'Use relation_type "prevalence_in" for source-stated prevalence or incidence findings' in prompt
    assert "text_span, sample_size_text, and statistical_support should copy or minimally trim the source wording" in prompt
    assert 'prefer statement_kind "hypothesis" or finding_polarity "uncertain"' in prompt
    assert '"relations"' in prompt
    assert "associated_with" in prompt
    assert "prevalence_in" in prompt


def test_batch_gleaning_prompt_requires_append_only_missed_items():
    prompt = format_batch_gleaning_prompt(
        "Example source text.",
        {
            "entities": [{"slug": "aspirin"}],
            "relations": [],
        },
    )

    assert "Return ONLY entities and relations that were genuinely missed" in (
        BATCH_EXTRACTION_GLEANING_PROMPT
    )
    assert "Do NOT rewrite" in BATCH_EXTRACTION_GLEANING_PROMPT
    assert "If nothing important is missing, return empty arrays" in BATCH_EXTRACTION_GLEANING_PROMPT
    assert "Every relation role entity_slug must already exist in the prior extraction" in (
        BATCH_EXTRACTION_GLEANING_PROMPT
    )
    assert '"entities": []' in prompt
    assert '"slug": "aspirin"' in prompt
