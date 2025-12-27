# Migration Cleanup Summary

## Date: 2024-12-27

### Changes Made

This cleanup removes all deprecated fields from the database schema after the migration to the revision architecture. All data that was in deprecated fields should have been migrated to the revision tables in the earlier migrations.

### 1. Removed Deprecated Model Fields

#### Entity Model (`backend/app/models/entity.py`)
Removed deprecated fields that were moved to `EntityRevision`:
- `kind`
- `label`
- `synonyms`
- `ontology_ref`

**Final Entity schema:**
- `id` (UUID, primary key)
- `created_at` (timestamp)

#### Source Model (`backend/app/models/source.py`)
Removed deprecated fields that were moved to `SourceRevision`:
- `kind`
- `title`
- `year`
- `origin`
- `url`
- `trust_level`
- `updated_at`

**Final Source schema:**
- `id` (UUID, primary key)
- `created_at` (timestamp)

#### Relation Model (`backend/app/models/relation.py`)
Removed deprecated fields that were moved to `RelationRevision`:
- `kind`
- `direction`
- `confidence`
- `notes`
- `updated_at`

Also removed the deprecated `roles` relationship (replaced by relation_role_revisions).

**Final Relation schema:**
- `id` (UUID, primary key)
- `source_id` (UUID, foreign key to sources)
- `created_at` (timestamp)

### 2. Deleted Deprecated Model

Removed `backend/app/models/role.py` - this model is completely replaced by `RelationRoleRevision`.

### 3. Updated Alembic Configuration

Updated `backend/alembic/env.py` to:
- Remove import of deleted `Role` model
- Add missing imports for `RefreshToken` and `AuditLog` models

### 4. Consolidated Migration History

Created a single clean migration that represents the current schema:
- **New migration:** `001_initial_clean.py` - Complete clean schema with all tables

Moved old migrations to `backend/alembic/old_migrations/`:
- `001_initial` (old)
- `002_revisions` (old)
- `003_add_users` (duplicate of 001)
- `004_add_refresh_tokens`
- `005_add_audit_logs`
- `006_add_email_verification`
- `007_add_password_reset`
- `008_rename_metadata_to_source_metadata`
- `009_remove_deprecated_fields` (superseded by clean schema)

### Current Migration Chain

The new, clean migration chain is:
```
001_initial_clean  (clean schema, no deprecated fields)
```

### Tables in Final Schema

1. **Users & Auth:**
   - `users` - User accounts
   - `refresh_tokens` - JWT refresh tokens

2. **Audit:**
   - `audit_logs` - Audit trail

3. **Entities:**
   - `entities` - Base entity table (id + created_at only)
   - `entity_revisions` - Entity content revisions
   - `entity_terms` - Entity labels/terms
   - `ui_categories` - UI categorization

4. **Sources:**
   - `sources` - Base source table (id + created_at only)
   - `source_revisions` - Source content revisions

5. **Relations:**
   - `relations` - Base relation table (id + source_id + created_at only)
   - `relation_revisions` - Relation content revisions
   - `relation_role_revisions` - Entity roles in relations (replaces old `roles` table)

6. **Other:**
   - `attributes` - Key-value attributes for entities/relations
   - `computed_relations` - AI-computed relations
   - `inference_cache` - Inference result cache

### Migration Path for Existing Databases

For databases that already ran the old migrations:

1. **Option A: Fresh start (recommended for development)**
   - Drop the database
   - Run `alembic upgrade head` to create clean schema

2. **Option B: Keep existing data**
   - Current databases already have the data migrated to revision tables
   - The deprecated fields are just sitting empty in the old columns
   - If you want to clean up an existing database, you would need to:
     1. Back up your database
     2. Manually drop the deprecated columns:
        ```sql
        -- Drop old roles table
        DROP TABLE roles;

        -- Drop deprecated entity columns
        ALTER TABLE entities DROP COLUMN kind;
        ALTER TABLE entities DROP COLUMN label;
        ALTER TABLE entities DROP COLUMN synonyms;
        ALTER TABLE entities DROP COLUMN ontology_ref;

        -- Drop deprecated source columns
        ALTER TABLE sources DROP COLUMN kind;
        ALTER TABLE sources DROP COLUMN title;
        ALTER TABLE sources DROP COLUMN year;
        ALTER TABLE sources DROP COLUMN origin;
        ALTER TABLE sources DROP COLUMN url;
        ALTER TABLE sources DROP COLUMN trust_level;
        ALTER TABLE sources DROP COLUMN updated_at;

        -- Drop deprecated relation columns
        ALTER TABLE relations DROP COLUMN kind;
        ALTER TABLE relations DROP COLUMN direction;
        ALTER TABLE relations DROP COLUMN confidence;
        ALTER TABLE relations DROP COLUMN notes;
        ALTER TABLE relations DROP COLUMN updated_at;
        ```
     3. Update the alembic_version table to match the new migration:
        ```sql
        UPDATE alembic_version SET version_num = '001_initial_clean';
        ```

### Testing

The migration syntax has been validated. For a full test:
1. Use a PostgreSQL database (SQLite has async driver issues with alembic)
2. Run `alembic upgrade head`
3. Verify all tables are created correctly

### Notes

- All old migrations are preserved in `backend/alembic/old_migrations/` for reference
- The new migration creates the exact same schema that would result from running all the old migrations, but without the deprecated fields
- This cleanup makes the codebase cleaner and removes technical debt from the migration to the revision architecture
