import pytest

from app.services.batch_extraction_orchestrator import BatchExtractionOrchestrator


class FakeLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[str] = []

    async def generate_json(
        self,
        prompt,
        system_prompt=None,
        temperature=None,
        max_tokens=2000,
        **kwargs,
    ):
        self.calls.append(prompt)
        if not self._responses:
            raise AssertionError("generate_json called more times than expected")
        return self._responses.pop(0)


def _entity(slug: str, *, summary: str | None = None, category: str = "drug") -> dict[str, str]:
    return {
        "slug": slug,
        "summary": summary or f"{slug} summary text",
        "category": category,
        "confidence": "high",
        "text_span": slug.replace("-", " "),
    }


def _relation(
    *,
    target_slug: str,
    text_span: str,
    confidence: str = "medium",
    notes: str | None = None,
) -> dict[str, object]:
    return {
        "relation_type": "treats",
        "roles": [
            {"entity_slug": "ssris", "role_type": "agent"},
            {"entity_slug": target_slug, "role_type": "target"},
            {"entity_slug": "placebo", "role_type": "control_group"},
        ],
        "confidence": confidence,
        "text_span": text_span,
        "notes": notes,
        "evidence_context": {
            "statement_kind": "finding",
            "finding_polarity": "supports",
            "study_design": "meta_analysis",
            "assertion_text": text_span,
        },
    }


@pytest.mark.asyncio
async def test_gleaning_pass_appends_missed_entities_and_relations() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=1,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    _entity("ssris"),
                    _entity("pain", category="outcome"),
                    _entity("placebo", category="other"),
                ],
                "relations": [
                    _relation(
                        target_slug="pain",
                        text_span="SSRIs reduced pain compared with placebo.",
                    )
                ],
            },
            {
                "entities": [
                    _entity("quality-of-life", category="outcome"),
                ],
                "relations": [
                    _relation(
                        target_slug="quality-of-life",
                        text_span="SSRIs improved quality of life compared with placebo.",
                    )
                ],
            },
        ]
    )

    entities, relations = await orchestrator.extract_batch(
        "SSRIs reduced pain and improved quality of life compared with placebo."
    )

    assert {entity.slug for entity in entities} == {
        "ssris",
        "pain",
        "placebo",
        "quality-of-life",
    }
    assert len(relations) == 2
    assert {relation.roles[1].entity_slug for relation in relations} == {
        "pain",
        "quality-of-life",
    }
    assert len(orchestrator.llm.calls) == 2


@pytest.mark.asyncio
async def test_gleaning_stops_after_duplicate_only_pass() -> None:
    duplicate_batch = {
        "entities": [
            _entity("ssris"),
            _entity("pain", category="outcome"),
            _entity("placebo", category="other"),
        ],
        "relations": [
            _relation(
                target_slug="pain",
                text_span="SSRIs reduced pain compared with placebo.",
            )
        ],
    }
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=2,
    )
    orchestrator.llm = FakeLLM([duplicate_batch, duplicate_batch])

    entities, relations = await orchestrator.extract_batch(
        "SSRIs reduced pain compared with placebo."
    )

    assert len(entities) == 3
    assert len(relations) == 1
    assert len(orchestrator.llm.calls) == 2


@pytest.mark.asyncio
async def test_extract_batch_normalizes_statement_kind_aliases_before_validation() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    _entity("probiotics", category="treatment"),
                    _entity("fibromyalgia", category="disease"),
                    _entity("anxiety", category="outcome"),
                ],
                "relations": [
                    {
                        "relation_type": "treats",
                        "roles": [
                            {"entity_slug": "probiotics", "role_type": "agent"},
                            {"entity_slug": "anxiety", "role_type": "target"},
                            {"entity_slug": "fibromyalgia", "role_type": "condition"},
                        ],
                        "confidence": "medium",
                        "text_span": "Conclusions were mixed about probiotic effects on anxiety in fibromyalgia.",
                        "evidence_context": {
                            "statement_kind": "conclusion",
                            "finding_polarity": "mixed",
                        },
                    }
                ],
            }
        ]
    )

    _, relations = await orchestrator.extract_batch(
        "Conclusions were mixed about probiotic effects on anxiety in fibromyalgia."
    )

    assert len(relations) == 1
    assert relations[0].evidence_context is not None
    assert relations[0].evidence_context.statement_kind == "finding"


