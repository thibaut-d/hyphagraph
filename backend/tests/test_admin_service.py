"""
Tests for AdminService — user management operations for superusers.
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.models.ui_category import UiCategory
from app.models.user import User
from app.schemas.admin import UserUpdate
from app.schemas.ui_category import UICategoryWrite
from app.services.admin_service import AdminService
from app.utils.errors import AppException, ValidationException


def _make_user(
    *,
    is_active: bool = True,
    is_superuser: bool = False,
    is_verified: bool = True,
) -> User:
    return User(
        id=uuid4(),
        email=f"user-{uuid4().hex[:8]}@example.com",
        hashed_password="$2b$12$placeholder",
        is_active=is_active,
        is_superuser=is_superuser,
        is_verified=is_verified,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
class TestAdminService:

    async def test_get_stats_counts_users(self, db_session):
        admin1 = _make_user(is_superuser=True)
        admin2 = _make_user(is_superuser=True)
        regular = _make_user()
        inactive = _make_user(is_active=False)
        for u in (admin1, admin2, regular, inactive):
            db_session.add(u)
        await db_session.commit()

        svc = AdminService(db_session)
        stats = await svc.get_stats()

        assert stats.total_users >= 4
        assert stats.superusers >= 2
        assert stats.active_users >= 3

    async def test_list_users_returns_paginated(self, db_session):
        for _ in range(3):
            db_session.add(_make_user())
        await db_session.commit()

        svc = AdminService(db_session)
        page = await svc.list_users(limit=2, offset=0)
        assert len(page) <= 2

    async def test_get_user_returns_record(self, db_session):
        user = _make_user()
        db_session.add(user)
        await db_session.commit()

        svc = AdminService(db_session)
        read = await svc.get_user(user.id)
        assert str(read.id) == str(user.id)
        assert read.email == user.email

    async def test_get_user_not_found_raises_404(self, db_session):
        svc = AdminService(db_session)
        with pytest.raises(AppException) as exc:
            await svc.get_user(uuid4())
        assert exc.value.status_code == 404

    async def test_update_user_changes_flags(self, db_session):
        user = _make_user(is_active=True, is_verified=False)
        db_session.add(user)
        await db_session.commit()

        svc = AdminService(db_session)
        admin_id = uuid4()  # Different user → no self-modification guard
        result = await svc.update_user(
            user.id,
            UserUpdate(is_active=False, is_verified=True),
            admin_id,
        )
        assert result.is_active is False
        assert result.is_verified is True

    async def test_update_user_cannot_deactivate_self(self, db_session):
        admin = _make_user(is_superuser=True)
        db_session.add(admin)
        await db_session.commit()

        svc = AdminService(db_session)
        with pytest.raises(ValidationException) as exc:
            await svc.update_user(admin.id, UserUpdate(is_active=False), admin.id)
        assert "deactivate yourself" in exc.value.detail.lower()

    async def test_update_user_cannot_demote_self(self, db_session):
        admin = _make_user(is_superuser=True)
        db_session.add(admin)
        await db_session.commit()

        svc = AdminService(db_session)
        with pytest.raises(ValidationException) as exc:
            await svc.update_user(admin.id, UserUpdate(is_superuser=False), admin.id)
        assert "superuser" in exc.value.detail.lower()

    async def test_update_user_cannot_demote_last_superuser(self, db_session):
        sole_super = _make_user(is_superuser=True)
        db_session.add(sole_super)
        await db_session.commit()

        svc = AdminService(db_session)
        other_admin_id = uuid4()
        with pytest.raises(ValidationException) as exc:
            await svc.update_user(
                sole_super.id, UserUpdate(is_superuser=False), other_admin_id
            )
        assert "last superuser" in exc.value.detail.lower()

    async def test_delete_user_removes_record(self, db_session):
        user = _make_user()
        db_session.add(user)
        await db_session.commit()

        svc = AdminService(db_session)
        await svc.delete_user(user.id, admin_id=uuid4())

        with pytest.raises(AppException):
            await svc.get_user(user.id)

    async def test_delete_user_cannot_delete_self(self, db_session):
        admin = _make_user(is_superuser=True)
        db_session.add(admin)
        await db_session.commit()

        svc = AdminService(db_session)
        with pytest.raises(ValidationException) as exc:
            await svc.delete_user(admin.id, admin_id=admin.id)
        assert "delete yourself" in exc.value.detail.lower()

    async def test_list_categories_returns_ordered_items(self, db_session):
        db_session.add(UiCategory(slug="b", labels={"en": "B"}, order=2))
        db_session.add(UiCategory(slug="a", labels={"en": "A"}, order=1))
        await db_session.commit()

        svc = AdminService(db_session)
        categories = await svc.list_categories()

        assert [category.slug for category in categories] == ["a", "b"]

    async def test_create_category_persists_record(self, db_session):
        svc = AdminService(db_session)

        category = await svc.create_category(
            UICategoryWrite(
                slug="drugs",
                labels={"en": "Drugs"},
                description={"en": "Drug category"},
                order=1,
            )
        )

        assert category.slug == "drugs"
        assert category.labels["en"] == "Drugs"

    async def test_get_category_not_found_raises_404(self, db_session):
        svc = AdminService(db_session)

        with pytest.raises(AppException) as exc:
            await svc.get_category(uuid4())

        assert exc.value.status_code == 404

    async def test_update_category_changes_fields(self, db_session):
        category = UiCategory(slug="drugs", labels={"en": "Drugs"}, order=1)
        db_session.add(category)
        await db_session.commit()

        svc = AdminService(db_session)
        updated = await svc.update_category(
            category.id,
            UICategoryWrite(
                slug="medications",
                labels={"en": "Medications"},
                description={"en": "Updated"},
                order=5,
            ),
        )

        assert updated.slug == "medications"
        assert updated.labels["en"] == "Medications"
        assert updated.order == 5

    async def test_delete_category_removes_record(self, db_session):
        category = UiCategory(slug="drugs", labels={"en": "Drugs"}, order=1)
        db_session.add(category)
        await db_session.commit()

        svc = AdminService(db_session)
        await svc.delete_category(category.id)

        with pytest.raises(AppException) as exc:
            await svc.get_category(category.id)

        assert exc.value.status_code == 404

    async def test_create_category_duplicate_slug_raises_conflict(self, db_session):
        db_session.add(UiCategory(slug="drugs", labels={"en": "Drugs"}, order=1))
        await db_session.commit()

        svc = AdminService(db_session)

        with pytest.raises(AppException) as exc:
            await svc.create_category(
                UICategoryWrite(
                    slug="drugs",
                    labels={"en": "Duplicate Drugs"},
                    description=None,
                    order=2,
                )
            )

        assert exc.value.status_code == 409
