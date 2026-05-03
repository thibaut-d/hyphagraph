import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import { apiFetch } from "../../api/client";
import { NotificationProvider } from "../../notifications/NotificationContext";
import { AdminView } from "../AdminView";

vi.mock("../../api/client", () => ({
  apiFetch: vi.fn(),
}));

function renderView() {
  return render(
    <NotificationProvider>
      <AdminView />
    </NotificationProvider>,
  );
}

describe("AdminView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiFetch).mockImplementation((path: string, options?: RequestInit) => {
      if (path === "/admin/stats") {
        return Promise.resolve({
          total_users: 1,
          active_users: 1,
          superusers: 1,
          verified_users: 1,
        });
      }
      if (path === "/admin/users") {
        return Promise.resolve([]);
      }
      if (path.startsWith("/entities/merge-candidates")) {
        return Promise.resolve([
          {
            source: {
              id: "entity-source",
              slug: "fibromyalgia-syndrome",
              summary: { en: "Duplicate label" },
            },
            target: {
              id: "entity-target",
              slug: "fibromyalgia",
              summary: { en: "Canonical label" },
            },
            similarity: 0.91,
            reason: "One slug contains the other",
            score_factors: {
              slug_similarity: 0.91,
              contains_slug: true,
              same_ui_category: false,
            },
            proposed_action: "merge",
          },
        ]);
      }
      if (path.startsWith("/admin/graph-cleaning/analysis")) {
        return Promise.resolve({
          duplicate_relations: [
            {
              fingerprint: "duplicate-group",
              reason: "Same source, relation type, direction, scope, and role participants",
              relation_count: 2,
              source_title: "Duplicate relation study",
              relations: [
                {
                  relation_id: "relation-1",
                  source_title: "Duplicate relation study",
                  kind: "treats",
                  direction: "supports",
                  confidence: 0.8,
                  roles: [
                    { entity_id: "entity-a", entity_slug: "duloxetine", role_type: "agent" },
                    { entity_id: "entity-b", entity_slug: "fibromyalgia", role_type: "target" },
                  ],
                },
                {
                  relation_id: "relation-2",
                  source_title: "Duplicate relation study",
                  kind: "treats",
                  direction: "supports",
                  confidence: 0.8,
                  roles: [
                    { entity_id: "entity-a", entity_slug: "duloxetine", role_type: "agent" },
                    { entity_id: "entity-b", entity_slug: "fibromyalgia", role_type: "target" },
                  ],
                },
              ],
            },
          ],
          role_consistency: [
            {
              entity_id: "entity-b",
              entity_slug: "fibromyalgia",
              relation_kind: "associated_with",
              reason: "Entity appears with multiple role types for the same relation kind",
              usages: [
                { role_type: "condition", count: 1, relation_ids: ["relation-2"] },
                { role_type: "target", count: 1, relation_ids: ["relation-3"] },
              ],
            },
          ],
        });
      }
      if (path === "/admin/graph-cleaning/critique") {
        const payload = JSON.parse(String(options?.body ?? "{}"));
        const fingerprint = payload.candidates?.[0]?.candidate_fingerprint ?? "duplicate-group";
        return Promise.resolve({
          model: "test-model",
          items: [
            {
              candidate_fingerprint: fingerprint,
              recommendation: "recommend",
              rationale: `LLM report for ${fingerprint}.`,
              risks: ["false positive"],
              evidence_gaps: ["source context"],
            },
          ],
        });
      }
      if (path === "/admin/graph-cleaning/decisions") {
        return Promise.resolve([]);
      }
      return Promise.resolve([]);
    });
  });

  it("shows graph cleaning candidates and keeps merge actions review-gated", async () => {
    renderView();

    expect(await screen.findByRole("heading", { name: "Administration Panel" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /Graph Cleaning/i }));

    expect(await screen.findByRole("heading", { name: "Graph Cleaning" })).toBeInTheDocument();
    expect(screen.getByText(/No candidate scan has been run for this session/)).toBeInTheDocument();
    expect(vi.mocked(apiFetch).mock.calls.some(([path]) =>
      String(path).startsWith("/admin/graph-cleaning/analysis")
    )).toBe(false);
    expect(vi.mocked(apiFetch).mock.calls.some(([path]) =>
      String(path).startsWith("/entities/merge-candidates")
    )).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Scan" }));
    expect(await screen.findByText("fibromyalgia-syndrome")).toBeInTheDocument();
    expect(screen.getAllByText("fibromyalgia").length).toBeGreaterThan(0);
    expect(screen.getByText("One slug contains the other")).toBeInTheDocument();
    expect(screen.getByText(/slug_similarity=0.91/)).toBeInTheDocument();
    expect(screen.getByText(/LLM critical analysis should challenge these candidates/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Duplicate Relation Review" })).toBeInTheDocument();
    expect(screen.getByText("Duplicate relation study")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Role Consistency Review" })).toBeInTheDocument();
    expect(screen.getByText("associated_with")).toBeInTheDocument();
    expect(screen.getByLabelText("Status")).toBeInTheDocument();
    expect(screen.getByLabelText("Type")).toBeInTheDocument();
    expect(screen.getByLabelText("LLM recommendation")).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByLabelText("Type"));
    fireEvent.click(await screen.findByRole("option", { name: "Duplicate relations" }));
    await waitFor(() => {
      expect(screen.queryByText("fibromyalgia-syndrome")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Duplicate relation study")).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByLabelText("Type"));
    fireEvent.click(await screen.findByRole("option", { name: "All types" }));
    expect(await screen.findByText("fibromyalgia-syndrome")).toBeInTheDocument();

    expect(screen.getByText("LLM critiques: 0/3")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Critique next batch" }));
    expect(await screen.findByText(/LLM: recommend/)).toBeInTheDocument();
    expect(screen.getByText("LLM critiques: 1/3")).toBeInTheDocument();
    expect(screen.getAllByText(/LLM report for entity-source:entity-target/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Risks: false positive/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence gaps: source context/)).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText("LLM recommendation"));
    fireEvent.click(await screen.findByRole("option", { name: "Recommend" }));
    expect(await screen.findByText("fibromyalgia-syndrome")).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByLabelText("LLM recommendation"));
    fireEvent.click(await screen.findByRole("option", { name: "All recommendations" }));
    expect(await screen.findByText("fibromyalgia-syndrome")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "LLM review" })[1]);
    expect(await screen.findByText(/LLM report for duplicate-group/)).toBeInTheDocument();
    expect(screen.getByText("LLM critiques: 2/3")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Mark duplicates" }));
    expect(await screen.findByRole("heading", { name: "Mark Duplicate Relations" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Mark Duplicate Relations" })).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Correct role" }));
    expect(await screen.findByRole("heading", { name: "Correct Relation Role" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Correct Relation Role" })).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Review merge/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Confirm Entity Merge" })).toBeInTheDocument();
    });
    expect(screen.getAllByText(/fibromyalgia-syndrome/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/fibromyalgia/).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Confirm Entity Merge" })).not.toBeInTheDocument();
    });

    const scanCallCountBeforeDismiss = vi.mocked(apiFetch).mock.calls.filter(([path]) =>
      String(path).startsWith("/admin/graph-cleaning/analysis") ||
      String(path).startsWith("/entities/merge-candidates")
    ).length;
    let dismissed = false;
    vi.mocked(apiFetch).mockImplementation((path: string, options?: RequestInit) => {
      if (path === "/admin/graph-cleaning/decisions" && options?.method === "POST") {
        dismissed = true;
        return Promise.resolve({});
      }
      if (path === "/admin/graph-cleaning/decisions") {
        return Promise.resolve(
          dismissed
            ? [
                {
                  id: "decision-1",
                  candidate_type: "entity_merge",
                  candidate_fingerprint: "entity-source:entity-target",
                  status: "dismissed",
                  notes: "Dismissed from graph-cleaning UI.",
                  decision_payload: null,
                  action_result: null,
                  reviewed_by_user_id: "admin",
                  created_at: "2026-05-03T00:00:00Z",
                  updated_at: "2026-05-03T00:00:00Z",
                },
              ]
            : [],
        );
      }
      return Promise.resolve([]);
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Dismiss" })[0]);
    await waitFor(() => {
      expect(vi.mocked(apiFetch).mock.calls.filter(([path]) =>
        String(path).startsWith("/admin/graph-cleaning/analysis") ||
        String(path).startsWith("/entities/merge-candidates")
      ).length).toBe(scanCallCountBeforeDismiss);
    });
    await waitFor(() => {
      expect(screen.queryByText("fibromyalgia-syndrome")).not.toBeInTheDocument();
    });
  }, 30000);

  it("keeps graph-cleaning action dialogs disabled until required fields are valid", async () => {
    renderView();

    fireEvent.click(await screen.findByRole("tab", { name: /Graph Cleaning/i }));
    expect(await screen.findByRole("heading", { name: "Graph Cleaning" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Scan" }));
    expect(await screen.findByText("fibromyalgia-syndrome")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Mark duplicates" }));
    const duplicateDialog = await screen.findByRole("dialog", { name: "Mark Duplicate Relations" });
    const duplicateSubmit = within(duplicateDialog).getByRole("button", { name: "Mark duplicates" });
    expect(duplicateSubmit).toBeDisabled();

    fireEvent.change(within(duplicateDialog).getByLabelText(/Rationale/), {
      target: { value: "ok" },
    });
    expect(duplicateSubmit).toBeDisabled();

    fireEvent.change(within(duplicateDialog).getByLabelText(/Rationale/), {
      target: { value: "Duplicate evidence context confirmed." },
    });
    expect(duplicateSubmit).toBeEnabled();

    fireEvent.click(within(duplicateDialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Mark Duplicate Relations" })).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Correct role" }));
    const roleDialog = await screen.findByRole("dialog", { name: "Correct Relation Role" });
    const roleSubmit = within(roleDialog).getByRole("button", { name: "Create revision" });
    expect(roleSubmit).toBeDisabled();

    fireEvent.change(within(roleDialog).getByLabelText(/Correct role type/), {
      target: { value: "target" },
    });
    expect(roleSubmit).toBeDisabled();

    fireEvent.change(within(roleDialog).getByLabelText(/Rationale/), {
      target: { value: "Role matches the source statement." },
    });
    expect(roleSubmit).toBeEnabled();
  });
});