@pytest.mark.asyncio
async def test_gleaning_keeps_original_items_when_follow_up_repeats_with_rewrites() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=1,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    _entity("ssris", summary="Original SSRI summary text."),
                    _entity("pain", category="outcome"),
                    _entity("placebo", category="other"),
                ],
                "relations": [
                    _relation(
                        target_slug="pain",
                        text_span="SSRIs reduced pain compared with placebo.",
                        confidence="medium",
                        notes="Original note",
                    )
                ],
            },
            {
                "entities": [
                    _entity("ssris", summary="Rewritten summary that should be ignored."),
                ],
                "relations": [
                    _relation(
                        target_slug="pain",
                        text_span="SSRIs reduced pain compared with placebo.",
                        confidence="high",
                        notes="Rewritten note that should be ignored",
                    )
                ],
            },
        ]
    )

    entities, relations = await orchestrator.extract_batch(
        "SSRIs reduced pain compared with placebo."
    )

    assert len(entities) == 3
    assert next(entity for entity in entities if entity.slug == "ssris").summary == (
        "Original SSRI summary text."
    )
    assert len(relations) == 1
    assert relations[0].confidence == "medium"
    assert relations[0].notes == "Original note"


@pytest.mark.asyncio
async def test_long_text_is_split_across_multiple_chunks_and_merged() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
        max_chunk_chars=60,
        chunk_overlap_chars=0,
        max_chunks=4,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    _entity("ssris"),
                    _entity("pain", category="outcome"),
                    _entity("placebo", category="other"),
                ],
                "relations": [
                    _relation(
                        target_slug="pain",
                        text_span="SSRIs reduced pain compared with placebo.",
                    )
                ],
            },
            {
                "entities": [
                    _entity("quality-of-life", category="outcome"),
                ],
                "relations": [
                    _relation(
                        target_slug="quality-of-life",
                        text_span="SSRIs improved quality of life compared with placebo.",
                    )
                ],
            },
        ]
    )

    text = (
        "SSRIs reduced pain compared with placebo. "
        "SSRIs improved quality of life compared with placebo."
    )
    entities, relations = await orchestrator.extract_batch(text)

    assert len(orchestrator.llm.calls) == 2
    assert {entity.slug for entity in entities} == {
        "ssris",
        "pain",
        "placebo",
        "quality-of-life",
    }
    assert {relation.roles[1].entity_slug for relation in relations} == {
        "pain",
        "quality-of-life",
    }


@pytest.mark.asyncio
async def test_chunk_overlap_duplicate_results_are_deduped() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
        max_chunk_chars=55,
        chunk_overlap_chars=20,
        max_chunks=4,
    )
    duplicate_batch = {
        "entities": [
            _entity("ssris"),
            _entity("pain", category="outcome"),
            _entity("placebo", category="other"),
        ],
        "relations": [
            _relation(
                target_slug="pain",
                text_span="SSRIs reduced pain compared with placebo.",
            )
        ],
    }
    orchestrator.llm = FakeLLM([duplicate_batch, duplicate_batch, duplicate_batch])

    text = (
        "SSRIs reduced pain compared with placebo. "
        "Additional filler keeps the relation inside overlapping chunks."
    )
    entities, relations = await orchestrator.extract_batch(text)

    assert len(orchestrator.llm.calls) >= 2
    assert len(entities) == 3
    assert len(relations) == 1


@pytest.mark.asyncio
async def test_chunking_keeps_tail_coverage_when_max_chunks_is_reached() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
        max_chunk_chars=40,
        chunk_overlap_chars=0,
        max_chunks=2,
    )
    orchestrator.llm = FakeLLM(
        [
            {"entities": [], "relations": []},
            {"entities": [], "relations": []},
        ]
    )

    text = (
        "Alpha sentence about background context. "
        "Beta sentence about methods. "
        "Tail marker sentence about the final finding."
    )
    await orchestrator.extract_batch(text)

    assert len(orchestrator.llm.calls) == 2
    assert "Tail marker sentence about the final finding." in orchestrator.llm.calls[-1]


@pytest.mark.asyncio
async def test_semantic_normalizer_upgrades_other_null_efficacy_relation() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    _entity("ssris"),
                    _entity("depression", category="outcome"),
                    _entity("fibromyalgia", category="disease"),
                    _entity("acupuncture", category="treatment"),
                    _entity("aerobic-exercise", category="treatment"),
                ],
                "relations": [
                    {
                        "relation_type": "other",
                        "roles": [
                            {"entity_slug": "ssris", "role_type": "agent", "source_mention": "SSRIs"},
                            {"entity_slug": "depression", "role_type": "outcome", "source_mention": "depression"},
                            {"entity_slug": "fibromyalgia", "role_type": "condition", "source_mention": "fibromyalgia"},
                            {"entity_slug": "acupuncture", "role_type": "comparator", "source_mention": "acupuncture"},
                            {"entity_slug": "aerobic-exercise", "role_type": "comparator", "source_mention": "aerobic exercise"},
                        ],
                        "confidence": "high",
                        "text_span": "Compared with acupuncture and aerobic exercise, SSRIs did not significantly improve depression in fibromyalgia.",
                        "evidence_context": {
                            "statement_kind": "finding",
                            "finding_polarity": "contradicts",
                            "assertion_text": "SSRIs did not significantly improve depression compared with acupuncture and aerobic exercise.",
                        },
                    }
                ],
            }
        ]
    )

    _, relations = await orchestrator.extract_batch(
        "Compared with acupuncture and aerobic exercise, SSRIs did not significantly improve depression in fibromyalgia."
    )

    assert len(relations) == 1
    relation = relations[0]
    assert relation.relation_type == "treats"
    assert [role.role_type for role in relation.roles].count("target") == 1
    assert {role.entity_slug for role in relation.roles if role.role_type == "control_group"} == {
        "acupuncture",
        "aerobic-exercise",
    }
    assert relation.evidence_context is not None
    assert relation.evidence_context.finding_polarity == "neutral"


