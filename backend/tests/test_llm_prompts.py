from app.llm.prompts import (
    BATCH_EXTRACTION_PROMPT,
    CLAIM_EXTRACTION_PROMPT,
    ENTITY_EXTRACTION_PROMPT,
    ENTITY_LINKING_PROMPT,
    MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
    RELATION_EXTRACTION_PROMPT,
    format_batch_extraction_prompt,
)


def test_system_prompt_forbids_outside_knowledge_and_merging_conflicts():
    assert "Do not add outside medical knowledge" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "Never merge or reconcile conflicting statements" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
    assert "omit the item instead of guessing" in MEDICAL_KNOWLEDGE_SYSTEM_PROMPT


def test_entity_prompt_requires_source_bounded_summaries_and_explicit_mentions():
    assert "Do NOT add background medical facts" in ENTITY_EXTRACTION_PROMPT
    assert "Only extract entities that are explicitly mentioned" in ENTITY_EXTRACTION_PROMPT
    assert "Do not create entities purely from implication" in ENTITY_EXTRACTION_PROMPT
    assert 'Do NOT create vague contextual entities like "duration-short-term"' in ENTITY_EXTRACTION_PROMPT


def test_relation_prompt_requires_explicit_relations_and_separate_conflicts():
    assert "Extract only relations that are explicitly stated in the text" in (
        RELATION_EXTRACTION_PROMPT
    )
    assert "output separate relations" in RELATION_EXTRACTION_PROMPT
    assert "Do not create a relation from background knowledge" in RELATION_EXTRACTION_PROMPT
    assert "HyphaGraph relations are hyperedges" in RELATION_EXTRACTION_PROMPT
    assert "additional roles in the SAME relation" in RELATION_EXTRACTION_PROMPT
    assert "Every role entity_slug used in a relation must be present" in RELATION_EXTRACTION_PROMPT
    assert "statement_kind" in RELATION_EXTRACTION_PROMPT
    assert "finding_polarity" in RELATION_EXTRACTION_PROMPT
    assert "study_design" in RELATION_EXTRACTION_PROMPT
    assert "sample_size" in RELATION_EXTRACTION_PROMPT
    assert "Do not create duration or dosage roles from vague qualifiers alone" in RELATION_EXTRACTION_PROMPT
    assert "dose-325-650mg" in RELATION_EXTRACTION_PROMPT
    assert '"entity_slug": "325-650mg"' not in RELATION_EXTRACTION_PROMPT


def test_claim_prompt_requires_faithful_paraphrase_and_conservative_evidence():
    assert "faithful source-bounded paraphrase" in CLAIM_EXTRACTION_PROMPT
    assert "Do not collapse multiple competing claims" in CLAIM_EXTRACTION_PROMPT
    assert "Assign evidence_strength conservatively" in CLAIM_EXTRACTION_PROMPT
    assert "Only extract claims that are explicitly stated" in CLAIM_EXTRACTION_PROMPT


def test_entity_linking_prompt_requires_conservative_matching():
    assert 'If the match is uncertain, return "NEW"' in ENTITY_LINKING_PROMPT
    assert "Do not use external knowledge" in ENTITY_LINKING_PROMPT


def test_batch_prompt_carries_global_evidence_first_constraints():
    prompt = format_batch_extraction_prompt("Example source text.")

    assert "Extract only information explicitly supported by the provided text" in prompt
    assert "Do not reconcile contradictions or competing findings" in prompt
    assert "claim_text must remain a faithful source-bounded paraphrase" in prompt
    assert "Only extract information that is clearly and explicitly stated" in prompt
    assert "HyphaGraph relations are n-ary hyperedges" in prompt
    assert "include those explicitly stated items as additional roles in the SAME relation" in prompt
    assert "Keep study findings separate from background statements, hypotheses, and methodology notes" in prompt
    assert "include study_context for every relation" in prompt
    assert "participant count" in prompt
    assert 'Do not create vague duration/dosage/timeframe entities such as "duration-short-term"' in prompt
    assert "contextual role fillers" in prompt
    assert "dose-60mg-daily" in prompt
    assert "placebo" in prompt
    assert '"entity_slug": "60mg-daily"' not in prompt
