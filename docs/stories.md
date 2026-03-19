# User Stories — HyphaGraph

> Written from the product owner's perspective. These stories define expected system behavior and are the canonical reference for acceptance testing.

---

## Roles

| Role | Description |
|------|-------------|
| **Guest** | Unauthenticated visitor |
| **User** | Authenticated researcher, physician, or analyst |
| **Admin** | Superuser with full system access |

---

## Epic 1 — Authentication

### US-AUTH-01 — Login

As a **User**, I want to log in with my email and password so that I can access the knowledge graph.

**Acceptance criteria:**
- A login form is accessible at `/login`
- Submitting valid credentials redirects the user to the home page
- Submitting invalid credentials shows an error message without revealing which field is wrong
- After login, the user's name or email is visible in the navigation
- The session persists across page refreshes (JWT stored client-side)

---

### US-AUTH-02 — Logout

As a **User**, I want to log out so that my session is terminated and the next person at this device cannot access my account.

**Acceptance criteria:**
- A logout action is accessible from the navigation
- After logout, the user is redirected to the login page
- Accessing a protected route after logout redirects to login

---

### US-AUTH-03 — Registration

As a **Guest**, I want to create an account so that I can contribute to and explore the knowledge graph.

**Acceptance criteria:**
- A registration form is accessible from the login page
- The form requires email and password (and password confirmation)
- A weak or mismatched password shows an inline error
- A duplicate email shows an appropriate error
- On success, the user is logged in and redirected to the home page

---

### US-AUTH-04 — Password Reset

As a **User**, I want to reset my password via email so that I can regain access if I forget it.

**Acceptance criteria:**
- A "Forgot password" link is accessible from the login page
- Submitting the form with a known email sends a reset link
- Submitting with an unknown email does not reveal whether the account exists
- Clicking a valid reset link shows a form to set a new password
- An expired or already-used token shows an error
- After a successful reset the user can log in with the new password

---

## Epic 2 — Navigation

### US-NAV-01 — Main Navigation

As a **User**, I want a persistent top navigation bar so that I can switch between major sections at any time.

**Acceptance criteria:**
- The navigation bar is visible on every page
- It contains links to: Home, Entities, Sources, Account
- The product logo/name is clickable and returns the user to the home page
- The active route is visually distinguished
- A global search entry point is visible and accessible

---

### US-NAV-02 — Responsive Navigation (Mobile)

As a **User** on a mobile device, I want a collapsible menu so that the navigation does not obstruct content on a small screen.

**Acceptance criteria:**
- On screens narrower than 900 px, the nav links are replaced by a hamburger icon
- Tapping the icon opens a side drawer with all main navigation links
- The drawer closes automatically after a link is tapped
- A language switcher is accessible inside the drawer
- The user's profile info is visible in the drawer footer

---

### US-NAV-03 — Home Page

As a **User**, I want a home page that orients me quickly so that I can decide where to go next.

**Acceptance criteria:**
- The home page is accessible at `/`
- It provides visible entry points to Entities and Sources
- It loads without error for any authenticated user

---

## Epic 3 — Entities

### US-ENT-01 — Browse Entities

As a **User**, I want to browse the list of entities so that I can discover what knowledge objects exist in the graph.

**Acceptance criteria:**
- `/entities` shows a list of entity cards or rows
- Each item displays: name, type/category, and a consensus level indicator
- The list is paginated or virtually scrolled for large datasets
- An empty state is shown when no entities exist

---

### US-ENT-02 — Filter Entities

As a **User**, I want to filter the entity list so that I can narrow down to entities relevant to my query.

**Acceptance criteria:**
- A filter drawer is accessible from the entities list page
- Filters include: entity category, consensus level, evidence quality
- Applying a filter updates the list without a full page reload
- A visible indicator shows when filters are active
- Filters do not alter computed scores — only the display is affected

---

### US-ENT-03 — Search Entities

As a **User**, I want to search for entities by name or term so that I can find a specific one quickly.