@pytest.mark.asyncio
async def test_semantic_normalizer_upgrades_other_association_relation() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    _entity("dysautonomia", category="disease"),
                    _entity("chronic-musculoskeletal-pain", category="disease"),
                ],
                "relations": [
                    {
                        "relation_type": "other",
                        "roles": [
                            {"entity_slug": "dysautonomia", "role_type": "target", "source_mention": "dysautonomia"},
                            {
                                "entity_slug": "chronic-musculoskeletal-pain",
                                "role_type": "condition",
                                "source_mention": "chronic musculoskeletal pain",
                            },
                        ],
                        "confidence": "high",
                        "text_span": "The high prevalence of dysautonomia in patients with chronic musculoskeletal painful conditions illustrates the association between dysautonomia and chronic pain.",
                        "evidence_context": {
                            "statement_kind": "finding",
                            "finding_polarity": "supports",
                        },
                    }
                ],
            }
        ]
    )

    _, relations = await orchestrator.extract_batch(
        "The high prevalence of dysautonomia in patients with chronic musculoskeletal painful conditions illustrates the association between dysautonomia and chronic pain."
    )

    assert len(relations) == 1
    assert relations[0].relation_type == "associated_with"


@pytest.mark.asyncio
async def test_semantic_normalizer_upgrades_other_prevalence_relation() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    _entity("dysautonomia", category="disease"),
                    _entity(
                        "people-with-chronic-musculoskeletal-pain",
                        category="population",
                    ),
                ],
                "relations": [
                    {
                        "relation_type": "other",
                        "roles": [
                            {"entity_slug": "dysautonomia", "role_type": "target", "source_mention": "dysautonomia"},
                            {
                                "entity_slug": "people-with-chronic-musculoskeletal-pain",
                                "role_type": "population",
                                "source_mention": "people with chronic musculoskeletal pain",
                            },
                        ],
                        "confidence": "high",
                        "text_span": "In people with chronic musculoskeletal pain, the pooled prevalence of dysautonomia was 64%.",
                        "evidence_context": {
                            "statement_kind": "finding",
                            "finding_polarity": "supports",
                        },
                    }
                ],
            }
        ]
    )

    _, relations = await orchestrator.extract_batch(
        "In people with chronic musculoskeletal pain, the pooled prevalence of dysautonomia was 64%."
    )

    assert len(relations) == 1
    assert relations[0].relation_type == "prevalence_in"


@pytest.mark.asyncio
async def test_semantic_normalizer_drops_ambiguous_other_relation_without_focal_target() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    _entity("pain", category="symptom"),
                    _entity("fatigue", category="symptom"),
                    _entity("dizziness", category="symptom"),
                    _entity("autonomic-dysfunction", category="disease"),
                ],
                "relations": [
                    {
                        "relation_type": "other",
                        "roles": [
                            {"entity_slug": "pain", "role_type": "agent", "source_mention": "pain"},
                            {"entity_slug": "fatigue", "role_type": "agent", "source_mention": "fatigue"},
                            {"entity_slug": "dizziness", "role_type": "agent", "source_mention": "dizziness"},
                            {
                                "entity_slug": "autonomic-dysfunction",
                                "role_type": "condition",
                                "source_mention": "autonomic dysfunction",
                            },
                        ],
                        "confidence": "medium",
                        "text_span": "Several chronic musculoskeletal disorders are characterized by pain, fatigue, dizziness and other associated symptoms that may be related to autonomic dysfunction.",
                        "evidence_context": {
                            "statement_kind": "background",
                            "finding_polarity": "uncertain",
                        },
                    }
                ],
            }
        ]
    )

    _, relations = await orchestrator.extract_batch(
        "Several chronic musculoskeletal disorders are characterized by pain, fatigue, dizziness and other associated symptoms that may be related to autonomic dysfunction."
    )

    assert relations == []


