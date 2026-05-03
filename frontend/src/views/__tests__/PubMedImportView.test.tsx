import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { PubMedImportView } from "../PubMedImportView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import * as pubmedApi from "../../api/pubmed";
import { ErrorCode } from "../../utils/errorHandler";

vi.mock("../../api/pubmed");
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

});
