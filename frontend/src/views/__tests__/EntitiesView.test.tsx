/**
 * Tests for EntitiesView component.
 *
 * Tests entity list display, filtering, pagination, and category badge display.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
import { EntitiesView } from '../EntitiesView';
import * as entityApi from '../../api/entities';

// Mock the API module
vi.mock('../../api/entities');

// Mock react-router navigation
const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    Link: actual.Link,
  };
});

// Mock filter components
vi.mock('../../components/filters', () => ({
  FilterDrawer: ({ children }: { children: React.ReactNode }) => <div data-testid="filter-drawer">{children}</div>,
  FilterSection: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CheckboxFilter: () => <div data-testid="checkbox-filter">Checkbox Filter</div>,
  SearchFilter: () => <div data-testid="search-filter">Search Filter</div>,
}));

// Mock ScrollToTop component
vi.mock('../../components/ScrollToTop', () => ({
  ScrollToTop: () => <div data-testid="scroll-to-top">Scroll to Top</div>,
}));

// Mock hooks
vi.mock('../../hooks/useFilterDrawer', () => ({
  useFilterDrawer: () => ({
    isOpen: false,
    openDrawer: vi.fn(),
    closeDrawer: vi.fn(),
  }),
}));

vi.mock('../../hooks/usePersistedFilters', () => ({
  usePersistedFilters: () => ({
    filters: {},
    setFilter: vi.fn(),
    clearAllFilters: vi.fn(),
    activeFilterCount: 0,
  }),
}));

vi.mock('../../hooks/useDebounce', () => ({
  useDebounce: (value: any) => value,
}));

vi.mock('../../hooks/useInfiniteScroll', () => ({
  useInfiniteScroll: () => ({ current: null }),
}));

describe('EntitiesView', () => {
  const mockEntities = [
    {
      id: 'entity-1',
      slug: 'aspirin',
      summary: { en: 'Analgesic drug' },
      ui_category_id: 'cat-1',
      created_at: new Date().toISOString(),
    },
    {
      id: 'entity-2',
      slug: 'diabetes',
      summary: { en: 'Metabolic disease' },
      ui_category_id: 'cat-2',
      created_at: new Date().toISOString(),
    },
    {
      id: 'entity-3',
      slug: 'fever',
      summary: { en: 'Elevated body temperature' },
      ui_category_id: undefined, // No category
      created_at: new Date().toISOString(),
    },
  ];

  const mockFilterOptions = {
    ui_categories: [
      { id: 'cat-1', label: { en: 'Drugs', fr: 'Médicaments' } },
      { id: 'cat-2', label: { en: 'Diseases', fr: 'Maladies' } },
    ],
    consensus_levels: null,
    evidence_quality_range: null,
    year_range: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock listEntities
    vi.mocked(entityApi.listEntities).mockResolvedValue({
      items: mockEntities,
      total: mockEntities.length,
      limit: 50,
      offset: 0,
    });

    // Mock getEntityFilterOptions
    vi.mocked(entityApi.getEntityFilterOptions).mockResolvedValue(mockFilterOptions);
  });

  it('renders entity list', async () => {
    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('aspirin')).toBeInTheDocument();
      expect(screen.getByText('diabetes')).toBeInTheDocument();
      expect(screen.getByText('fever')).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays entity summaries', async () => {
    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Analgesic drug')).toBeInTheDocument();
      expect(screen.getByText('Metabolic disease')).toBeInTheDocument();
      expect(screen.getByText('Elevated body temperature')).toBeInTheDocument();
    });
  });

  it('displays category badges for entities with categories', async () => {
    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Check that category chips are displayed
      expect(screen.getByText('Drugs')).toBeInTheDocument();
      expect(screen.getByText('Diseases')).toBeInTheDocument();
    });
  });

  it('does not display category badge for entities without category', async () => {
    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    await waitFor(() => {
      // The entity 'fever' has no category, so no extra badge should appear
      // We verify this by counting the category chips
      const drugsChips = screen.getAllByText('Drugs');
      const diseasesChips = screen.getAllByText('Diseases');

      expect(drugsChips).toHaveLength(1); // Only for 'aspirin'
      expect(diseasesChips).toHaveLength(1); // Only for 'diabetes'
    });
  });

  it('displays category badges with correct language labels', async () => {
    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    // Should use English labels by default
    await waitFor(() => {
      expect(screen.getByText('Drugs')).toBeInTheDocument();
      expect(screen.getByText('Diseases')).toBeInTheDocument();
    });
  });

  it('renders create entity button', async () => {
    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /create entity/i })).toBeInTheDocument();
    });
  });

  it('renders filter button', async () => {
    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /filters/i })).toBeInTheDocument();
    });
  });

  it('fetches filter options on mount', async () => {
    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(entityApi.getEntityFilterOptions).toHaveBeenCalled();
    });
  });

  it('fetches entities on mount', async () => {
    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(entityApi.listEntities).toHaveBeenCalled();
    });
  });

  it('displays empty state when no entities', async () => {
    vi.mocked(entityApi.listEntities).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });

    render(
      <BrowserRouter>
        <EntitiesView />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });

    // List should be rendered but empty
    const list = screen.getByRole('list');
    expect(list).toBeInTheDocument();
    expect(list.children).toHaveLength(0);
  });
});
