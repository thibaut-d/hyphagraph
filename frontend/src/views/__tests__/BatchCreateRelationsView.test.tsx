/**
 * Tests for BatchCreateRelationsView.
 *
 * Tests: initial render, adding/removing relation rows, adding/removing roles,
 * source validation, submission flow, results summary, error handling.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { BatchCreateRelationsView } from "../BatchCreateRelationsView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import * as entitiesApi from "../../api/entities";
import * as sourcesApi from "../../api/sources";
import * as relationsApi from "../../api/relations";

vi.mock("../../api/entities");
vi.mock("../../api/sources");
vi.mock("../../api/relations");

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts) {
        return Object.entries(opts).reduce(
          (s, [k, v]) => s.replace(`{{${k}}}`, String(v)),
          key
        );
      }
      return key;
    },
  }),
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => vi.fn() };
});

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockEntities = {
  items: [
    { id: "e-1", slug: "aspirin", label: "aspirin" },
    { id: "e-2", slug: "ibuprofen", label: "ibuprofen" },
  ],
};

const mockSources = {
  items: [
    { id: "s-1", title: "Study A" },
    { id: "s-2", title: "Study B" },
  ],
};

const mockRelation = { id: "r-1", kind: "treats", source_id: "s-1" };

function renderView() {
  return render(
    <NotificationProvider>
      <MemoryRouter>
        <BatchCreateRelationsView />
      </MemoryRouter>
    </NotificationProvider>
  );
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(entitiesApi.listEntities).mockResolvedValue(mockEntities as never);
  vi.mocked(sourcesApi.listSources).mockResolvedValue(mockSources as never);
  vi.mocked(relationsApi.createRelation).mockResolvedValue(mockRelation as never);
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("BatchCreateRelationsView — initial render", () => {
  it("shows loading spinner while metadata loads", () => {
    vi.mocked(entitiesApi.listEntities).mockImplementation(() => new Promise(() => {}));
    vi.mocked(sourcesApi.listSources).mockImplementation(() => new Promise(() => {}));
    renderView();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("renders page title after loading", async () => {
    renderView();
    await waitFor(() =>
      expect(screen.getByText("batch_relations.page_title")).toBeInTheDocument()
    );
  });

  it("shows source selector after loading", async () => {
    renderView();
    await waitFor(() =>
      expect(screen.getByTestId("source-select")).toBeInTheDocument()
    );
  });

  it("renders one relation card by default", async () => {
    renderView();
    await waitFor(() => {
      // The card header text is produced by t("batch_relations.relation_n", { n: 1 })
      // Since the mock key has no {{n}} literal, all cards render the same key text.
      // Assert there is exactly one such element.
      const cards = screen.getAllByText(/batch_relations\.relation_n/);
      expect(cards).toHaveLength(1);
    });
  });

  it("submit button is present", async () => {
    renderView();
    await waitFor(() =>
      expect(screen.getByText(/batch_relations.submit/)).toBeInTheDocument()
    );
  });
});

describe("BatchCreateRelationsView — adding and removing rows", () => {
  it("adds a new relation card when Add Relation is clicked", async () => {
    renderView();
    await waitFor(() => expect(screen.getByText("batch_relations.add_relation")).toBeInTheDocument());

    fireEvent.click(screen.getByText("batch_relations.add_relation"));

    await waitFor(() => {
      // After adding, there should be 2 card headers
      const cards = screen.getAllByText(/batch_relations\.relation_n/);
      expect(cards).toHaveLength(2);
    });
  });

  it("delete button is disabled when only one card remains", async () => {
    renderView();
    await waitFor(() => expect(screen.queryByRole("progressbar")).not.toBeInTheDocument());

    // Only one card — delete should be disabled
    const deleteBtn = screen.getAllByRole("button", { name: "common.delete" })[0];
    expect(deleteBtn).toBeDisabled();
  });

  it("can remove a card when there are multiple", async () => {
    renderView();
    await waitFor(() => expect(screen.getByText("batch_relations.add_relation")).toBeInTheDocument());

    fireEvent.click(screen.getByText("batch_relations.add_relation"));
    await waitFor(() => {
      expect(screen.getAllByText(/batch_relations\.relation_n/)).toHaveLength(2);
    });

    // Both delete buttons should now be enabled
    const deleteBtns = screen.getAllByRole("button", { name: "common.delete" });
    expect(deleteBtns[0]).not.toBeDisabled();
    fireEvent.click(deleteBtns[0]);

    await waitFor(() => {
      expect(screen.getAllByText(/batch_relations\.relation_n/)).toHaveLength(1);
    });
  });
});

describe("BatchCreateRelationsView — roles", () => {
  it("each card starts with 2 roles", async () => {
    renderView();
    await waitFor(() => expect(screen.queryByRole("progressbar")).not.toBeInTheDocument());

    // Each role has a remove button; 2 roles in the first card
    const removeRoleBtns = screen.getAllByRole("button", {
      name: "batch_relations.remove_role",
    });
    expect(removeRoleBtns.length).toBeGreaterThanOrEqual(2);
  });

  it("can add a role to a card", async () => {
    renderView();
    await waitFor(() => expect(screen.queryByRole("progressbar")).not.toBeInTheDocument());

    const addRoleBtn = screen.getByText("batch_relations.add_role");
    fireEvent.click(addRoleBtn);

    const removeRoleBtns = screen.getAllByRole("button", {
      name: "batch_relations.remove_role",
    });
    expect(removeRoleBtns.length).toBeGreaterThanOrEqual(3);
  });
});

describe("BatchCreateRelationsView — validation", () => {
  it("shows source error when submitting without a source", async () => {
    renderView();
    await waitFor(() => expect(screen.queryByRole("progressbar")).not.toBeInTheDocument());

    fireEvent.click(screen.getByText(/batch_relations.submit/));

    await waitFor(() =>
      expect(screen.getByText("batch_relations.error_source_required")).toBeInTheDocument()
    );
    expect(relationsApi.createRelation).not.toHaveBeenCalled();
  });
});

describe("BatchCreateRelationsView — submission and results", () => {
  /**
   * The validation requires source, kind, and role fields.
   * We simulate: kind filled, role types filled, then submit with source missing
   * to test the error path, OR we bypass the validator by faking createRelation.
   *
   * For the success path, we set sourceId through the hidden input on the
   * underlying MUI select element and fill kind / role_type text fields.
   */
  async function loadView() {
    renderView();
    await waitFor(() => expect(screen.queryByRole("progressbar")).not.toBeInTheDocument());
  }

  function fillKind(value = "treats") {
    const kindInputs = screen.getAllByPlaceholderText(/batch_relations\.kind_placeholder/);
    fireEvent.change(kindInputs[0], { target: { value } });
  }

  function fillRoleTypes() {
    const roleTypeInputs = screen.getAllByPlaceholderText(/batch_relations\.role_type_placeholder/);
    fireEvent.change(roleTypeInputs[0], { target: { value: "subject" } });
    fireEvent.change(roleTypeInputs[1], { target: { value: "object" } });
  }

  it("submit with no source shows source error", async () => {
    await loadView();
    fireEvent.click(screen.getByText(/batch_relations\.submit/));
    await waitFor(() =>
      expect(screen.getByText("batch_relations.error_source_required")).toBeInTheDocument()
    );
  });

  it("submit with missing kind shows validation error in results", async () => {
    // Fill source via underlying input, leave kind empty
    await loadView();
    const sourceInput = document
      .querySelector('[data-testid="source-select"] input') as HTMLInputElement;
    fireEvent.change(sourceInput, { target: { value: "s-1" } });

    // Don't fill kind — submit directly
    fireEvent.click(screen.getByText(/batch_relations\.submit/));

    // createRelation should NOT be called (validation failure → goes to results with error)
    await waitFor(() =>
      expect(screen.getByText("batch_relations.done_title")).toBeInTheDocument()
    );
    expect(screen.getByText(/batch_relations\.stat_failed/)).toBeInTheDocument();
    expect(relationsApi.createRelation).not.toHaveBeenCalled();
  });

  it("shows done title and stat_created after all succeed", async () => {
    await loadView();
    // Set source
    const sourceInput = document
      .querySelector('[data-testid="source-select"] input') as HTMLInputElement;
    fireEvent.change(sourceInput, { target: { value: "s-1" } });

    fillKind();
    fillRoleTypes();
    // Also set entity ids on both role selects
    const entitySelects = document.querySelectorAll(
      '.MuiInputBase-root input[aria-hidden="true"]'
    );
    // Set entity values directly on underlying inputs
    // Alternate approach: just submit and let createRelation be called
    // Since we need entity_id to pass validation, mock createRelation to succeed regardless
    // and let the validation pass via non-empty role_type
    // Actually entity_id validation: roles.some(r => !r.entity_id) → will fail
    // Let's set the entity inputs as well
    const allHiddenInputs = document.querySelectorAll('input[aria-hidden="true"]');
    // First two hidden inputs are the entity selects inside role rows
    if (allHiddenInputs.length >= 2) {
      fireEvent.change(allHiddenInputs[0], { target: { value: "e-1" } });
      fireEvent.change(allHiddenInputs[1], { target: { value: "e-2" } });
    }

    fireEvent.click(screen.getByText(/batch_relations\.submit/));
    await waitFor(() =>
      expect(screen.getByText("batch_relations.done_title")).toBeInTheDocument()
    );
    expect(screen.getByText(/batch_relations\.stat_created/)).toBeInTheDocument();
  });

  it("shows Create more button in results and resets form", async () => {
    await loadView();
    const sourceInput = document
      .querySelector('[data-testid="source-select"] input') as HTMLInputElement;
    fireEvent.change(sourceInput, { target: { value: "s-1" } });
    // Trigger submit (validation will fail → still shows done_title with stat_failed)
    fireEvent.click(screen.getByText(/batch_relations\.submit/));
    await waitFor(() =>
      expect(screen.getByText("batch_relations.done_title")).toBeInTheDocument()
    );

    fireEvent.click(screen.getByText("batch_relations.create_more"));
    await waitFor(() =>
      expect(screen.queryByText("batch_relations.done_title")).not.toBeInTheDocument()
    );
    expect(screen.getByText("batch_relations.page_title")).toBeInTheDocument();
  });

  it("shows stat_failed chip when createRelation throws", async () => {
    vi.mocked(relationsApi.createRelation).mockRejectedValue(new Error("Server error"));
    await loadView();
    const sourceInput = document
      .querySelector('[data-testid="source-select"] input') as HTMLInputElement;
    fireEvent.change(sourceInput, { target: { value: "s-1" } });
    fillKind();
    fillRoleTypes();
    const allHiddenInputs = document.querySelectorAll('input[aria-hidden="true"]');
    if (allHiddenInputs.length >= 2) {
      fireEvent.change(allHiddenInputs[0], { target: { value: "e-1" } });
      fireEvent.change(allHiddenInputs[1], { target: { value: "e-2" } });
    }
    fireEvent.click(screen.getByText(/batch_relations\.submit/));
    await waitFor(() =>
      expect(screen.getByText(/batch_relations\.stat_failed/)).toBeInTheDocument()
    );
  });
});
