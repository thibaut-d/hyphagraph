import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import RelationsView from "../RelationsView";
import * as relationsApi from "../../api/relations";

vi.mock("../../api/relations");
vi.mock("../../components/ExportMenu", () => ({
  ExportMenu: () => <div>Export Relations</div>,
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
    <MemoryRouter initialEntries={["/relations"]}>
      <RelationsView />
    </MemoryRouter>,
  );
}

describe("RelationsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(relationsApi.listRelations).mockResolvedValue({
      items: [
        {
          id: "rel-1",
          source_id: "source-1",
          source_title: "Trial A",
          source_year: 2024,
          kind: "treats",
          direction: "supports",
          confidence: 0.82,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          status: "confirmed",
          roles: [],
        } as any,
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
  });

  it("renders a real relations index with export and batch-create actions", async () => {
    renderView();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Relations" })).toBeInTheDocument();
    });

    expect(screen.getByText("Export Relations")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Batch Create" })).toHaveAttribute("href", "/relations/batch");
    expect(screen.getByRole("link", { name: "treats" })).toHaveAttribute("href", "/relations/rel-1");
    expect(screen.getByText("Trial A (2024)")).toBeInTheDocument();
  });
});
