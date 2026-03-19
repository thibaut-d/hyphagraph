"""
Pact provider verification — all APIs.

Reads every pact file in the pacts/ directory and verifies the backend
satisfies each interaction using the existing test infrastructure.

Usage:
    # 1. Generate pact files (frontend):
    #    cd frontend && npm run test:pact
    #
    # 2. Verify the provider (backend):
    #    cd backend && pytest tests/test_pact_provider.py -v

No external pact binary needed — uses AsyncClient / ASGITransport with the
same SQLite in-memory setup as all other backend tests.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.base import Base
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.models.staged_extraction import StagedExtraction
from app.models.ui_category import UiCategory
from app.models.user import User

PACT_DIR = Path(__file__).parent.parent.parent / "pacts"

# Stable IDs that match every consumer test file
KNOWN_ENTITY_ID = UUID("123e4567-e89b-42d3-a456-426614174000")
KNOWN_CATEGORY_ID = UUID("123e4567-e89b-42d3-a456-426614174001")
KNOWN_SOURCE_ID = UUID("223e4567-e89b-42d3-a456-426614174000")
KNOWN_RELATION_ID = UUID("323e4567-e89b-42d3-a456-426614174000")
KNOWN_EXTRACTION_ID = UUID("423e4567-e89b-42d3-a456-426614174000")
KNOWN_TERM_ID = UUID("523e4567-e89b-42d3-a456-426614174000")
KNOWN_USER_ID = UUID("623e4567-e89b-42d3-a456-426614174000")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def pact_db():
    """Fresh SQLite in-memory DB for pact provider tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.execute(sql_text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def pact_client(pact_db: AsyncSession):
    """
    AsyncClient with DB override and a pre-created test user.
    The get_current_user dependency always returns this user so all
    authenticated interactions work without real JWTs.
    """
    test_user = User(
        id=KNOWN_USER_ID,
        email="pact@example.com",
        hashed_password="hashed",
        is_active=True,
        is_verified=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
    )
    pact_db.add(test_user)
    await pact_db.commit()

    async def _get_db():
        yield pact_db

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        yield client, pact_db

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Provider state setup helpers
# ---------------------------------------------------------------------------


async def _ensure_entity(db: AsyncSession) -> None:
    if await db.get(Entity, KNOWN_ENTITY_ID):
        return
    db.add(Entity(id=KNOWN_ENTITY_ID))
    await db.flush()
    db.add(EntityRevision(entity_id=KNOWN_ENTITY_ID, slug="aspirin", is_current=True))
    await db.commit()


async def _ensure_source(db: AsyncSession) -> None:
    if await db.get(Source, KNOWN_SOURCE_ID):
        return
    db.add(Source(id=KNOWN_SOURCE_ID))
    await db.flush()
    db.add(
        SourceRevision(
            source_id=KNOWN_SOURCE_ID,
            kind="study",
            title="Test Study",
            url="https://example.com",
            trust_level=0.8,
            is_current=True,
        )
    )
    await db.commit()


async def _ensure_relation(db: AsyncSession) -> None:
    await _ensure_entity(db)
    await _ensure_source(db)
    if await db.get(Relation, KNOWN_RELATION_ID):
        return
    db.add(Relation(id=KNOWN_RELATION_ID, source_id=KNOWN_SOURCE_ID))
    await db.flush()
    rev = RelationRevision(
        relation_id=KNOWN_RELATION_ID,
        kind="treats",
        direction="positive",
        confidence=0.8,
        is_current=True,
    )
    db.add(rev)
    await db.flush()
    db.add(
        RelationRoleRevision(
            relation_revision_id=rev.id,
            entity_id=KNOWN_ENTITY_ID,
            role_type="drug",
        )
    )
    await db.commit()


async def _ensure_category(db: AsyncSession) -> None:
    if await db.get(UiCategory, KNOWN_CATEGORY_ID):
        return
    db.add(
        UiCategory(
            id=KNOWN_CATEGORY_ID,
            slug="drug",
            labels={"en": "Drug", "fr": "Médicament"},
            order=0,
        )
    )
    await db.commit()


async def _ensure_term(db: AsyncSession) -> None:
    await _ensure_entity(db)
    if await db.get(EntityTerm, KNOWN_TERM_ID):
        return
    db.add(
        EntityTerm(
            id=KNOWN_TERM_ID,
            entity_id=KNOWN_ENTITY_ID,
            term="Aspirin",
            language="en",
            display_order=0,
        )
    )
    await db.commit()


async def _ensure_staged_extraction(db: AsyncSession) -> None:
    await _ensure_source(db)
    if await db.get(StagedExtraction, KNOWN_EXTRACTION_ID):
        return
    db.add(
        StagedExtraction(
            id=KNOWN_EXTRACTION_ID,
            extraction_type="entity",
            status="pending",
            source_id=KNOWN_SOURCE_ID,
            extraction_data={
                "slug": "aspirin",
                "category": "drug",
                "confidence": "high",
                "text_span": "aspirin",
            },
            validation_score=0.9,
            confidence_adjustment=0.0,
            validation_flags=[],
            auto_commit_eligible=False,
        )
    )
    await db.commit()


async def _setup_state(state: str, db: AsyncSession) -> None:
    """Dispatch to the right setup helper based on provider state name."""
    s = state.lower()

    if "entity" in s and "term" in s:
        await _ensure_term(db)
    elif "entity" in s and "infer" in s:
        await _ensure_relation(db)
    elif "entity" in s and "id" in s:
        await _ensure_entity(db)
    elif "some entities" in s or "entities exist" in s:
        await _ensure_entity(db)
    elif "source" in s and "id" in s:
        await _ensure_source(db)
    elif "some sources" in s or "sources exist" in s:
        await _ensure_source(db)
    elif "relation" in s and "id" in s:
        await _ensure_relation(db)
    elif "relations exist" in s:
        await _ensure_relation(db)
    elif "category" in s or "categories" in s:
        await _ensure_category(db)
    elif "staged extraction" in s or "extraction" in s:
        await _ensure_staged_extraction(db)
    # "user is authenticated" → handled by dependency override; no DB work needed.
    # "no user with email ... exists" → registration test; no pre-existing user needed.


# ---------------------------------------------------------------------------
# Pact matcher helpers
# ---------------------------------------------------------------------------


def _extract_example(node):
    """Unwrap pact matcher objects into their concrete example values."""
    if isinstance(node, dict):
        if "pact:matcher:type" in node or "pact:generator:type" in node:
            return _extract_example(node.get("value"))
        return {k: _extract_example(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_extract_example(i) for i in node]
    return node


def _validate(actual, expected, path="$") -> list[str]:
    """
    Structural validation: every key in the expected example must exist in
    the actual response.  Catches field removal without implementing the
    full Pact matching-rule spec.
    """
    errors: list[str] = []

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, got {type(actual).__name__}"]
        for key, exp_val in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key}: field missing in response")
                continue
            errors.extend(_validate(actual[key], exp_val, f"{path}.{key}"))

    elif isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}: expected array, got {type(actual).__name__}"]
        if expected:
            for item in actual:
                errors.extend(_validate(item, expected[0], f"{path}[*]"))

    return errors


