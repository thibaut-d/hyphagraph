"""
Conservative semantic normalization for automatic extraction output.

The LLM sometimes emits relation or entity shapes that are locally justified by
the source span but semantically off by one step: `other` instead of `treats`,
`contradicts` instead of `neutral` for null efficacy findings, or arm/group
nouns instead of the underlying intervention entity. This module repairs only a
small, auditable set of those cases before validation and staging.
"""

from __future__ import annotations

import re

from app.llm.schemas import (
    BatchExtractionResponse,
    ExtractedEntity,
    ExtractedRelation,
    ExtractedRelationEvidenceContext,
    ExtractedRole,
)

_GROUP_SUFFIX_PATTERN = re.compile(r"\s+(group|groups|arm|arms)\s*$", re.IGNORECASE)
_PLURAL_GROUP_WRAPPER_PATTERN = re.compile(r"\s+(groups|arms)\s*$", re.IGNORECASE)
_ALL_CAPS_ACRONYM_PATTERN = re.compile(r"^[A-Z0-9-]{2,10}$")
_NON_SLUG_CHARS_PATTERN = re.compile(r"[^a-z0-9]+")

_NULL_EFFECT_PATTERN = re.compile(
    r"\b("
    r"did not significantly|"
    r"no significant (difference|benefit|effect|improvement|advantage|reduction|increase)|"
    r"not significantly|"
    r"non[- ]significant|"
    r"similar to|"
    r"no clear advantage|"
    r"showed no difference|"
    r"no statistically significant"
    r")\b",
    re.IGNORECASE,
)
_TREATS_CUE_PATTERN = re.compile(
    r"\b("
    r"reduced|reduction|improved|improvement|improves|effective|efficacy|benefit|"
    r"beneficial|relief|response|responded|ameliorat|recovery|symptom improvement|"
    r"quality of life|did not significantly|no significant"
    r")\b",
    re.IGNORECASE,
)
_CAUSES_CUE_PATTERN = re.compile(
    r"\b("
    r"adverse event|adverse events|side effect|side effects|dropout|dropout rates|"
    r"complaint|complaints|caused|causes|reported more|reported fewer|dry mouth|"
    r"headache|headaches|nausea|sedation|somnolence|sexual dysfunction|"
    r"gastrointestinal"
    r")\b",
    re.IGNORECASE,
)
_ASSOCIATION_CUE_PATTERN = re.compile(
    r"\b("
    r"associated with|"
    r"association between|"
    r"correlated with|"
    r"correlation between|"
    r"linked to|"
    r"related to|"
    r"comorbid with|"
    r"co[- ]occurs? with|"
    r"illustrates the association between"
    r")\b",
    re.IGNORECASE,
)
_PREVALENCE_CUE_PATTERN = re.compile(
    r"\b("
    r"prevalence|"
    r"pooled prevalence|"
    r"incidence|"
    r"prevalent in|"
    r"present in"
    r")\b",
    re.IGNORECASE,
)
_RECOMMENDATION_CUE_PATTERN = re.compile(
    r"\b("
    r"screening .* warranted|"
    r"regular screening|"
    r"recommended|"
    r"should be screened|"
    r"should consider|"
    r"is warranted"
    r")\b",
    re.IGNORECASE,
)
_DECREASED_RISK_CUE_PATTERN = re.compile(
    r"\b("
    r"reduced odds|reduced risk|lower odds|lower risk|decreased odds|decreased risk|"
    r"reduction in|significantly reduced|less likely|fewer"
    r")\b",
    re.IGNORECASE,
)
_INCREASED_RISK_CUE_PATTERN = re.compile(
    r"\b("
    r"increased odds|increased risk|higher odds|higher risk|elevated odds|elevated risk|"
    r"increase in|significantly increased|more likely|more frequent"
    r")\b",
    re.IGNORECASE,
)
_BASELINE_COVARIATE_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"baseline characteristics|at baseline|after propensity score matching|"
    r"propensity score matching|well matched|cohort than|cohort compared with|"
    r"remained higher|remained lower"
    r")\b",
    re.IGNORECASE,
)
_COVARIATE_OUTCOME_PATTERN = re.compile(
    r"\b("
    r"bmi|body mass index|haemoglobin a1c|hemoglobin a1c|hba1c|"
    r"age|sex|obesity|diabetes|comorbidit"
    r")\b",
    re.IGNORECASE,
)
_SPECULATIVE_SUMMARY_PATTERN = re.compile(
    r"\b("
    r"potentially reflecting|may reflect|might reflect|could reflect|suggesting lower|"
    r"suggests lower"
    r")\b",
    re.IGNORECASE,
)