**Acceptance criteria:**
- The global search bar accepts text input
- Results include matching entities by name and synonymous terms
- Search is accessible from the navigation and from `/entities`
- Selecting a result navigates to the entity detail page

---

### US-ENT-04 — View Entity Detail

As a **User**, I want to open an entity's detail page so that I can understand what is known about it.

**Acceptance criteria:**
- `/entities/:entityId` displays the entity's name and category
- A summary (human-authored or LLM-generated) is shown, clearly labeled as such
- External reference links (e.g. Wikipedia) are displayed if available
- Derived properties with their consensus status are listed
- Each property links to its supporting evidence
- Key contributing sources are ranked and listed
- The page clearly distinguishes narrative summaries from computed conclusions

---

### US-ENT-05 — Filter Entity Evidence (Drawer)

As a **User**, I want to filter the evidence shown on an entity detail page so that I can focus on specific study types or time periods.

**Acceptance criteria:**
- A filter drawer is accessible on the entity detail page
- Filters include: evidence direction (supports/contradicts/mixed), study type, publication year, minimum source authority
- Applying filters does not change consensus status or computed scores
- A visible warning appears when evidence is hidden by active filters

---

### US-ENT-06 — Create Entity

As a **User**, I want to create a new entity so that I can add a knowledge object to the graph.

**Acceptance criteria:**
- A "Create entity" action is accessible from the entities list
- The form requires at minimum a name and a category
- An optional summary field is available
- Submitting a valid form creates the entity and navigates to its detail page
- Submitting an incomplete form shows inline validation errors
- The creating user is recorded as the provenance actor

---

### US-ENT-07 — Edit Entity

As a **User**, I want to edit an entity's details so that I can correct or improve the information.

**Acceptance criteria:**
- An edit action is accessible from the entity detail page
- The form is pre-filled with current values
- Saving creates a new revision; the previous revision is retained in history
- The editing user is recorded as the provenance actor for the new revision
- Cancelling discards changes

---

### US-ENT-08 — Delete Entity

As a **User**, I want to delete an entity so that I can remove erroneous or duplicate records.

**Acceptance criteria:**
- A delete action is accessible from the entity detail page
- A confirmation prompt is shown before deletion
- Deleting an entity removes it from the entity list
- Relations that referenced the deleted entity are handled gracefully (not silently broken)

---

### US-ENT-09 — Bulk Import Entities (CSV/JSON)

As a **User**, I want to import entities in bulk from a CSV or JSON file so that I can populate the graph efficiently.

**Acceptance criteria:**
- An import action is accessible from the entities list toolbar
- Supported formats: CSV and JSON
- The import has a 3-stage UI: upload → preview table → done summary
- The preview shows each row with its parsed status (valid / duplicate / error)
- The import is limited to 500 rows per batch
- Duplicate detection is performed before committing
- Per-row status is shown in the done summary
- The importing user is recorded for provenance

---

## Epic 4 — Sources

### US-SRC-01 — Browse Sources

As a **User**, I want to browse the list of sources so that I can explore the literature independently from entities.

**Acceptance criteria:**
- `/sources` shows source cards with: title, study type, year, authority score, and graph usage count
- The list supports pagination or virtual scrolling
- An empty state is shown when no sources exist

---

### US-SRC-02 — Filter Sources

As a **User**, I want to filter the source list so that I can narrow down to sources matching specific criteria.

**Acceptance criteria:**
- A filter drawer is accessible from the sources list page
- Filters include: study type, publication year, authority score, graph role (pillar/supporting/contradictory)
- Applying a filter updates the list immediately
- A visible indicator shows when filters are active

---

### US-SRC-03 — View Source Detail

As a **User**, I want to open a source's detail page so that I can critically evaluate it.

**Acceptance criteria:**
- `/sources/:sourceId` displays full metadata: title, authors, year, study type, authority score
- An abstract or summary is shown if available
- External links (DOI, URL) are displayed and functional
- Related hyperedges (relations derived from this source) are listed
- Linked entities are listed

---

### US-SRC-04 — Create Source Manually

As a **User**, I want to manually create a source so that I can add references not available through automated import.

