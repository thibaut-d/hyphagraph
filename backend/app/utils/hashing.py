"""
Scope hash generation for computed relation caching.

Implements the deterministic hashing algorithm from DATABASE_SCHEMA.md:
1. Collect entity ID and scope filter parameters
2. Sort scope attributes by key for determinism
3. Create canonical form: "entity_id|key1:val1|key2:val2|..."
4. Compute SHA256 hash
5. Return as hex string
"""
import hashlib
import json
from typing import Optional, Union
from uuid import UUID


def compute_scope_hash(
    entity_id: Union[UUID, str],
    scope_filter: Optional[dict] = None
) -> str:
    """
    Compute deterministic hash for inference query scope.

    This hash is used as a cache key for computed relations.
    Same inputs always produce the same hash (deterministic).

    Args:
        entity_id: Entity UUID (as UUID object or string)
        scope_filter: Optional scope filter dict (e.g., {"population": "adults"})

    Returns:
        SHA256 hash as 64-character hex string

    Examples:
        >>> entity_id = UUID("...")
        >>> compute_scope_hash(entity_id, {"population": "adults"})
        'a1b2c3...'  # 64-char hex string

        >>> compute_scope_hash(entity_id, None)
        'd4e5f6...'  # Different hash for no scope
    """
    # Convert UUID to string for canonical representation
    entity_str = str(entity_id)

    # Build canonical scope representation
    scope_parts = []

    if scope_filter is None:
        # Explicitly represent None scope
        scope_parts.append("scope:null")
    elif not scope_filter:
        # Empty dict
        scope_parts.append("scope:empty")
    else:
        # Sort scope attributes by key for determinism
        sorted_keys = sorted(scope_filter.keys())
        for key in sorted_keys:
            value = scope_filter[key]
            # Convert value to JSON for consistent representation
            # (handles nested dicts, lists, etc.)
            value_str = json.dumps(value, sort_keys=True)
            scope_parts.append(f"{key}:{value_str}")

    # Create canonical form: entity_id|scope_part1|scope_part2|...
    canonical = f"entity:{entity_str}|" + "|".join(scope_parts)

    # Compute SHA256 hash
    hash_obj = hashlib.sha256(canonical.encode('utf-8'))

    # Return as hex string
    return hash_obj.hexdigest()
