import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router";
import type { ReactNode } from "react";

import { SourcesView } from "../SourcesView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import * as sourceApi from "../../api/sources";

const mockUsePersistedFilters = vi.fn();

vi.mock("../../api/sources");

vi.mock("../../components/filters", () => ({
  FilterDrawer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  FilterSection: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CheckboxFilter: () => <div>Checkbox Filter</div>,
  RangeFilter: () => <div>Range Filter</div>,
  SearchFilter: () => <div>Search Filter</div>,
}));

vi.mock("../../components/ScrollToTop", () => ({
  ScrollToTop: () => null,
}));

vi.mock("../../components/ExportMenu", () => ({
  ExportMenu: () => null,
}));

vi.mock("../../hooks/useFilterDrawer", () => ({
  useFilterDrawer: () => ({
    isOpen: false,
    openDrawer: vi.fn(),
    closeDrawer: vi.fn(),
  }),
}));

vi.mock("../../hooks/usePersistedFilters", () => ({
  usePersistedFilters: () => mockUsePersistedFilters(),
}));

vi.mock("../../hooks/useDebounce", () => ({
  useDebounce: (value: unknown) => value,
}));

vi.mock("../../hooks/useInfiniteScroll", () => ({
  useInfiniteScroll: () => ({ current: null }),
}));

function renderView() {
  return render(
    <NotificationProvider>
      <BrowserRouter>
        <SourcesView />
      </BrowserRouter>
    </NotificationProvider>,
  );
}

describe("SourcesView", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(sourceApi.listSources).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });

    vi.mocked(sourceApi.getSourceFilterOptions).mockResolvedValue({
      kinds: ["study"],
      year_range: [2000, 2024],
      domains: ["clinical"],
      roles: ["agent"],
    });
  });

  it("refetches when domain filters change", async () => {
    let filters = {};
    mockUsePersistedFilters.mockImplementation(() => ({
      filters,
      setFilter: vi.fn(),
      clearAllFilters: vi.fn(),
      activeFilterCount: 0,
    }));

    const view = renderView();

    await waitFor(() => {
      expect(sourceApi.listSources).toHaveBeenCalled();
    });
    const initialCallCount = vi.mocked(sourceApi.listSources).mock.calls.length;

    filters = { domain: ["clinical"] };
    view.rerender(
      <NotificationProvider>
        <BrowserRouter>
          <SourcesView />
        </BrowserRouter>
      </NotificationProvider>,
    );

    await waitFor(() => {
      expect(sourceApi.listSources.mock.calls.length).toBeGreaterThan(initialCallCount);
    });

    expect(sourceApi.listSources).toHaveBeenLastCalledWith(
      expect.objectContaining({ domain: ["clinical"] }),
    );
  });

  it("refetches when role filters change", async () => {
    let filters = {};
    mockUsePersistedFilters.mockImplementation(() => ({
      filters,
      setFilter: vi.fn(),
      clearAllFilters: vi.fn(),
      activeFilterCount: 0,
    }));

    const view = renderView();

    await waitFor(() => {
      expect(sourceApi.listSources).toHaveBeenCalled();
    });
    const initialCallCount = vi.mocked(sourceApi.listSources).mock.calls.length;

    filters = { role: ["agent"] };
    view.rerender(
      <NotificationProvider>
        <BrowserRouter>
          <SourcesView />
        </BrowserRouter>
      </NotificationProvider>,
    );

    await waitFor(() => {
      expect(sourceApi.listSources.mock.calls.length).toBeGreaterThan(initialCallCount);
    });

    expect(sourceApi.listSources).toHaveBeenLastCalledWith(
      expect.objectContaining({ role: ["agent"] }),
    );
  });

  it("renders authority and graph usage metrics for each source row", async () => {
    mockUsePersistedFilters.mockImplementation(() => ({
      filters: {},
      setFilter: vi.fn(),
      clearAllFilters: vi.fn(),
      activeFilterCount: 0,
    }));

    vi.mocked(sourceApi.listSources).mockResolvedValue({
      items: [
        {
          id: "source-1",
          title: "Trial A",
          kind: "study",
          year: 2024,
          url: "https://example.com/trial-a",
          trust_level: 0.82,
          graph_usage_count: 3,
          created_at: new Date().toISOString(),
          status: "confirmed",
        } as any,
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });

    renderView();

    await waitFor(() => {
      expect(screen.getByText("Trial A")).toBeInTheDocument();
    });

    expect(screen.getByText("Authority {{value}}%")).toBeInTheDocument();
    expect(screen.getByText("Used {{count}}x")).toBeInTheDocument();
  });

  it("keeps the loading state visible while an empty filtered list refetches", async () => {
    let filters: Record<string, unknown> = {};
    mockUsePersistedFilters.mockImplementation(() => ({
      filters,
      setFilter: vi.fn(),
      clearAllFilters: vi.fn(),
      activeFilterCount: Object.keys(filters).length,
    }));

    let resolveRefetch: ((value: Awaited<ReturnType<typeof sourceApi.listSources>>) => void) | null = null;
    vi.mocked(sourceApi.listSources).mockImplementation((params) => {
      if (params?.domain?.length) {
        return new Promise((resolve) => {
          resolveRefetch = resolve;
        });
      }

      return Promise.resolve({
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
      });
    });

    const view = renderView();

    await waitFor(() => {
      expect(screen.getByText("No sources")).toBeInTheDocument();
    });
    expect(screen.getByText("No sources")).toBeInTheDocument();

    filters = { domain: ["clinical"] };
    view.rerender(
      <NotificationProvider>
        <BrowserRouter>
          <SourcesView />
        </BrowserRouter>
      </NotificationProvider>,
    );

    await waitFor(() => {
      expect(sourceApi.listSources).toHaveBeenLastCalledWith(
        expect.objectContaining({ domain: ["clinical"] }),
      );
    });

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    expect(screen.queryByText("No sources match the current filters")).not.toBeInTheDocument();

    resolveRefetch?.({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });

    await waitFor(() => {
      expect(screen.getByText("No sources match the current filters")).toBeInTheDocument();
    });
  });
});
