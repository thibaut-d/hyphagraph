import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { BulkSourceExtractionView } from "../BulkSourceExtractionView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import * as extractionApi from "../../api/extraction";
import * as jobsApi from "../../api/longRunningJobs";

vi.mock("../../api/extraction");
vi.mock("../../api/longRunningJobs");

describe("BulkSourceExtractionView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
        study_budget: 10,
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
          <BulkSourceExtractionView />
        </MemoryRouter>
      </NotificationProvider>,
    );

    fireEvent.change(screen.getByLabelText(/search imported studies/i), {
      target: { value: "ketamine" },
    });
    fireEvent.click(screen.getByRole("button", { name: /start bulk extraction/i }));

    await waitFor(() => {
      expect(extractionApi.startBulkSourceExtractionJob).toHaveBeenCalledWith({
        search: "ketamine",
        study_budget: 10,
      });
      expect(screen.getByText(/Matched 5 unextracted studies/i)).toBeInTheDocument();
    });
  });
});
