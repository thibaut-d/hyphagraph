import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import InferencesView from "../InferencesView";
import * as entitiesApi from "../../api/entities";
import * as inferencesApi from "../../api/inferences";

vi.mock("../../api/entities");
vi.mock("../../api/inferences");

vi.mock("../../components/ScrollToTop", () => ({
  ScrollToTop: () => null,
}));

vi.mock("../../hooks/useInfiniteScroll", () => ({
  useInfiniteScroll: () => ({ current: null }),
}));

function renderView() {
  return render(
    <MemoryRouter initialEntries={["/inferences"]}>
      <InferencesView />
    </MemoryRouter>,
  );
}

describe("InferencesView", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(entitiesApi.listEntities).mockResolvedValue({
      items: [
        {
          id: "entity-1",
          slug: "aspirin",
          summary: { en: "Analgesic" },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          status: "confirmed",
        },
        {
          id: "entity-2",
          slug: "ibuprofen",
          summary: { en: "NSAID" },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          status: "confirmed",
        },
      ],
      total: 2,
      limit: 20,
      offset: 0,
    });
  });

  it("renders a dense inference index with explicit columns and detail links", async () => {
    vi.mocked(inferencesApi.getInferenceForEntity)
      .mockResolvedValueOnce({
        entity_id: "entity-1",
        role_inferences: [
          {
            role_type: "agent",
            score: 0.7,
            confidence: 0.9,
            disagreement: 0.1,
            coverage: 2,
          },
        ],
      } as any)
      .mockResolvedValueOnce({
        entity_id: "entity-2",
        role_inferences: [
          {
            role_type: "target",
            score: -0.6,
            confidence: 0.75,
            disagreement: 0.42,
            coverage: 4,
          },
        ],
      } as any);

    renderView();

    expect(await screen.findByRole("heading", { name: "Inference Index" })).toBeInTheDocument();
    expect(screen.getAllByText("Score direction").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Evidence count")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("aspirin")).toBeInTheDocument();
      expect(screen.getByText("ibuprofen")).toBeInTheDocument();
      expect(screen.getByText("agent")).toBeInTheDocument();
      expect(screen.getByText("target")).toBeInTheDocument();
    });

    expect(screen.getByText("Support-leaning")).toBeInTheDocument();
    expect(screen.getByText("Contradiction-leaning")).toBeInTheDocument();
    const detailLinks = screen.getAllByRole("link", { name: "View detail" });
    expect(detailLinks[0]).toHaveAttribute("href", "/entities/aspirin/properties/agent");
    expect(detailLinks[1]).toHaveAttribute("href", "/entities/ibuprofen/properties/target");
  });

  it("filters the index by role and search term", async () => {
    const user = userEvent.setup();

    vi.mocked(inferencesApi.getInferenceForEntity)
      .mockResolvedValueOnce({
        entity_id: "entity-1",
        role_inferences: [
          {
            role_type: "agent",
            score: 0.7,
            confidence: 0.9,
            disagreement: 0.1,
            coverage: 2,
          },
        ],
      } as any)
      .mockResolvedValueOnce({
        entity_id: "entity-2",
        role_inferences: [
          {
            role_type: "target",
            score: -0.2,
            confidence: 0.55,
            disagreement: 0.15,
            coverage: 1,
          },
        ],
      } as any);

    renderView();

    await screen.findByText("aspirin");

    await user.type(screen.getByLabelText("Search entity or role"), "ibu");

    await waitFor(() => {
      expect(screen.getByText("ibuprofen")).toBeInTheDocument();
      expect(screen.queryByText("aspirin")).not.toBeInTheDocument();
    });

    await user.clear(screen.getByLabelText("Search entity or role"));
    await user.click(screen.getByLabelText("Role"));
    await user.click(screen.getByRole("option", { name: "agent" }));

    await waitFor(() => {
      expect(screen.getByText("aspirin")).toBeInTheDocument();
      expect(screen.queryByText("ibuprofen")).not.toBeInTheDocument();
    });
  });

  it("shows an explicit entity-level error strip and retries failed entities", async () => {
    const user = userEvent.setup();

    vi.mocked(inferencesApi.getInferenceForEntity)
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({
        entity_id: "entity-2",
        role_inferences: [],
      } as any)
      .mockResolvedValueOnce({
        entity_id: "entity-1",
        role_inferences: [
          {
            role_type: "agent",
            score: 0.7,
            confidence: 0.9,
            disagreement: 0.1,
            coverage: 2,
          },
        ],
      } as any);

    renderView();

    expect(await screen.findByText(/Some entities could not load inferences/i)).toBeInTheDocument();
    expect(screen.getByText("aspirin: Failed to load inferences")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(() => {
      expect(screen.getByText("agent")).toBeInTheDocument();
    });

    expect(inferencesApi.getInferenceForEntity).toHaveBeenCalledTimes(3);
  });
});
