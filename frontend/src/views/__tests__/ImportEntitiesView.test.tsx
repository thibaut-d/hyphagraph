/**
 * Tests for ImportEntitiesView.
 *
 * Tests the three-stage import workflow:
 * Stage 1 (upload): format selector, file picker, format hints, preview button
 * Stage 2 (preview): per-row table, stats chips, confirm/cancel
 * Stage 3 (done): success summary, navigation options
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ImportEntitiesView } from "../ImportEntitiesView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import * as importApi from "../../api/import";

vi.mock("../../api/import");

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

const mockPreviewResult: importApi.ImportPreviewResult = {
  rows: [
    { row: 1, slug: "aspirin", summary_en: "A drug", status: "new", error: null },
    { row: 2, slug: "ibuprofen", summary_en: null, status: "duplicate", error: null },
    { row: 3, slug: "", summary_en: null, status: "invalid", error: "slug is required" },
  ],
  total: 3,
  new_count: 1,
  duplicate_count: 1,
  invalid_count: 1,
};

const mockImportResult: importApi.ImportResult = {
  created: 1,
  skipped_duplicates: 1,
  failed: 1,
  entity_ids: ["uuid-1"],
};

function makeFile(name = "entities.csv", content = "slug\naspirin"): File {
  return new File([content], name, { type: "text/csv" });
}

function renderView() {
  return render(
    <NotificationProvider>
      <MemoryRouter>
        <ImportEntitiesView />
      </MemoryRouter>
    </NotificationProvider>
  );
}

describe("ImportEntitiesView — Stage 1 (upload)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page title", () => {
    renderView();
    expect(screen.getByText("import.page_title")).toBeInTheDocument();
  });

  it("renders upload title and description", () => {
    renderView();
    expect(screen.getByText("import.upload_title")).toBeInTheDocument();
    expect(screen.getByText("import.upload_description")).toBeInTheDocument();
  });

  it("shows the CSV format hint by default", () => {
    renderView();
    expect(screen.getByText("import.csv_hint")).toBeInTheDocument();
  });

  it("switches to JSON hint when JSON toggle is clicked", () => {
    renderView();
    fireEvent.click(screen.getByText("JSON"));
    expect(screen.getByText("import.json_hint")).toBeInTheDocument();
  });

  it("preview button is disabled when no file is selected", () => {
    renderView();
    const btn = screen.getByText("import.preview_button").closest("button");
    expect(btn).toBeDisabled();
  });

  it("shows step indicator", () => {
    renderView();
    expect(screen.getByText(/import.step_upload/)).toBeInTheDocument();
    expect(screen.getByText(/import.step_preview/)).toBeInTheDocument();
    expect(screen.getByText(/import.step_done/)).toBeInTheDocument();
  });
});

describe("ImportEntitiesView — Stage 2 (preview)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(importApi.previewEntityImport).mockResolvedValue(mockPreviewResult);
  });

  async function goToPreview() {
    renderView();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile()] } });
    fireEvent.click(screen.getByText("import.preview_button"));
    await waitFor(() => expect(screen.getByText("aspirin")).toBeInTheDocument());
  }

  it("advances to preview stage after successful preview call", async () => {
    await goToPreview();
    expect(importApi.previewEntityImport).toHaveBeenCalledOnce();
  });

  it("shows new/duplicate/invalid stat chips", async () => {
    await goToPreview();
    // chips contain the translated key with count
    expect(screen.getByText(/import.stat_new/)).toBeInTheDocument();
    expect(screen.getByText(/import.stat_duplicate/)).toBeInTheDocument();
    expect(screen.getByText(/import.stat_invalid/)).toBeInTheDocument();
  });

  it("renders preview table rows", async () => {
    await goToPreview();
    expect(screen.getByText("aspirin")).toBeInTheDocument();
    expect(screen.getByText("ibuprofen")).toBeInTheDocument();
  });

  it("shows row status chips", async () => {
    await goToPreview();
    expect(screen.getByText("import.row_status_new")).toBeInTheDocument();
    expect(screen.getByText("import.row_status_duplicate")).toBeInTheDocument();
  });

  it("shows error text for invalid rows", async () => {
    await goToPreview();
    expect(screen.getByText("slug is required")).toBeInTheDocument();
  });

  it("cancel button returns to upload stage", async () => {
    await goToPreview();
    fireEvent.click(screen.getByText("common.cancel"));
    await waitFor(() => {
      expect(screen.getByText("import.upload_title")).toBeInTheDocument();
    });
  });

  it("confirm button is disabled when new_count is 0", async () => {
    vi.mocked(importApi.previewEntityImport).mockResolvedValue({
      ...mockPreviewResult,
      new_count: 0,
    });
    renderView();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile()] } });
    fireEvent.click(screen.getByText("import.preview_button"));
    await waitFor(() => expect(screen.getByText(/import.confirm_button/)).toBeInTheDocument());
    const confirmBtn = screen.getByText(/import.confirm_button/).closest("button");
    expect(confirmBtn).toBeDisabled();
  });
});

describe("ImportEntitiesView — Stage 3 (done)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(importApi.previewEntityImport).mockResolvedValue(mockPreviewResult);
    vi.mocked(importApi.executeEntityImport).mockResolvedValue(mockImportResult);
  });

  async function goToDone() {
    renderView();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile()] } });
    fireEvent.click(screen.getByText("import.preview_button"));
    await waitFor(() => expect(screen.getByText("aspirin")).toBeInTheDocument());
    fireEvent.click(screen.getByText(/import.confirm_button/));
    await waitFor(() => expect(screen.getByText("import.done_title")).toBeInTheDocument());
  }

  it("advances to done stage after successful import", async () => {
    await goToDone();
    expect(importApi.executeEntityImport).toHaveBeenCalledOnce();
  });

  it("shows created/skipped/failed chips", async () => {
    await goToDone();
    expect(screen.getByText(/import.stat_created/)).toBeInTheDocument();
    expect(screen.getByText(/import.stat_skipped/)).toBeInTheDocument();
    expect(screen.getByText(/import.stat_failed/)).toBeInTheDocument();
  });

  it("Import more button resets to upload stage", async () => {
    await goToDone();
    fireEvent.click(screen.getByText("import.import_more"));
    await waitFor(() => {
      expect(screen.getByText("import.upload_title")).toBeInTheDocument();
    });
  });

  it("Back to Entities link is present", async () => {
    await goToDone();
    expect(screen.getByText("import.back_to_entities")).toBeInTheDocument();
  });
});

describe("ImportEntitiesView — error handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows error alert when preview API call fails", async () => {
    vi.mocked(importApi.previewEntityImport).mockRejectedValue(
      new Error("Server error")
    );
    renderView();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile()] } });
    fireEvent.click(screen.getByText("import.preview_button"));
    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });
});
