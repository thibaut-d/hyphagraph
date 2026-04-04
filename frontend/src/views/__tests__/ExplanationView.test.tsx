import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ExplanationView } from "../ExplanationView";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (
      key: string,
      defaultValueOrOptions?: string | { defaultValue?: string },
    ) => {
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      return defaultValueOrOptions?.defaultValue || key;
    },
  }),
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

describe("ExplanationView", () => {
  it("redirects the legacy explain route to the canonical property detail route", async () => {
    render(
      <MemoryRouter initialEntries={["/explain/entity-123/therapeutic_use"]}>
        <Routes>
          <Route path="/explain/:entityId/:roleType" element={<ExplanationView />} />
          <Route
            path="/entities/:id/properties/:roleType"
            element={<div>Canonical property detail page</div>}
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Canonical property detail page")).toBeInTheDocument();
  });

  it("shows an error when required route params are missing", () => {
    render(
      <MemoryRouter initialEntries={["/explain"]}>
        <Routes>
          <Route path="/explain" element={<ExplanationView />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("An error occurred");
  });
});
