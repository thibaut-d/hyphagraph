## Add Admin UI for Entity Graph Merge

Allow admins to merge two knowledge-graph entity nodes into one when they refer to the
same real-world concept (e.g. "aspirin" and "acetylsalicylic-acid").

**The backend service already exists**: `backend/app/services/entity_merge_service.py`
exposes `merge_entities(source_id, target_id, db)`. What is missing is the API endpoint
and the admin panel UI.

Note: this is a *graph-level* merge (entity nodes + their relations), distinct from the
*vocabulary-level* category merge above.

### Objective
Give admins a UI-driven way to deduplicate entity nodes without direct database access.

### Impacted modules
- `backend/app/api/entities.py` (or a new `entity_merge.py`) — `POST /entities/{entity_id}/merge-into/{target_id}` (superuser)
- `frontend/src/views/AdminView.tsx` — "Merge into…" search-and-select dialog, accessible from an Entities tab or from the entity detail page

### Plan
1. Add `POST /entities/{entity_id}/merge-into/{target_id}` (superuser only) that delegates to `EntityMergeService.merge_entities()`.
   - Returns a summary of re-parented relations and deleted source node.
2. Add an Entities tab (or context menu entry on the entity detail page) in the admin panel with a merge action.
   - Type-ahead search to find the target entity by slug or label.
   - Confirmation dialog showing which entity will be kept and which removed.

### Status
completed
