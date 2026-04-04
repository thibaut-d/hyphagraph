import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

import { SearchView } from "../SearchView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import * as searchApi from "../../api/search";
import { ErrorCode } from "../../utils/errorHandler";

vi.mock("../../api/search");
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (_key: string, defaultValue?: string) => defaultValue ?? _key,
  }),
  initReactI18next: { type: '3rdParty', init: () => {} },
}));

const showError = vi.fn();

vi.mock("../../notifications/NotificationContext", () => ({
  NotificationProvider: ({ children }: { children: ReactNode }) => children,
  useNotification: () => ({
    showError,
    showInfo: vi.fn(),
    showSuccess: vi.fn(),
    showWarning: vi.fn(),
  }),
}));

describe("SearchView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the parsed backend error message inline", async () => {
    vi.spyOn(searchApi, "search").mockRejectedValue({
      code: ErrorCode.RATE_LIMIT_EXCEEDED,
      message: "Too many requests. Please try again later.",
      details: "Rate limit exceeded for search",
    });

    render(
      <NotificationProvider>
        <MemoryRouter initialEntries={["/search"]}>
          <SearchView />
        </MemoryRouter>
      </NotificationProvider>,
    );

    fireEvent.change(
      screen.getByLabelText("Search entities, sources, relations..."),
      { target: { value: "aspirin" } },
    );

    await waitFor(() => {
      expect(
        screen.getByText("Too many requests. Please try again later."),
      ).toBeInTheDocument();
    });

    expect(showError).toHaveBeenCalled();
  });

  it("routes relation results to the exact source evidence row and preserves relation detail access", async () => {
    vi.spyOn(searchApi, "search").mockResolvedValue({
      query: "aspirin",
      total: 1,
      limit: 20,
      offset: 0,
      entity_count: 0,
      source_count: 0,
      relation_count: 1,
      results: [
        {
          id: "rel-1",
          type: "relation",
          title: "treats",
          snippet: "Aspirin treats headache",
          source_id: "src-1",
          entity_ids: ["entity-1", "entity-2"],
          direction: "supports",
        },
      ],
    });

    render(
      <NotificationProvider>
        <MemoryRouter initialEntries={["/search"]}>
          <SearchView />
        </MemoryRouter>
      </NotificationProvider>,
    );

    fireEvent.change(
      screen.getByLabelText("Search entities, sources, relations..."),
      { target: { value: "aspirin" } },
    );

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "treats" })).toHaveAttribute(
        "href",
        "/sources/src-1?relation=rel-1#relation-rel-1",
      );
    });

    expect(screen.getByRole("link", { name: "Relation details" })).toHaveAttribute(
      "href",
      "/relations/rel-1",
    );
  });
});
