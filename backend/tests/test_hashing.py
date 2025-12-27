"""
Tests for scope hash generation.

Tests the deterministic hashing algorithm from DATABASE_SCHEMA.md:
- Canonical ordering of entities and roles
- SHA256 hashing
- Determinism (same inputs → same hash)
"""
import pytest
from uuid import UUID, uuid4

from app.utils.hashing import compute_scope_hash


class TestScopeHashGeneration:
    """Test scope hash generation for computed relation caching."""

    def test_same_input_produces_same_hash(self):
        """Test determinism: same inputs → same hash."""
        entity_id = uuid4()
        scope_filter = {"population": "adults"}

        hash1 = compute_scope_hash(entity_id, scope_filter)
        hash2 = compute_scope_hash(entity_id, scope_filter)

        assert hash1 == hash2

    def test_different_entity_produces_different_hash(self):
        """Test different entity IDs produce different hashes."""
        entity_id1 = uuid4()
        entity_id2 = uuid4()
        scope_filter = {"population": "adults"}

        hash1 = compute_scope_hash(entity_id1, scope_filter)
        hash2 = compute_scope_hash(entity_id2, scope_filter)

        assert hash1 != hash2

    def test_different_scope_produces_different_hash(self):
        """Test different scope filters produce different hashes."""
        entity_id = uuid4()

        hash1 = compute_scope_hash(entity_id, {"population": "adults"})
        hash2 = compute_scope_hash(entity_id, {"population": "children"})

        assert hash1 != hash2

    def test_none_scope_produces_consistent_hash(self):
        """Test None scope is handled consistently."""
        entity_id = uuid4()

        hash1 = compute_scope_hash(entity_id, None)
        hash2 = compute_scope_hash(entity_id, None)

        assert hash1 == hash2

    def test_empty_scope_produces_different_hash_than_none(self):
        """Test empty scope {} is different from None scope."""
        entity_id = uuid4()

        hash_none = compute_scope_hash(entity_id, None)
        hash_empty = compute_scope_hash(entity_id, {})

        assert hash_none != hash_empty

    def test_scope_key_order_doesnt_matter(self):
        """Test scope attribute order doesn't affect hash (canonical ordering)."""
        entity_id = uuid4()

        hash1 = compute_scope_hash(entity_id, {"population": "adults", "condition": "chronic_pain"})
        hash2 = compute_scope_hash(entity_id, {"condition": "chronic_pain", "population": "adults"})

        assert hash1 == hash2

    def test_hash_is_hex_string(self):
        """Test hash is returned as hex string."""
        entity_id = uuid4()
        scope_filter = {"population": "adults"}

        hash_result = compute_scope_hash(entity_id, scope_filter)

        # Should be a hex string (SHA256 = 64 hex characters)
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_multiple_scope_attributes(self):
        """Test hash with multiple scope attributes."""
        entity_id = uuid4()
        scope_filter = {
            "population": "adults",
            "condition": "chronic_pain",
            "dosage": "high"
        }

        hash1 = compute_scope_hash(entity_id, scope_filter)
        hash2 = compute_scope_hash(entity_id, scope_filter)

        assert hash1 == hash2

    def test_nested_scope_values(self):
        """Test scope with nested structures (JSON values)."""
        entity_id = uuid4()

        # Scope might have complex values
        scope_filter = {
            "population": "adults",
            "age_range": {"min": 18, "max": 65}
        }

        hash1 = compute_scope_hash(entity_id, scope_filter)
        hash2 = compute_scope_hash(entity_id, scope_filter)

        # Should still be deterministic
        assert hash1 == hash2

    def test_string_entity_id(self):
        """Test scope hash works with string UUID."""
        entity_id = str(uuid4())
        scope_filter = {"population": "adults"}

        # Should work with both UUID and string
        hash_result = compute_scope_hash(entity_id, scope_filter)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64
