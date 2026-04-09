from __future__ import annotations

from typing import cast

from app.schemas.common_types import JsonObject, JsonValue, ScopeFilter

EVIDENCE_CONTEXT_KEY = "evidence_context"

LEGACY_EVIDENCE_CONTEXT_KEYS = {
    "assertion_text",
    "evidence_strength",
    "finding_polarity",
    "methodology_text",
    "sample_size",
    "sample_size_text",
    "source_type",
    "statement_kind",
    "statistical_support",
    "study_design",
}


def _as_json_object(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None
    return cast(JsonObject, dict(value))


def build_relation_context_payload(
    *,
    scope: ScopeFilter | JsonObject | None,
    evidence_context: JsonObject | None,
) -> JsonObject | None:
    payload: JsonObject = {}

    if scope:
        payload.update(dict(scope))

    if evidence_context:
        payload[EVIDENCE_CONTEXT_KEY] = dict(evidence_context)

    return payload or None


def split_relation_context_payload(
    stored_scope: object,
) -> tuple[ScopeFilter | None, JsonObject | None]:
    scope_data = _as_json_object(stored_scope)
    if not scope_data:
        return None, None

    scope: ScopeFilter = {}
    evidence_context: JsonObject = {}

    nested_evidence = _as_json_object(scope_data.get(EVIDENCE_CONTEXT_KEY))
    if nested_evidence:
        evidence_context.update(nested_evidence)

    for key, value in scope_data.items():
        if key == EVIDENCE_CONTEXT_KEY:
            continue
        if key in LEGACY_EVIDENCE_CONTEXT_KEYS:
            evidence_context[key] = cast(JsonValue, value)
            continue
        scope[key] = cast(str | int | float | bool | None, value)

    return (scope or None), (evidence_context or None)
