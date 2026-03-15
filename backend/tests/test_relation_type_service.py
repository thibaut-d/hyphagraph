import json

import pytest

from app.models.relation_type import RelationType
from app.services.relation_type_service import RelationTypeService


@pytest.mark.asyncio
async def test_suggest_new_type_returns_typed_response_when_similar_exists(db_session) -> None:
    db_session.add(
        RelationType(
            type_id="treats",
            label=json.dumps({"en": "Treats"}),
            description="Indicates a treatment effect",
            aliases=json.dumps(["cures"]),
            is_active=True,
            is_system=True,
            usage_count=5,
            category="therapeutic",
        )
    )
    await db_session.commit()

    service = RelationTypeService(db_session)

    suggestion = await service.suggest_new_type("cures", "Indicates a treatment effect")

    assert suggestion.similar_existing == "treats"
    assert suggestion.should_add is False
    assert "Similar type 'treats' already exists" in suggestion.reason


@pytest.mark.asyncio
async def test_get_statistics_returns_named_contract_with_read_models(db_session) -> None:
    db_session.add_all(
        [
            RelationType(
                type_id="treats",
                label=json.dumps({"en": "Treats"}),
                description="Indicates a treatment effect",
                aliases=json.dumps(["cures"]),
                is_active=True,
                is_system=True,
                usage_count=7,
                category="therapeutic",
            ),
            RelationType(
                type_id="causes",
                label=json.dumps({"en": "Causes"}),
                description="Indicates a causal effect",
                aliases=None,
                is_active=True,
                is_system=False,
                usage_count=3,
                category="causal",
            ),
        ]
    )
    await db_session.commit()

    service = RelationTypeService(db_session)

    stats = await service.get_statistics()

    assert stats.total_types == 2
    assert stats.system_types == 1
    assert stats.user_types == 1
    assert stats.total_usage == 10
    assert stats.by_category == {"therapeutic": 1, "causal": 1}
    assert [relation_type.type_id for relation_type in stats.most_used] == ["treats", "causes"]
    assert stats.most_used[0].aliases == ["cures"]
    assert stats.most_used[0].label == {"en": "Treats"}
