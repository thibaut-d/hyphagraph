from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def _script_directory() -> ScriptDirectory:
    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[1] / "alembic"),
    )
    return ScriptDirectory.from_config(alembic_cfg)


def test_alembic_head_includes_revision_confirmation_and_review_revisions() -> None:
    script = _script_directory()

    confirmation_revision = script.get_revision("010_add_rev_confirm_fields")
    review_status_revision = script.get_revision("013_add_llm_review_status")
    role_guard_revision = script.get_revision("016_entity_term_role_guards")

    assert confirmation_revision is not None
    assert review_status_revision is not None
    assert role_guard_revision is not None

    confirmation_source = Path(confirmation_revision.path).read_text()
    assert '"entity_revisions"' in confirmation_source
    assert '"source_revisions"' in confirmation_source
    assert '"relation_revisions"' in confirmation_source
    assert "confirmed_by_user_id" in confirmation_source
    assert "confirmed_at" in confirmation_source
    assert "ix_entity_revisions_current_unique" in confirmation_source
    assert "ix_source_revisions_current_unique" in confirmation_source
    assert "ix_relation_revisions_current_unique" in confirmation_source

    review_status_source = Path(review_status_revision.path).read_text()
    assert "llm_review_status" in review_status_source


def test_alembic_history_retains_trust_and_role_guard_invariants() -> None:
    script = _script_directory()

    initial_revision = script.get_revision("001_initial_schema")
    role_guard_revision = script.get_revision("016_entity_term_role_guards")

    assert initial_revision is not None
    assert role_guard_revision is not None

    initial_source = Path(initial_revision.path).read_text()
    assert "ck_source_revisions_trust_level" in initial_source
    assert "trust_level >= 0" in initial_source
    assert "trust_level <= 1" in initial_source

    role_guard_source = Path(role_guard_revision.path).read_text()
    assert "ix_entity_terms_entity_term_null_language_unique" in role_guard_source
    assert "uq_relation_role_revision_participant" in role_guard_source
