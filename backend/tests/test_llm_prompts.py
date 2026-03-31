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


def test_relation_prompt_requires_explicit_relations_and_separate_conflicts():
    assert "Extract only relations that are explicitly stated in the text" in (
        RELATION_EXTRACTION_PROMPT
    )
    assert "output separate relations" in RELATION_EXTRACTION_PROMPT
    assert "Do not create a relation from background knowledge" in RELATION_EXTRACTION_PROMPT


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