**Acceptance criteria:**
- A "Create source" action is accessible from the sources list
- The form accepts: title, authors, year, study type, URL/DOI, authority score, summary
- Submitting a valid form creates the source and navigates to its detail page
- Inline validation errors appear for invalid or missing required fields
- The creating user is recorded for provenance

---

### US-SRC-05 — Edit Source

As a **User**, I want to edit a source's metadata so that I can correct errors or add missing information.

**Acceptance criteria:**
- An edit action is accessible from the source detail page
- The form is pre-filled with current values
- Saving creates a new revision; the previous revision is retained
- The editing user is recorded for the new revision
- Cancelling discards changes

---

### US-SRC-06 — Delete Source

As a **User**, I want to delete a source so that I can remove erroneous or duplicate entries.

**Acceptance criteria:**
- A delete action is accessible from the source detail page
- A confirmation prompt is shown before deletion
- Deleting a source is reflected immediately in the source list

---

### US-SRC-07 — Import Source from URL

As a **User**, I want to import a source by pasting a URL so that metadata can be extracted automatically.

**Acceptance criteria:**
- A "Import from URL" dialog is accessible from the sources list
- The dialog distinguishes PubMed URLs from general web URLs
- For PubMed URLs, metadata is fetched via the PubMed API
- For general URLs, available metadata is extracted from the page
- The user can review and edit the pre-filled metadata before saving
- Submitting an invalid or unreachable URL shows an appropriate error

---

### US-SRC-08 — Import Sources from PubMed Search

As a **User**, I want to search PubMed and import results so that I can add literature in bulk without leaving the application.

**Acceptance criteria:**
- A PubMed search panel is accessible from the sources list
- The user can enter a query and see a list of matching results
- Each result shows: title, authors, year, PMID
- The user can select one or more results to import
- Imported sources are created with metadata pre-filled from PubMed
- Already-imported PMIDs are flagged to prevent duplicates

---

### US-SRC-09 — Upload Document for Extraction

As a **User**, I want to upload a document (PDF) so that claims can be extracted automatically via LLM.

**Acceptance criteria:**
- A document upload action is accessible from the sources area
- Accepted format: PDF
- Upload progress is indicated
- On success, the extraction pipeline is triggered and the user is informed
- Extraction errors are surfaced clearly
- The source record is created with the document as its origin
- LLM-generated metadata is labeled as such

---

### US-SRC-10 — Bulk Import Sources (BibTeX / RIS / JSON)

As a **User**, I want to bulk-import sources from a BibTeX, RIS, or JSON file so that I can add an entire bibliography at once.

**Acceptance criteria:**
- A bulk import action is accessible from the sources list
- Supported formats: BibTeX, RIS, JSON
- The import uses a 3-stage UI: upload → preview → done summary
- Duplicates are detected before committing
- Per-record status is shown in the done summary

---

### US-SRC-11 — Export Sources

As a **User**, I want to export the sources list so that I can use the bibliography in external tools.

**Acceptance criteria:**
- An export button is accessible from the sources list
- Supported formats: JSON and CSV
- The exported file contains all currently visible (filtered) sources
- The download starts immediately

---

## Epic 5 — Relations

### US-REL-01 — View Relation Detail

As a **User**, I want to view the detail of a relation so that I can understand the specific claim made by a source.

**Acceptance criteria:**
- A relation detail view shows: kind, direction, confidence, scope, notes
- The source that asserts the claim is linked and accessible
- All participating entities with their roles are listed
- The LLM-generated flag is shown if applicable

---

### US-REL-02 — Create Relation

As a **User**, I want to create a relation between entities so that I can record a claim from a source.

**Acceptance criteria:**
- A "Create relation" action is accessible from entity detail and relation list pages
- The form requires: at least two participating entities with roles, a source, a kind/direction, and a confidence value
- Submitting a valid form creates the relation and navigates to its detail
- Inline validation errors appear for missing required fields
- The creating user is recorded for provenance

---

### US-REL-03 — Edit Relation

As a **User**, I want to edit a relation so that I can correct an incorrect claim.

