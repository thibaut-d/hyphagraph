import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { PubMedImportView } from "../PubMedImportView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import * as pubmedApi from "../../api/pubmed";
import * as extractionApi from "../../api/extraction";
import * as jobsApi from "../../api/longRunningJobs";
import { ErrorCode } from "../../utils/errorHandler";

vi.mock("../../api/pubmed");
vi.mock("../../api/extraction");
vi.mock("../../api/longRunningJobs");
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, defaultValueOrOptions?: string | { defaultValue?: string }) => {
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      return defaultValueOrOptions?.defaultValue || key;
    },
  }),
  initReactI18next: { type: '3rdParty', init: () => {} },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

describe("PubMedImportView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the parsed backend search error", async () => {
    vi.spyOn(pubmedApi, "bulkSearchPubMed").mockRejectedValue({
      code: ErrorCode.RATE_LIMIT_EXCEEDED,
      message: "Too many requests. Please try again later.",
      details: "PubMed search rate limit hit",
    });

    render(
      <NotificationProvider>
        <MemoryRouter>
          <PubMedImportView />
        </MemoryRouter>
      </NotificationProvider>,
    );

    fireEvent.change(screen.getByLabelText(/search query or pubmed url/i), {
      target: { value: "aspirin" },
    });
    fireEvent.click(screen.getByRole("button", { name: /search pubmed/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Too many requests. Please try again later."),
      ).toBeInTheDocument();
    });
  });

  it("starts a bulk extraction job for imported studies", async () => {
    vi.spyOn(extractionApi, "startBulkSourceExtractionJob").mockResolvedValue({
      job_id: "job-1",
      status: "pending",
    });
    vi.spyOn(jobsApi, "getLongRunningJob").mockResolvedValue({
      id: "job-1",
      kind: "bulk_source_extraction",
      status: "succeeded",
      request_payload: {},
      result_payload: {
        search: "ketamine",
        study_budget: 5,
        matched_count: 5,
        selected_count: 5,
        extracted_count: 5,
        failed_count: 0,
        skipped_count: 0,
        results: [],
      },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

    render(
      <NotificationProvider>
        <MemoryRouter>
          <PubMedImportView />
        </MemoryRouter>
      </NotificationProvider>,
    );

    fireEvent.change(screen.getByLabelText(/search imported studies/i), {
      target: { value: "ketamine" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^bulk extract$/i }));

    await waitFor(() => {
      expect(extractionApi.startBulkSourceExtractionJob).toHaveBeenCalledWith({
        search: "ketamine",
        study_budget: 10,
      });
      expect(screen.getByText(/Matched 5 unextracted studies/i)).toBeInTheDocument();
    });
  });
});
