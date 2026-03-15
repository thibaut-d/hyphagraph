import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("../../api/export", () => ({
  downloadExportFile: vi.fn(),
}));

vi.mock("../../notifications/NotificationContext", () => ({
  useNotification: () => ({
    showError: vi.fn(),
  }),
}));

import { downloadExportFile } from "../../api/export";
import { ExportMenu } from "../ExportMenu";

describe("ExportMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("delegates export download to the shared export api helper", async () => {
    (downloadExportFile as any).mockResolvedValue("entities.json");
    const onExport = vi.fn();

    render(<ExportMenu exportType="entities" onExport={onExport} />);

    fireEvent.click(screen.getByRole("button", { name: /export/i }));
    fireEvent.click(screen.getByText("Export as JSON"));

    await waitFor(() => {
      expect(downloadExportFile).toHaveBeenCalledWith("entities", "json");
      expect(onExport).toHaveBeenCalledWith("json");
    });
  });
});