**Acceptance criteria:**
- An edit action is accessible from the relation detail page
- The form is pre-filled with current values
- Saving creates a new revision; the previous revision is retained
- The editing user is recorded for the new revision

---

### US-REL-04 — Delete Relation

As a **User**, I want to delete a relation so that I can remove an erroneous or duplicate claim.

**Acceptance criteria:**
- A delete action is accessible from the relation detail page
- A confirmation prompt is shown before deletion

---

### US-REL-05 — Batch Create Relations

As a **User**, I want to create multiple relations at once so that I can record several claims from the same source efficiently.

**Acceptance criteria:**
- A batch relation creation form is accessible from the sources or relations area
- The form allows multiple rows, each defining one relation
- A shared source selector applies to all rows in the batch
- Each row shows its individual result (success / error) after submission
- Partial failures do not block successful rows

---

### US-REL-06 — Export Relations

As a **User**, I want to export relations so that I can use them in external analysis tools.

**Acceptance criteria:**
- An export button is accessible from the relations list
- Supported formats: JSON, CSV, RDF
- The download starts immediately

---

## Epic 6 — Inference & Computed Relations

### US-INF-01 — View Inferences for an Entity

As a **User**, I want to see computed inferences for an entity so that I can understand what the system has derived from the evidence.

**Acceptance criteria:**
- An inferences section is accessible from the entity detail page
- Each inference shows: kind, direction, uncertainty, contributing sources
- The computed nature of the output is clearly labeled
- Inferences are never presented as authoritative truth

---

### US-INF-02 — Filter Inferences

As a **User**, I want to filter inferences so that I can focus on a specific type or direction.

**Acceptance criteria:**
- Filters for inference direction and kind are available on the inference view
- Applying filters updates the displayed list immediately

---

### US-INF-03 — View Inference Score Detail

As a **User**, I want to see the breakdown of an inference score so that I can evaluate its reliability.

**Acceptance criteria:**
- An inference detail view shows: score, uncertainty, model version, computed date
- Contributing relations and their weights are listed
- The scope hash is shown for reproducibility

---

## Epic 7 — Explanation & Traceability

### US-EXP-01 — Trace a Conclusion to Sources

As a **User**, I want to trace any conclusion back to its source documents so that I can verify the evidence chain.

**Acceptance criteria:**
- From any computed property or inference, the user can reach the source document in at most 2 clicks
- Each intermediate step (relation → source) is explicitly navigable
- No dead-end links exist in the evidence chain

---

### US-EXP-02 — View Property Evidence

As a **User**, I want to view all hyperedges supporting or contradicting a property so that I can perform a scientific audit.

**Acceptance criteria:**
- A property detail view lists all associated evidence items
- Each item shows: readable claim, direction (support/contradict), conditions, source
- The list is sortable by direction and source authority

---

### US-EXP-03 — View Synthesis

As a **User**, I want to view the synthesized state of knowledge for an entity so that I can form an overview without reading every source.

**Acceptance criteria:**
- A synthesis view is accessible from the entity detail page
- The synthesis is algorithmically derived, never manually authored
- Contributing factors and uncertainty are displayed alongside the synthesis
- The synthesis is clearly distinguished from narrative summaries

---

### US-EXP-04 — View Disagreements

As a **User**, I want to see where sources disagree so that I can identify areas of scientific controversy.

**Acceptance criteria:**
- A disagreements view is accessible from the entity detail page
- Contradicting claims are shown side by side with their respective sources
- Contradictions are never hidden or downplayed
- The user can navigate from a disagreement directly to the conflicting sources

---

## Epic 8 — LLM Extraction Review

### US-LLM-01 — Review Extraction Queue

As a **User**, I want to review LLM-extracted claims before they become authoritative so that hallucinations do not enter the knowledge graph unchecked.

**Acceptance criteria:**
- A review queue is accessible from the application
- The queue lists pending extractions with: claim text, entity links, confidence score, flags
- Extractions with score ≥ 0.9 and no flags are auto-verified and do not appear in the queue
- Uncertain extractions appear with status `pending`

---

