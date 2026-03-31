import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { ScopeFilterPanel } from "../ScopeFilterPanel";

const translate = (
  key: string,
  defaultValueOrOptions?: string | { defaultValue?: string; [key: string]: unknown },
) => {
  if (typeof defaultValueOrOptions === "string") {
    return defaultValueOrOptions;
  }
  if (defaultValueOrOptions && typeof defaultValueOrOptions === "object") {
    let result = defaultValueOrOptions.defaultValue || key;
    Object.entries(defaultValueOrOptions).forEach(([field, value]) => {
      if (field !== "defaultValue") {
        result = result.replace(`{{${field}}}`, String(value));
      }
    });
    return result;
  }
  return key;
};

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: translate,
  }),
}));

describe("ScopeFilterPanel", () => {
  it("renders active filters with human-readable labels and delegates removal", () => {
    const onRemoveFilter = vi.fn();

    render(
      <ScopeFilterPanel
        scopeFilter={{ population: "adults", dosage: "low" }}
        newFilterKey=""
        newFilterValue=""
        onKeyChange={vi.fn()}
        onValueChange={vi.fn()}
        onAddFilter={vi.fn()}
        onRemoveFilter={onRemoveFilter}
        onClearFilters={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /scope filter/i }));

    expect(screen.getByText("Scope Filter (2 active)")).toBeInTheDocument();
    expect(screen.getByText("Population: adults")).toBeInTheDocument();
    expect(screen.getByText("Dosage: low")).toBeInTheDocument();
    expect(screen.getByText(/Filters narrow the evidence included in the inference/i)).toBeInTheDocument();

    const populationChip = screen.getByText("Population: adults").closest('[role="button"]');
    fireEvent.click(within(populationChip as HTMLElement).getByTestId("CancelIcon"));

    expect(onRemoveFilter).toHaveBeenCalledWith("population");
  });

  it("offers guided dimensions and applies a preset dimension selection", () => {
    const onKeyChange = vi.fn();

    render(
      <ScopeFilterPanel
        scopeFilter={{}}
        newFilterKey=""
        newFilterValue=""
        onKeyChange={onKeyChange}
        onValueChange={vi.fn()}
        onAddFilter={vi.fn()}
        onRemoveFilter={vi.fn()}
        onClearFilters={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /scope filter/i }));

    expect(screen.getByText("Common dimensions")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Population: Adults" }));

    expect(onKeyChange).toHaveBeenCalledWith("population");
  });

  it("supports custom dimensions and enables add when both fields are populated", () => {
    const onAddFilter = vi.fn();

    function Harness() {
      const [key, setKey] = useState("");
      const [value, setValue] = useState("");

      return (
        <ScopeFilterPanel
          scopeFilter={{}}
          newFilterKey={key}
          newFilterValue={value}
          onKeyChange={setKey}
          onValueChange={setValue}
          onAddFilter={onAddFilter}
          onRemoveFilter={vi.fn()}
          onClearFilters={vi.fn()}
        />
      );
    }

    render(
      <Harness />,
    );

    fireEvent.click(screen.getByRole("button", { name: /scope filter/i }));
    fireEvent.mouseDown(screen.getByRole("combobox", { name: "Scope dimension" }));
    fireEvent.click(screen.getByRole("option", { name: "Custom dimension" }));

    const customKeyInput = screen.getByLabelText("Custom attribute");
    const valueInput = screen.getByLabelText("Value");
    const addButton = screen.getByRole("button", { name: "Apply scope filter" });

    fireEvent.change(customKeyInput, { target: { value: "disease_stage" } });
    fireEvent.change(valueInput, { target: { value: "stage ii" } });
    fireEvent.keyDown(valueInput, { key: "Enter", code: "Enter" });

    expect(addButton).toBeEnabled();
    expect(onAddFilter).toHaveBeenCalledTimes(1);
  });
});
