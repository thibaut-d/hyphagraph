import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { BugReportDialog } from "../BugReportDialog";

vi.mock("../../auth/AuthContext", () => ({
  useAuthContext: () => ({ user: null }),
}));

vi.mock("../../api/bugReport", () => ({
  getCaptcha: vi.fn(),
  submitBugReport: vi.fn(),
}));

import { getCaptcha } from "../../api/bugReport";

describe("BugReportDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("clears stale captcha state when a reopened dialog fails to load a new challenge", async () => {
    vi.mocked(getCaptcha)
      .mockResolvedValueOnce({ token: "captcha-1", question: "1 + 1?" })
      .mockRejectedValueOnce(new Error("load failed"));

    const { rerender } = render(<BugReportDialog open={true} onClose={() => {}} />);

    expect(await screen.findByLabelText("1 + 1?")).toBeInTheDocument();

    rerender(<BugReportDialog open={false} onClose={() => {}} />);
    rerender(<BugReportDialog open={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(
        screen.getByText("Could not load CAPTCHA. Please try again.")
      ).toBeInTheDocument();
    });

    expect(screen.queryByLabelText("1 + 1?")).not.toBeInTheDocument();
    expect(screen.getByText("Loading CAPTCHA…")).toBeInTheDocument();
  });
});
