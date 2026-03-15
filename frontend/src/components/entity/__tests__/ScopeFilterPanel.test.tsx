import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ScopeFilterPanel } from "../ScopeFilterPanel";

const translate = (
  key: string,
  defaultValueOrOptions?: string | { defaultValue?: string },
  interpolation?: { count?: number },
) => {
  if (typeof defaultValueOrOptions === "string") {
    if (key === "scope_filter.active_count") {
      return ` (${interpolation?.count ?? 0} active)`;
    }
    return defaultValueOrOptions;
  }
  return defaultValueOrOptions?.defaultValue || key;
};

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: translate,
  }),
}));

describe("ScopeFilterPanel", () => {
  it("renders active filters and delegates filter actions", () => {
    const onKeyChange = vi.fn();
    const onValueChange = vi.fn();
    const onAddFilter = vi.fn();
    const onRemoveFilter = vi.fn();
    const onClearFilters = vi.fn();

    render(
      <ScopeFilterPanel
        scopeFilter={{ population: "adults", dosage: "low" }}
        newFilterKey=""
        newFilterValue=""
        onKeyChange={onKeyChange}
        onValueChange={onValueChange}
        onAddFilter={onAddFilter}
        onRemoveFilter={onRemoveFilter}
        onClearFilters={onClearFilters}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Scope Filter/ }));

    expect(screen.getByText("Scope Filter (2 active)")).toBeInTheDocument();
    expect(screen.getByText("population: adults")).toBeInTheDocument();
    expect(screen.getByText("dosage: low")).toBeInTheDocument();

    const populationChip = screen.getByText("population: adults").closest('[role="button"]');
    fireEvent.click(within(populationChip as HTMLElement).getByTestId("CancelIcon"));
    expect(onRemoveFilter).toHaveBeenCalledWith("population");

    expect(onClearFilters).not.toHaveBeenCalled();
  });

  it("enables add when both fields are populated and submits on button or Enter", () => {
    const onKeyChange = vi.fn();
    const onValueChange = vi.fn();
    const onAddFilter = vi.fn();

    render(
      <ScopeFilterPanel
        scopeFilter={{}}
        newFilterKey="population"
        newFilterValue="adults"
        onKeyChange={onKeyChange}
        onValueChange={onValueChange}
        onAddFilter={onAddFilter}
        onRemoveFilter={vi.fn()}
        onClearFilters={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Scope Filter/ }));

    const keyInput = screen.getByLabelText("Attribute");
    const valueInput = screen.getByLabelText("Value");
    const addButton = screen.getByRole("button", { name: "Add", hidden: true });

    fireEvent.change(keyInput, { target: { value: "condition" } });
    fireEvent.change(valueInput, { target: { value: "migraine" } });

    expect(onKeyChange).toHaveBeenCalledWith("condition");
    expect(onValueChange).toHaveBeenCalledWith("migraine");
    expect(addButton).toBeEnabled();

    fireEvent.click(addButton);
    fireEvent.keyPress(valueInput, { key: "Enter", code: "Enter", charCode: 13 });

    expect(onAddFilter).toHaveBeenCalledTimes(2);
  });

  it("disables add while either filter field is blank", () => {
    render(
      <ScopeFilterPanel
        scopeFilter={{}}
        newFilterKey="population"
        newFilterValue=" "
        onKeyChange={vi.fn()}
        onValueChange={vi.fn()}
        onAddFilter={vi.fn()}
        onRemoveFilter={vi.fn()}
        onClearFilters={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Scope Filter/ }));

    expect(screen.getByRole("button", { name: "Add", hidden: true })).toBeDisabled();
  });
});
