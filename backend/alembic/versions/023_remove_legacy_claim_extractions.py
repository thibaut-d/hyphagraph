"""Migrate legacy staged claim extractions into relation-shaped rows.

Revision ID: 023_rm_legacy_claim_extractions
Revises: 022_add_entity_term_kind
Create Date: 2026-04-15
"""

from __future__ import annotations

import re
from typing import Any

import sqlalchemy as sa
from alembic import op


revision = "023_rm_legacy_claim_extractions"
down_revision = "022_add_entity_term_kind"
branch_labels = None
depends_on = None


MIGRATION_FLAG = "legacy_claim_migrated"


def _normalize_slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    if normalized and not normalized[0].isalpha():
        normalized = f"item-{normalized}"
    return normalized or "legacy-claim"


def _normalize_evidence_strength(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    aliases = {
        "high": "strong",
        "medium": "moderate",
        "low": "weak",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in {"strong", "moderate", "weak", "anecdotal"}:
        return normalized
    return None


def _relation_type_from_claim_type(value: Any) -> str:
    if isinstance(value, str) and value.strip().lower() == "mechanism":
        return "mechanism"
    return "other"


def _claim_to_relation_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    claim_text = payload.get("claim_text")
    text_span = payload.get("text_span") or claim_text or "Legacy migrated extraction"
    entities_involved = payload.get("entities_involved") or []
    normalized_entities = [
        _normalize_slug(entity)
        for entity in entities_involved
        if isinstance(entity, str) and entity.strip()
    ]

    if not normalized_entities:
        normalized_entities = ["legacy-claim-subject"]

    roles = [{"entity_slug": normalized_entities[0], "role_type": "subject"}]
    for entity_slug in normalized_entities[1:]:
        roles.append({"entity_slug": entity_slug, "role_type": "participant"})
    if len(roles) == 1:
        roles.append({"entity_slug": normalized_entities[0], "role_type": "context"})

    evidence_context = {"statement_kind": "finding"}
    evidence_strength = _normalize_evidence_strength(payload.get("evidence_strength"))
    if evidence_strength:
        evidence_context["evidence_strength"] = evidence_strength
    if isinstance(claim_text, str) and claim_text.strip():
        evidence_context["assertion_text"] = claim_text.strip()

    relation_payload = {
        "relation_type": _relation_type_from_claim_type(payload.get("claim_type")),
        "roles": roles,
        "confidence": payload.get("confidence") or "medium",
        "text_span": text_span,
        "notes": claim_text.strip() if isinstance(claim_text, str) and claim_text.strip() else None,
        "evidence_context": evidence_context,
    }

    flags = [MIGRATION_FLAG]
    if len(normalized_entities) < 2:
        flags.append("legacy_claim_single_entity")
    return relation_payload, flags


def _relation_to_claim_payload(payload: dict[str, Any]) -> dict[str, Any]:
    evidence_context = payload.get("evidence_context") or {}
    roles = payload.get("roles") or []
    entity_slugs: list[str] = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        entity_slug = role.get("entity_slug")
        if isinstance(entity_slug, str) and entity_slug not in entity_slugs:
            entity_slugs.append(entity_slug)

    claim_text = payload.get("notes")
    if not isinstance(claim_text, str) or not claim_text.strip():
        assertion_text = evidence_context.get("assertion_text")
        claim_text = assertion_text if isinstance(assertion_text, str) and assertion_text.strip() else payload.get("text_span")

    claim_type = "mechanism" if payload.get("relation_type") == "mechanism" else "other"
    return {
        "claim_text": claim_text,
        "entities_involved": entity_slugs,
        "claim_type": claim_type,
        "evidence_strength": evidence_context.get("evidence_strength"),
        "confidence": payload.get("confidence") or "medium",
        "text_span": payload.get("text_span") or claim_text,
    }


def upgrade() -> None:
    bind = op.get_bind()
    staged_extractions = sa.table(
        "staged_extractions",
        sa.column("id", sa.String),
        sa.column("extraction_type", sa.String),
        sa.column("extraction_data", sa.JSON),
        sa.column("validation_flags", sa.JSON),
    )

    rows = bind.execute(
        sa.select(
            staged_extractions.c.id,
            staged_extractions.c.extraction_data,
            staged_extractions.c.validation_flags,
        ).where(sa.func.lower(staged_extractions.c.extraction_type) == "claim")
    ).mappings().all()

    for row in rows:
        extraction_data = row["extraction_data"] or {}
        relation_payload, migration_flags = _claim_to_relation_payload(extraction_data)
        existing_flags = [
            flag for flag in (row["validation_flags"] or [])
            if isinstance(flag, str)
        ]
        combined_flags = existing_flags + [
            flag for flag in migration_flags if flag not in existing_flags
        ]
        bind.execute(
            staged_extractions.update()
            .where(staged_extractions.c.id == row["id"])
            .values(
                extraction_type="relation",
                extraction_data=relation_payload,
                validation_flags=combined_flags,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    staged_extractions = sa.table(
        "staged_extractions",
        sa.column("id", sa.String),
        sa.column("extraction_type", sa.String),
        sa.column("extraction_data", sa.JSON),
        sa.column("validation_flags", sa.JSON),
    )

    rows = bind.execute(
        sa.select(
            staged_extractions.c.id,
            staged_extractions.c.extraction_data,
            staged_extractions.c.validation_flags,
        ).where(
            staged_extractions.c.extraction_type == "relation"
        )
    ).mappings().all()

    for row in rows:
        existing_flags = [
            flag for flag in (row["validation_flags"] or [])
            if isinstance(flag, str)
        ]
        if MIGRATION_FLAG not in existing_flags:
            continue

        claim_payload = _relation_to_claim_payload(row["extraction_data"] or {})
        updated_flags = [flag for flag in existing_flags if flag != MIGRATION_FLAG]
        bind.execute(
            staged_extractions.update()
            .where(staged_extractions.c.id == row["id"])
            .values(
                extraction_type="claim",
                extraction_data=claim_payload,
                validation_flags=updated_flags,
            )
        )