class ExtractionSemanticNormalizer:
    """Normalize narrow, benchmark-driven extraction failure modes."""

    def normalize_batch_response(
        self,
        response: BatchExtractionResponse,
    ) -> BatchExtractionResponse:
        normalized_entities, entity_slug_aliases = self._normalize_entities(response.entities)
        relation_entity_aliases = self._derive_relation_entity_aliases(
            response.relations,
            entity_slug_aliases=entity_slug_aliases,
        )
        if relation_entity_aliases:
            entity_slug_aliases.update(relation_entity_aliases)
            normalized_entities = self._apply_entity_slug_aliases(
                normalized_entities,
                relation_entity_aliases,
            )
        normalized_relations = self._normalize_relations(
            response.relations,
            entity_slug_aliases=entity_slug_aliases,
            entities=normalized_entities,
        )
        return BatchExtractionResponse(
            entities=normalized_entities,
            relations=normalized_relations,
        )

    def _normalize_entities(
        self,
        entities: list[ExtractedEntity],
    ) -> tuple[list[ExtractedEntity], dict[str, str]]:
        normalized_entities: list[ExtractedEntity] = []
        entity_slug_aliases: dict[str, str] = {}
        seen_slugs: set[str] = set()

        for entity in entities:
            normalized_entity = self._normalize_entity(entity)
            entity_slug_aliases[entity.slug] = normalized_entity.slug
            if normalized_entity.slug in seen_slugs:
                continue
            normalized_entities.append(normalized_entity)
            seen_slugs.add(normalized_entity.slug)

        return normalized_entities, entity_slug_aliases

    def _apply_entity_slug_aliases(
        self,
        entities: list[ExtractedEntity],
        entity_slug_aliases: dict[str, str],
    ) -> list[ExtractedEntity]:
        aliased_entities: list[ExtractedEntity] = []
        seen_slugs: set[str] = set()

        for entity in entities:
            aliased_slug = entity_slug_aliases.get(entity.slug, entity.slug)
            aliased_entity = entity if aliased_slug == entity.slug else entity.model_copy(
                update={"slug": aliased_slug}
            )
            if aliased_entity.slug in seen_slugs:
                continue
            aliased_entities.append(aliased_entity)
            seen_slugs.add(aliased_entity.slug)

        return aliased_entities

    def _normalize_entity(self, entity: ExtractedEntity) -> ExtractedEntity:
        if entity.category not in {"drug", "treatment", "other"}:
            return entity

        text_span = entity.text_span.strip()
        match = _GROUP_SUFFIX_PATTERN.search(text_span)
        if not match:
            return entity

        base_mention = _GROUP_SUFFIX_PATTERN.sub("", text_span).strip(" -")
        if not base_mention:
            return entity

        normalized_slug = self._slugify_base_mention(
            base_mention,
            plural_wrapper=bool(_PLURAL_GROUP_WRAPPER_PATTERN.search(text_span)),
        )
        if not normalized_slug or normalized_slug == entity.slug:
            return entity

        return entity.model_copy(
            update={
                "slug": normalized_slug,
                "text_span": base_mention,
            }
        )

    def _normalize_relations(
        self,
        relations: list[ExtractedRelation],
        *,
        entity_slug_aliases: dict[str, str],
        entities: list[ExtractedEntity],
    ) -> list[ExtractedRelation]:
        entity_lookup = {entity.slug: entity for entity in entities}
        normalized_relations: list[ExtractedRelation] = []
        for relation in relations:
            normalized_relation = self._normalize_relation(
                relation,
                entity_slug_aliases=entity_slug_aliases,
                entity_lookup=entity_lookup,
            )
            if normalized_relation is not None:
                normalized_relations.append(normalized_relation)
        return normalized_relations

    def _derive_relation_entity_aliases(
        self,
        relations: list[ExtractedRelation],
        *,
        entity_slug_aliases: dict[str, str],
    ) -> dict[str, str]:
        derived_aliases: dict[str, str] = {}

        for relation in relations:
            for role in relation.roles:
                if role.role_type != "agent" or not role.source_mention:
                    continue
                normalized_slug = self._derive_group_wrapped_agent_slug(
                    role.source_mention,
                    relation.text_span,
                )
                if not normalized_slug:
                    continue

                current_slug = entity_slug_aliases.get(role.entity_slug, role.entity_slug)
                if normalized_slug != current_slug:
                    derived_aliases[current_slug] = normalized_slug

        return derived_aliases

    def _derive_group_wrapped_agent_slug(
        self,
        source_mention: str,
        relation_text_span: str,
    ) -> str | None:
        stripped_source_mention = source_mention.strip()
        if not stripped_source_mention:
            return None

        direct_group_wrapper = _GROUP_SUFFIX_PATTERN.search(stripped_source_mention)
        if direct_group_wrapper:
            base_mention = _GROUP_SUFFIX_PATTERN.sub("", stripped_source_mention).strip(" -")
            return self._slugify_base_mention(
                base_mention,
                plural_wrapper=bool(_PLURAL_GROUP_WRAPPER_PATTERN.search(stripped_source_mention)),
            )

        wrapped_in_relation = re.search(
            rf"\b{re.escape(stripped_source_mention)}\s+(groups|arms)\b",
            relation_text_span,
            re.IGNORECASE,
        )
        if wrapped_in_relation:
            return self._slugify_base_mention(
                stripped_source_mention,
                plural_wrapper=True,
            )

        return None

    def _normalize_relation(
        self,
        relation: ExtractedRelation,
        *,
        entity_slug_aliases: dict[str, str],
        entity_lookup: dict[str, ExtractedEntity],
    ) -> ExtractedRelation | None:
        normalized_roles = [
            role.model_copy(
                update={
                    "entity_slug": entity_slug_aliases.get(role.entity_slug, role.entity_slug),
                    "role_type": self._normalize_role_type(role.role_type),
                }
            )
            for role in relation.roles
        ]

        normalized_relation_type = relation.relation_type
        if self._should_drop_context_only_relation(relation):
            return None
        if normalized_relation_type == "other":
            normalized_relation_type = self._infer_relation_type(
                relation,
                roles=normalized_roles,
                entity_lookup=entity_lookup,
            )
        if normalized_relation_type == "other" and self._should_drop_ambiguous_other_relation(
            relation,
            roles=normalized_roles,
        ):
            return None

        normalized_roles = self._normalize_core_target_role(
            normalized_roles,
            relation_type=normalized_relation_type,
        )

        normalized_evidence_context = self._normalize_evidence_context(
            relation.evidence_context,
            relation_type=normalized_relation_type,
            text_span=relation.text_span,
        )

        return relation.model_copy(
            update={
                "relation_type": normalized_relation_type,
                "roles": normalized_roles,
                "evidence_context": normalized_evidence_context,
            }
        )

    def _normalize_role_type(self, role_type: str) -> str:
        if role_type == "comparator":
            return "control_group"
        return role_type

    def _infer_relation_type(
        self,
        relation: ExtractedRelation,
        *,
        roles: list[ExtractedRole],
        entity_lookup: dict[str, ExtractedEntity],
    ) -> str:
        role_types = {role.role_type for role in roles}
        text_span = relation.text_span
        if "agent" not in role_types or not role_types.intersection({"target", "outcome"}):
            if self._looks_like_associated_with(text_span, roles=roles):
                return "associated_with"
            if self._looks_like_prevalence_in(text_span, roles=roles):
                return "prevalence_in"
            return relation.relation_type

        if self._looks_like_decreases_risk(text_span):
            return "decreases_risk"
        if self._looks_like_increases_risk(text_span):
            return "increases_risk"
        if self._looks_like_causes(text_span, roles=roles, entity_lookup=entity_lookup):
            return "causes"
        if self._looks_like_treats(text_span, roles=roles, entity_lookup=entity_lookup):
            return "treats"
        if self._looks_like_associated_with(text_span, roles=roles):
            return "associated_with"
        if self._looks_like_prevalence_in(text_span, roles=roles):
            return "prevalence_in"
        return relation.relation_type

    def _looks_like_decreases_risk(self, text_span: str) -> bool:
        return bool(_DECREASED_RISK_CUE_PATTERN.search(text_span))

    def _looks_like_increases_risk(self, text_span: str) -> bool:
        return bool(_INCREASED_RISK_CUE_PATTERN.search(text_span))

    def _looks_like_prevalence_in(
        self,
        text_span: str,
        *,
        roles: list[ExtractedRole],
    ) -> bool:
        role_types = {role.role_type for role in roles}
        if "target" not in role_types:
            return False
        if not role_types.intersection({"population", "condition", "study_group", "control_group"}):
            return False
        return bool(_PREVALENCE_CUE_PATTERN.search(text_span))

    def _looks_like_associated_with(
        self,
        text_span: str,
        *,
        roles: list[ExtractedRole],
    ) -> bool:
        role_types = {role.role_type for role in roles}
        if "target" not in role_types:
            return False
        if not role_types.intersection({"condition", "population", "study_group", "control_group"}):
            return False
        return bool(_ASSOCIATION_CUE_PATTERN.search(text_span))

    def _looks_like_treats(
        self,
        text_span: str,
        *,
        roles: list[ExtractedRole],
        entity_lookup: dict[str, ExtractedEntity],
    ) -> bool:
        role_types = {role.role_type for role in roles}
        if "agent" not in role_types or not role_types.intersection({"target", "outcome"}):
            return False
        if _CAUSES_CUE_PATTERN.search(text_span):
            return False
        if _TREATS_CUE_PATTERN.search(text_span):
            return True

        target_like_categories = {
            entity_lookup.get(role.entity_slug).category
            for role in roles
            if role.role_type in {"target", "outcome"} and entity_lookup.get(role.entity_slug)
        }
        return bool(target_like_categories.intersection({"disease", "symptom", "outcome"}))

    def _looks_like_causes(
        self,
        text_span: str,
        *,
        roles: list[ExtractedRole],
        entity_lookup: dict[str, ExtractedEntity],
    ) -> bool:
        if not _CAUSES_CUE_PATTERN.search(text_span):
            return False

        target_like_categories = {
            entity_lookup.get(role.entity_slug).category
            for role in roles
            if role.role_type in {"target", "outcome"} and entity_lookup.get(role.entity_slug)
        }
        return bool(target_like_categories.intersection({"symptom", "outcome", "other"}))

    def _normalize_core_target_role(
        self,
        roles: list[ExtractedRole],
        *,
        relation_type: str,
    ) -> list[ExtractedRole]:
        if relation_type not in {"treats", "causes", "prevents"}:
            return roles

        has_target = any(role.role_type == "target" for role in roles)
        outcome_roles = [role for role in roles if role.role_type == "outcome"]
        if has_target or len(outcome_roles) != 1:
            return roles

        promoted_role = outcome_roles[0].model_copy(update={"role_type": "target"})
        normalized_roles: list[ExtractedRole] = []
        for role in roles:
            if role is outcome_roles[0]:
                normalized_roles.append(promoted_role)
            else:
                normalized_roles.append(role)
        return normalized_roles

    def _normalize_evidence_context(
        self,
        evidence_context: ExtractedRelationEvidenceContext | None,
        *,
        relation_type: str,
        text_span: str,
    ) -> ExtractedRelationEvidenceContext | None:
        if evidence_context is None:
            return None
        if evidence_context.statement_kind != "finding":
            return evidence_context
        if evidence_context.finding_polarity != "contradicts":
            return evidence_context
        if relation_type not in {"treats", "prevents", "decreases_risk", "increases_risk", "other"}:
            return evidence_context
        if not _NULL_EFFECT_PATTERN.search(text_span):
            return evidence_context

        return evidence_context.model_copy(update={"finding_polarity": "neutral"})

    def _should_drop_ambiguous_other_relation(
        self,
        relation: ExtractedRelation,
        *,
        roles: list[ExtractedRole],
    ) -> bool:
        role_types = {role.role_type for role in roles}
        if _RECOMMENDATION_CUE_PATTERN.search(relation.text_span):
            return True
        if not role_types.intersection({"target", "outcome"}):
            return True
        return len({role.entity_slug for role in roles}) < 2

    def _should_drop_context_only_relation(self, relation: ExtractedRelation) -> bool:
        text_span = relation.text_span
        if (
            _BASELINE_COVARIATE_CONTEXT_PATTERN.search(text_span)
            and _COVARIATE_OUTCOME_PATTERN.search(text_span)
        ):
            return True
        if _SPECULATIVE_SUMMARY_PATTERN.search(text_span):
            return True
        return False

    def _slugify_base_mention(self, base_mention: str, *, plural_wrapper: bool) -> str | None:
        candidate = base_mention.strip()
        if not candidate:
            return None

        if _ALL_CAPS_ACRONYM_PATTERN.fullmatch(candidate) and plural_wrapper and not candidate.endswith("S"):
            candidate = f"{candidate}s"

        normalized = candidate.lower()
        normalized = _NON_SLUG_CHARS_PATTERN.sub("-", normalized)
        normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
        if not normalized:
            return None
        if not normalized[0].isalpha():
            normalized = f"item-{normalized}"
        return normalized