### US-LLM-02 — Approve or Reject Extractions

As a **User**, I want to approve or reject individual extractions so that I can control what enters the graph.

**Acceptance criteria:**
- Each extraction in the queue has approve and reject actions
- Approving an extraction materializes it as a relation in the graph
- Rejecting removes it from the queue without creating a relation
- The action is recorded in the audit trail with the acting user and timestamp

---

### US-LLM-03 — Batch Approve / Reject Extractions

As a **User**, I want to batch-approve or batch-reject extractions so that I can process the queue efficiently.

**Acceptance criteria:**
- The review queue supports multi-select
- Batch approve and batch reject actions are available
- Each record's status is updated individually; partial failures are reported
- The batch action is recorded in the audit trail

---

### US-LLM-04 — Filter Extraction Queue

As a **User**, I want to filter the extraction queue so that I can prioritize my review work.

**Acceptance criteria:**
- Filters for extraction type, confidence score range, and flag status are available
- Applying filters updates the queue immediately

---

### US-LLM-05 — Navigate from Extraction to Entity/Relation

As a **User**, I want to open the entity or relation linked to an extraction so that I can verify context before approving.

**Acceptance criteria:**
- Each extraction in the review queue shows links to its associated entity and relation
- Clicking a link opens the relevant detail page in the main view

---

## Epic 9 — Search

### US-SRCH-01 — Global Search

As a **User**, I want to search across entities, sources, and relations from a single search bar so that I can find relevant items regardless of their type.

**Acceptance criteria:**
- The global search bar is accessible from the main navigation on all pages
- Results are grouped by type (entities, sources, relations)
- Selecting a result navigates directly to the corresponding detail page
- The search responds within an acceptable time for a non-empty query

---

## Epic 10 — Account Management

### US-ACC-01 — View Account Settings

As a **User**, I want to view and update my account settings so that I can manage my profile.

**Acceptance criteria:**
- `/account` displays the current user's email and profile information
- The user can change their password from this page
- Changes are saved with confirmation feedback

---

## Epic 11 — Admin

### US-ADM-01 — Manage Users

As an **Admin**, I want to manage user accounts so that I can control who has access to the system.

**Acceptance criteria:**
- An admin panel is accessible to superusers only
- The panel lists all users with their email, active status, and role
- The admin can activate, deactivate, or promote users
- Non-admin users cannot access the admin panel (403 returned)

---

### US-ADM-02 — Manage UI Categories

As an **Admin**, I want to manage UI categories so that entities can be grouped meaningfully for end users.

**Acceptance criteria:**
- The admin panel allows creating, editing, and deleting UI categories
- Each category has a slug (unique), labels (localised), description, and display order
- Category changes are reflected immediately in the entity list and filters

---

## Epic 12 — Internationalisation

### US-I18N-01 — Switch Language

As a **User**, I want to switch the interface language so that I can use the application in my preferred language.

**Acceptance criteria:**
- A language switcher is accessible from the navigation (desktop) and from the drawer (mobile)
- Supported languages: English (EN) and French (FR)
- Switching language updates all UI strings immediately without a full page reload
- The selected language persists across sessions

---

## Non-Functional Stories

### US-NF-01 — Traceability Constraint

As a **User**, I want every claim's source to be reachable in at most 2 clicks so that I can verify knowledge quickly.

**Acceptance criteria:**
- From any displayed property, inference, or synthesis, the originating source is never more than 2 navigation steps away

---

### US-NF-02 — Contradiction Visibility

As a **User**, I want contradictions to always remain visible so that the system never misrepresents the state of evidence.

**Acceptance criteria:**
- No filter, view, or UI element permanently hides a contradiction
- When evidence is filtered out, a visible warning indicates that some items are hidden

---

### US-NF-03 — LLM Non-Authoritativeness

As a **User**, I want LLM-generated content to be clearly labeled so that I am never misled into treating AI output as verified fact.

**Acceptance criteria:**
- Every piece of content generated or assisted by an LLM carries a visible label
- LLM output cannot bypass the human review workflow to become an authoritative claim
