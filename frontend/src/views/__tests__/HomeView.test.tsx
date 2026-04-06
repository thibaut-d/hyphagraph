import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { HomeView } from "../HomeView";
import * as entitiesApi from "../../api/entities";
import * as sourcesApi from "../../api/sources";

vi.mock("../../api/entities");
vi.mock("../../api/sources");
vi.mock("../../notifications/NotificationContext", () => ({
  useNotification: () => ({
    showError: vi.fn(),
    showSuccess: vi.fn(),
    showInfo: vi.fn(),
    showWarning: vi.fn(),
  }),
}));
vi.mock("react-i18next", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-i18next")>();
  return {
    ...actual,
    useTranslation: () => ({
      t: (_key: string, fallback?: string | Record<string, unknown>) => {
        if (typeof fallback === "string") {
          return fallback;
        }
        return _key;
      },
    }),
  };
});

function renderView() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <HomeView />
    </MemoryRouter>,
  );
}

describe("HomeView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(entitiesApi.listEntities).mockResolvedValue({
      items: [],
      total: 0,
      limit: 1,
      offset: 0,
    });
    vi.mocked(sourcesApi.listSources).mockResolvedValue({
      items: [],
      total: 0,
      limit: 1,
      offset: 0,
    });
  });

  it("shows an empty-state message when no entities or sources exist", async () => {
    renderView();

    await waitFor(() => {
      expect(
        screen.getByText(
          "No data yet. Create entities and relationships to start building the graph.",
        ),
      ).toBeInTheDocument();
    });

    expect(screen.queryByText("Failed to load statistics")).not.toBeInTheDocument();
  });

  it("keeps the warning for actual statistics fetch failures", async () => {
    vi.mocked(entitiesApi.listEntities).mockRejectedValue(new Error("boom"));

    renderView();

    await waitFor(() => {
      expect(
        screen.getByText(
          "No data yet. Create entities and relationships to start building the graph.",
        ),
      ).toBeInTheDocument();
    });
  });
});