# ---------------------------------------------------------------------------
# The test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pact_provider(pact_client):
    """
    Verify every interaction in every pact file against the live backend.
    Skips if no pact files exist (run `cd frontend && npm run test:pact` first).
    """
    pact_files = sorted(PACT_DIR.glob("*.json"))
    if not pact_files:
        pytest.skip(
            f"No pact files found in {PACT_DIR}\n"
            "Generate them first:  cd frontend && npm run test:pact"
        )

    client, db = pact_client
    failures: list[str] = []

    for pact_file in pact_files:
        pact = json.loads(pact_file.read_text())

        for interaction in pact.get("interactions", []):
            desc = interaction["description"]

            # Provider states: V4 spec → array; V3 → plain string.
            raw_states = interaction.get("providerStates", interaction.get("providerState", []))
            if isinstance(raw_states, str):
                raw_states = [{"name": raw_states}]
            for s in raw_states:
                await _setup_state(s.get("name", ""), db)

            # "create a term" interactions need a clean slate — the list-terms
            # interaction may have already seeded the same term.
            if "create a term" in desc.lower():
                await db.execute(delete(EntityTerm).where(EntityTerm.entity_id == KNOWN_ENTITY_ID))
                await _ensure_entity(db)
                await db.commit()

            req = interaction["request"]
            method = req["method"].upper()
            path = req["path"]

            # Pact V4 stores header values as lists; httpx requires plain strings.
            raw_headers = req.get("headers", {})
            headers = {k: v[0] if isinstance(v, list) else v for k, v in raw_headers.items()}

            req_body = req.get("body")
            if isinstance(req_body, dict) and "content" in req_body:
                req_body = req_body["content"]

            # Append query string from pact query object if present
            query_params = req.get("query", {})
            if query_params:
                qs = "&".join(
                    f"{k}={v[0] if isinstance(v, list) else v}"
                    for k, v in query_params.items()
                )
                path = f"{path}?{qs}"

            kwargs: dict = {"headers": headers}
            if req_body is not None:
                kwargs["json"] = req_body

            try:
                response = await getattr(client, method.lower())(path, **kwargs)
            except Exception as exc:
                failures.append(f"[{desc}] Server raised {type(exc).__name__}: {exc}")
                # Recover the session so subsequent interactions can still run.
                try:
                    await db.rollback()
                except Exception:
                    pass
                continue

            # --- Status check ---
            expected = interaction["response"]
            expected_status = expected.get("status", 200)
            if response.status_code != expected_status:
                failures.append(
                    f"[{desc}] HTTP {response.status_code} ≠ {expected_status}: "
                    f"{response.text[:300]}"
                )
                continue

            # --- Body shape check ---
            resp_body = expected.get("body")
            if resp_body is None:
                continue
            if isinstance(resp_body, dict) and "content" in resp_body:
                resp_body = resp_body["content"]

            example = _extract_example(resp_body)
            errs = _validate(response.json(), example)
            for e in errs:
                failures.append(f"[{desc}] {e}")

    assert not failures, "Pact provider verification failed:\n" + "\n".join(
        f"  • {f}" for f in failures
    )
