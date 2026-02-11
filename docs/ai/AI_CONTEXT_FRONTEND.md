# AI Context — Frontend (Layer 2)

Load this file when working on React/TypeScript frontend code.

---

## Folder Structure

```
frontend/src/
├── app/                     # App shell
│   ├── App.tsx              # Root with AuthProvider and Router
│   └── routes.tsx           # Route definitions (React Router v7)
│
├── api/                     # Typed API clients (one per domain)
│   ├── client.tsx           # Base HTTP client with token refresh
│   ├── auth.ts, entities.ts, sources.ts
│   ├── relations.ts, inferences.ts, explanations.ts
│   └── search.ts
│
├── auth/                    # Authentication context
│   ├── AuthContext.tsx       # React Context for auth state
│   └── useAuth.ts           # Custom hook
│
├── components/              # Reusable UI components
│   ├── Layout.tsx           # App shell with responsive navigation
│   ├── ProtectedRoute.tsx   # Auth-protected route wrapper
│   ├── InferenceBlock.tsx   # Inference display with "Explain" button
│   ├── EvidenceTrace.tsx    # Sortable source evidence table
│   ├── EntityTermsManager.tsx, EntityTermsDisplay.tsx
│   ├── UserAvatar.tsx, ProfileMenu.tsx, ScrollToTop.tsx
│   └── filters/            # Filter drawer components
│       ├── FilterDrawer.tsx, FilterDrawerHeader.tsx
│       ├── CheckboxFilter.tsx, RangeFilter.tsx
│       ├── SearchFilter.tsx, YearRangeFilter.tsx
│       └── ActiveFilters.tsx
│
├── views/                   # Page components (27+ views)
│   ├── HomeView.tsx
│   ├── EntitiesView.tsx, EntityDetailView.tsx
│   ├── CreateEntityView.tsx, EditEntityView.tsx
│   ├── SourcesView.tsx, SourceDetailView.tsx
│   ├── CreateSourceView.tsx, EditSourceView.tsx
│   ├── InferencesView.tsx, ExplanationView.tsx
│   ├── SearchView.tsx, SynthesisView.tsx
│   ├── DisagreementsView.tsx, EvidenceView.tsx
│   ├── PropertyDetailView.tsx
│   └── AccountView.tsx, ProfileView.tsx, ...
│
├── hooks/                   # Custom hooks
│   ├── useFilterDrawer.ts   # Filter drawer state
│   ├── usePersistedFilters.ts  # localStorage persistence
│   ├── useDebounce.ts
│   └── useInfiniteScroll.ts
│
├── types/                   # Shared TypeScript types
│   ├── entity.ts, source.ts, relation.ts
│   ├── inference.ts, filters.ts
│
├── i18n/                    # Internationalization
│   ├── config.ts            # i18next setup
│   ├── en.json, fr.json
│
└── test/
    └── setup.ts             # Vitest setup with jest-dom
```

---

## State Management

**Distributed approach** (no Redux/Zustand):

| State Type | Location | Mechanism |
|-----------|----------|-----------|
| Authentication | `auth/AuthContext.tsx` | React Context |
| Filter state | `hooks/usePersistedFilters.ts` | localStorage + hooks |
| UI state | Component-level | useState/useReducer |
| Server data | API calls in views | useEffect + useState |

---

## Critical Patterns

### API Client

All API calls go through `api/client.tsx`:

```typescript
// Base client handles auth token injection + refresh
const response = await apiFetch('/entities', { method: 'GET' });
```

- Token automatically attached from localStorage
- Automatic refresh on 401
- Type-safe response handling

### API Module Pattern

```typescript
// api/entities.ts
export async function getEntity(id: string): Promise<EntityRead> {
  return apiFetch(`/entities/${id}`);
}

export async function createEntity(data: EntityWrite): Promise<EntityRead> {
  return apiFetch('/entities', { method: 'POST', body: JSON.stringify(data) });
}
```

### View Pattern

```typescript
export default function EntityDetailView() {
  const { id } = useParams();
  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getEntity(id!).then(setEntity).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <CircularProgress />;
  if (!entity) return <Alert severity="error">Not found</Alert>;

  return (/* JSX */);
}
```

### Filter Drawer Pattern

```typescript
const { filters, setFilter, clearFilters, activeCount } = usePersistedFilters('entities', {
  search: '', category: [], yearRange: [2000, 2026]
});
```

- Filters stored in localStorage per view
- Active count shown as badge
- Warning when evidence is hidden by filters
- Filters affect display, NOT underlying calculations

---

## UX Constraints (from UX.md)

1. **Never hide contradictions** — disagreements always surfaced
2. **Never present syntheses as absolute truth** — always show uncertainty
3. **Every conclusion traceable to sources** — 2 clicks max
4. **Progressive disclosure** — summary first, details on demand
5. **Responsive** — mobile/tablet/desktop via MUI breakpoints

---

## Known Pitfalls

1. **Auth race condition** — `AuthContext` has `loading` state; `ProtectedRoute` shows spinner until auth check completes (don't redirect before loading finishes)
2. **MUI Button as Link** — `Button component={RouterLink}` renders as `<a>`, use `getByRole('link')` in tests
3. **i18n in tests** — Mock `useTranslation` or use i18n test provider
4. **Entity terms** — Fetched separately from entity; handle API errors gracefully (empty array, not blocking error)
5. **InferenceBlock** — Each role inference has an "Explain" button linking to `/explain/:entityId/:roleType`

---

## Testing Patterns

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../api/client', () => ({
  apiFetch: vi.fn(),
}));

describe('EntityDetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should display entity slug', async () => {
    (apiFetch as any).mockResolvedValue({ slug: 'test', summary: {} });
    // render and assert...
  });
});
```

- Use `vi.mock()` for API clients
- `vi.clearAllMocks()` in `beforeEach`
- Test loading, success, and error states
- For components with routing: wrap in `MemoryRouter`
