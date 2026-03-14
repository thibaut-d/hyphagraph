import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import {
  getSource,
  listRelationsBySource,
  mockSource,
  renderSourceDetailView,
} from "./SourceDetailView.test-support";

describe("SourceDetailView errors", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows API error when source loading fails", async () => {
    (getSource as any).mockRejectedValue({
      code: "SOURCE_NOT_FOUND",
      message: "Source not found",
      details: "Source with ID 123 does not exist",
    });
    (listRelationsBySource as any).mockResolvedValue([]);

    renderSourceDetailView("123e4567-e89b-12d3-a456-426614174000");

    await waitFor(() => {
      expect(screen.getByText("Source not found")).toBeInTheDocument();
    });
  });

  it("keeps source metadata visible when only relations loading fails", async () => {
    (getSource as any).mockResolvedValue(mockSource);
    (listRelationsBySource as any).mockRejectedValue({
      code: "RATE_LIMIT_EXCEEDED",
      message: "Too many requests. Please try again later.",
      details: "Relations endpoint rate limited",
    });

    renderSourceDetailView(mockSource.id);

    await waitFor(() => {
      expect(screen.getByText("Test Study on Aspirin")).toBeInTheDocument();
    });

    expect(screen.getAllByText("Too many requests. Please try again later.").length).toBeGreaterThan(0);
    expect(screen.queryByText(/no relations yet/i)).not.toBeInTheDocument();
  });
});
