import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EntityDetailFilters, EntityDetailFilterValues } from "../EntityDetailFilters";
import { SourceRead } from "../../../types/source";

// Mock i18n
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue: string) => defaultValue,
  }),
}));

describe("EntityDetailFilters", () => {
  const mockOnFilterChange = vi.fn();

  const createMockSource = (overrides?: Partial<SourceRead>): SourceRead => ({
    id: "source-1",
    kind: "study",
    title: "Test Source",
    year: 2020,
    origin: "Journal",
    url: "https://example.com",
    trust_level: 0.8,
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Direction filter", () => {
    it("renders evidence direction filter section", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [createMockSource()];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      expect(screen.getByText("Evidence Direction")).toBeInTheDocument();
    });

    it("displays all direction options", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [createMockSource()];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      expect(screen.getByText("Supports")).toBeInTheDocument();
      expect(screen.getByText("Contradicts")).toBeInTheDocument();
      expect(screen.getByText("Neutral")).toBeInTheDocument();
      expect(screen.getByText("Mixed")).toBeInTheDocument();
    });

    it("calls onFilterChange when direction is selected", async () => {
      const user = userEvent.setup();
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [createMockSource()];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      const supportsCheckbox = screen.getByLabelText("Supports");
      await user.click(supportsCheckbox);

      expect(mockOnFilterChange).toHaveBeenCalledWith("directions", ["positive"]);
    });

    it("shows selected directions as checked", () => {
      const filters: EntityDetailFilterValues = {
        directions: ["positive", "negative"],
      };
      const sources: SourceRead[] = [createMockSource()];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      expect(screen.getByLabelText("Supports")).toBeChecked();
      expect(screen.getByLabelText("Contradicts")).toBeChecked();
      expect(screen.getByLabelText("Neutral")).not.toBeChecked();
      expect(screen.getByLabelText("Mixed")).not.toBeChecked();
    });
  });

  describe("Study type filter", () => {
    it("renders study type filter section", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [createMockSource({ kind: "clinical_trial" })];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      expect(screen.getByText("Study Type")).toBeInTheDocument();
    });

    it("extracts unique study types from sources", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [
        createMockSource({ id: "1", kind: "clinical_trial" }),
        createMockSource({ id: "2", kind: "meta_analysis" }),
        createMockSource({ id: "3", kind: "clinical_trial" }), // Duplicate
      ];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      expect(screen.getByText("clinical_trial")).toBeInTheDocument();
      expect(screen.getByText("meta_analysis")).toBeInTheDocument();
    });

    it("does not render study type filter when no sources", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      expect(screen.queryByText("Study Type")).not.toBeInTheDocument();
    });

    it("calls onFilterChange when study type is selected", async () => {
      const user = userEvent.setup();
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [createMockSource({ kind: "clinical_trial" })];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      const checkbox = screen.getByLabelText("clinical_trial");
      await user.click(checkbox);

      expect(mockOnFilterChange).toHaveBeenCalledWith("kinds", ["clinical_trial"]);
    });

    it("shows selected study types as checked", () => {
      const filters: EntityDetailFilterValues = {
        kinds: ["clinical_trial"],
      };
      const sources: SourceRead[] = [
        createMockSource({ id: "1", kind: "clinical_trial" }),
        createMockSource({ id: "2", kind: "meta_analysis" }),
      ];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      expect(screen.getByLabelText("clinical_trial")).toBeChecked();
      expect(screen.getByLabelText("meta_analysis")).not.toBeChecked();
    });

    it("sorts study types alphabetically", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [
        createMockSource({ id: "1", kind: "zebra_study" }),
        createMockSource({ id: "2", kind: "alpha_study" }),
        createMockSource({ id: "3", kind: "meta_analysis" }),
      ];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      const checkboxes = screen.getAllByRole("checkbox", { name: /study/i });
      const labels = checkboxes.map((cb) => cb.getAttribute("aria-label"));

      // Should be alphabetically sorted
      expect(labels).toEqual(["alpha_study", "meta_analysis", "zebra_study"]);
    });
  });

  describe("Publication year filter", () => {
    it("renders publication year filter section", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [createMockSource({ year: 2020 })];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      expect(screen.getByText("Publication Year")).toBeInTheDocument();
    });

    it("calculates year range from sources", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [
        createMockSource({ id: "1", year: 2010 }),
        createMockSource({ id: "2", year: 2020 }),
        createMockSource({ id: "3", year: 2015 }),
      ];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      // RangeFilter should be rendered with min=2010, max=2020
      expect(screen.getByText("Publication Year")).toBeInTheDocument();
      // The range filter displays the range values
      expect(screen.getByText("2010")).toBeInTheDocument();
      expect(screen.getByText("2020")).toBeInTheDocument();
    });

    it("does not render year filter when no sources", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      expect(screen.queryByText("Publication Year")).not.toBeInTheDocument();
    });

    it("uses filter value when provided", () => {
      const filters: EntityDetailFilterValues = {
        yearRange: [2012, 2018],
      };
      const sources: SourceRead[] = [
        createMockSource({ id: "1", year: 2010 }),
        createMockSource({ id: "2", year: 2020 }),
      ];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      // Should display the filtered range, not the full range
      expect(screen.getByText("2012")).toBeInTheDocument();
      expect(screen.getByText("2018")).toBeInTheDocument();
    });
  });

  describe("Minimum authority filter", () => {
    it("always renders minimum authority filter", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      expect(screen.getByText("Minimum Authority Score")).toBeInTheDocument();
    });

    it("defaults to 0 when no filter value", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [createMockSource()];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      // Should display range from 0 to 1
      expect(screen.getByText("0.0")).toBeInTheDocument();
      expect(screen.getByText("1.0")).toBeInTheDocument();
    });

    it("uses filter value when provided", () => {
      const filters: EntityDetailFilterValues = {
        minTrustLevel: 0.5,
      };
      const sources: SourceRead[] = [createMockSource()];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      // Should display 0.5 as the minimum
      expect(screen.getByText("0.5")).toBeInTheDocument();
    });
  });

  describe("Filter updates", () => {
    it("updates options when sources change", () => {
      const filters: EntityDetailFilterValues = {};
      const { rerender } = render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={[createMockSource({ kind: "study_a" })]}
        />
      );

      expect(screen.getByText("study_a")).toBeInTheDocument();
      expect(screen.queryByText("study_b")).not.toBeInTheDocument();

      // Update sources
      rerender(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={[
            createMockSource({ id: "1", kind: "study_a" }),
            createMockSource({ id: "2", kind: "study_b" }),
          ]}
        />
      );

      expect(screen.getByText("study_a")).toBeInTheDocument();
      expect(screen.getByText("study_b")).toBeInTheDocument();
    });

    it("recalculates year range when sources change", () => {
      const filters: EntityDetailFilterValues = {};
      const { rerender } = render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={[createMockSource({ year: 2015 })]}
        />
      );

      expect(screen.getByText("2015")).toBeInTheDocument();

      // Update with wider year range
      rerender(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={[
            createMockSource({ id: "1", year: 2010 }),
            createMockSource({ id: "2", year: 2020 }),
          ]}
        />
      );

      expect(screen.getByText("2010")).toBeInTheDocument();
      expect(screen.getByText("2020")).toBeInTheDocument();
    });
  });

  describe("Edge cases", () => {
    it("handles sources with null years gracefully", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [
        createMockSource({ id: "1", year: 2020 }),
        { ...createMockSource({ id: "2" }), year: null as unknown as number },
        createMockSource({ id: "3", year: 2015 }),
      ];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      // Should only use non-null years
      expect(screen.getByText("2015")).toBeInTheDocument();
      expect(screen.getByText("2020")).toBeInTheDocument();
    });

    it("handles empty study types gracefully", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [
        createMockSource({ id: "1", kind: "valid_study" }),
        createMockSource({ id: "2", kind: "" }),
        createMockSource({ id: "3", kind: "another_study" }),
      ];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      // Should filter out empty kinds
      expect(screen.getByText("valid_study")).toBeInTheDocument();
      expect(screen.getByText("another_study")).toBeInTheDocument();
      expect(screen.queryByLabelText("")).not.toBeInTheDocument();
    });

    it("handles single year source", () => {
      const filters: EntityDetailFilterValues = {};
      const sources: SourceRead[] = [createMockSource({ year: 2020 })];

      render(
        <EntityDetailFilters
          filters={filters}
          onFilterChange={mockOnFilterChange}
          sources={sources}
        />
      );

      // Should create range [2020, 2020]
      expect(screen.getByText("Publication Year")).toBeInTheDocument();
      expect(screen.getByText("2020")).toBeInTheDocument();
    });
  });
});
