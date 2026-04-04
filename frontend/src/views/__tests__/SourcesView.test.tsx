import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
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
});