@pytest.mark.asyncio
async def test_incomplete_associated_with_relation_is_downgraded_then_reclassified_to_treats() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    _entity("probiotics", category="treatment"),
                    _entity("sleep", category="outcome"),
                ],
                "relations": [
                    {
                        "relation_type": "associated_with",
                        "roles": [
                            {"entity_slug": "probiotics", "role_type": "agent", "source_mention": "probiotics"},
                            {"entity_slug": "sleep", "role_type": "target", "source_mention": "sleep"},
                        ],
                        "confidence": "medium",
                        "text_span": "Probiotics were associated with improvements in sleep.",
                        "evidence_context": {
                            "statement_kind": "finding",
                            "finding_polarity": "supports",
                        },
                    }
                ],
            }
        ]
    )

    _, relations = await orchestrator.extract_batch(
        "Probiotics were associated with improvements in sleep."
    )

    assert len(relations) == 1
    assert relations[0].relation_type == "treats"


@pytest.mark.asyncio
async def test_semantic_normalizer_rewrites_intervention_group_entity_slug_and_role_reference() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    {
                        **_entity("ssri-groups"),
                        "text_span": "SSRI groups",
                    },
                    _entity("adverse-events", category="other"),
                    _entity("placebo", category="other"),
                ],
                "relations": [
                    {
                        "relation_type": "causes",
                        "roles": [
                            {"entity_slug": "ssri-groups", "role_type": "agent", "source_mention": "SSRI groups"},
                            {"entity_slug": "adverse-events", "role_type": "target", "source_mention": "adverse events"},
                            {"entity_slug": "placebo", "role_type": "control_group", "source_mention": "placebo"},
                        ],
                        "confidence": "high",
                        "text_span": "Compared with placebo, SSRI groups reported more adverse events.",
                        "evidence_context": {
                            "statement_kind": "finding",
                            "finding_polarity": "supports",
                            "assertion_text": "SSRI groups reported more adverse events than placebo.",
                        },
                    }
                ],
            }
        ]
    )

    entities, relations = await orchestrator.extract_batch(
        "Compared with placebo, SSRI groups reported more adverse events."
    )

    assert {entity.slug for entity in entities} == {"ssris", "adverse-events", "placebo"}
    assert entities[0].text_span == "SSRI"
    assert relations[0].roles[0].entity_slug == "ssris"


@pytest.mark.asyncio
async def test_semantic_normalizer_pluralizes_agent_slug_when_relation_span_uses_group_wrapper() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    {
                        **_entity("ssri"),
                        "text_span": "SSRI",
                    },
                    _entity("adverse-events", category="other"),
                    _entity("placebo", category="other"),
                ],
                "relations": [
                    {
                        "relation_type": "causes",
                        "roles": [
                            {"entity_slug": "ssri", "role_type": "agent", "source_mention": "SSRI"},
                            {"entity_slug": "adverse-events", "role_type": "target", "source_mention": "adverse events"},
                            {"entity_slug": "placebo", "role_type": "control_group", "source_mention": "placebo"},
                        ],
                        "confidence": "high",
                        "text_span": "Compared with placebo, SSRI groups reported more adverse events.",
                        "evidence_context": {
                            "statement_kind": "finding",
                            "finding_polarity": "supports",
                            "assertion_text": "SSRI groups reported more adverse events than placebo.",
                        },
                    }
                ],
            }
        ]
    )

    entities, relations = await orchestrator.extract_batch(
        "Compared with placebo, SSRI groups reported more adverse events."
    )

    assert {entity.slug for entity in entities} == {"ssris", "adverse-events", "placebo"}
    assert relations[0].roles[0].entity_slug == "ssris"


@pytest.mark.asyncio
async def test_semantic_normalizer_upgrades_other_adverse_event_relation_to_causes() -> None:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=False,
        max_gleaning_passes=0,
    )
    orchestrator.llm = FakeLLM(
        [
            {
                "entities": [
                    _entity("ssris"),
                    _entity("adverse-events", category="other"),
                    _entity("placebo", category="other"),
                ],
                "relations": [
                    {
                        "relation_type": "other",
                        "roles": [
                            {"entity_slug": "ssris", "role_type": "agent", "source_mention": "SSRIs"},
                            {"entity_slug": "adverse-events", "role_type": "outcome", "source_mention": "adverse events"},
                            {"entity_slug": "placebo", "role_type": "control_group", "source_mention": "placebo"},
                        ],
                        "confidence": "high",
                        "text_span": "Compared with placebo, SSRIs reported more adverse events.",
                        "evidence_context": {
                            "statement_kind": "finding",
                            "finding_polarity": "supports",
                            "assertion_text": "SSRIs were associated with more adverse events than placebo.",
                        },
                    }
                ],
            }
        ]
    )

    _, relations = await orchestrator.extract_batch(
        "Compared with placebo, SSRIs reported more adverse events."
    )

    assert relations[0].relation_type == "causes"
    assert [role.role_type for role in relations[0].roles].count("target") == 1
