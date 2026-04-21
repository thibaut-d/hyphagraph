import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExtractionPreview } from "../ExtractionPreview";
import * as extractionApi from "../../api/extraction";
import type { DocumentExtractionPreview } from "../../types/extraction";

vi.mock("../../api/extraction");

vi.mock("react-i18next", () => ({
  initReactI18next: { type: "3rdParty", init: () => {} },
  useTranslation: () => ({
    t: (key: string, defaultValueOrOptions?: string | { defaultValue?: string }) => {
      const translations: Record<string, string> = {
        "extraction_preview.title": "Extraction Complete!",
        "extraction_preview.empty_msg":
          "Extraction finished, but no entities or relations were found in the selected text.",
        "extraction_preview.empty_title": "No extractable knowledge found",
        "extraction_preview.empty_guidance":
          "The source text was stored for review, but the extraction worker did not return any graph items.",
        "extraction_preview.empty_action_guidance":
          "No entities or relations are available to save from this extraction.",
        "extraction_preview.high_confidence_bold": "High-confidence extraction detected.",
        "extraction_preview.high_confidence_rest":
          "All entities have exact or synonym matches. You can quick-save or review details below.",
        "extraction_preview.new_entities": "0 new entities",
        "extraction_preview.linked_entities": "0 linked entities",
        "extraction_preview.relations": "0 relations",
        "extraction_preview.entities_section": "Entities (0)",
        "extraction_preview.relations_section": "Relations (0)",
        "extraction_preview.quick_save": "Quick Save",
        "extraction_preview.save_to_graph": "Save to Graph",
        "extraction_preview.no_entities_alert":
          "No entities selected. Please select at least one entity to create or link before saving.",
        "extraction_preview.all_skipped":
          "All entities skipped. Adjust decisions above to enable saving.",
        "common.cancel": "Cancel",
      };

      if (translations[key]) {
        return translations[key];
      }
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      return defaultValueOrOptions?.defaultValue || key;
    },
    i18n: { language: "en" },
  }),
}));

const emptyPreview: DocumentExtractionPreview = {
  source_id: "source-1",
  entities: [],
  relations: [],
  entity_count: 0,
  relation_count: 0,
  link_suggestions: [],
  needs_review_count: 0,
  auto_verified_count: 0,
  avg_validation_score: null,
};

describe("ExtractionPreview", () => {
  it("shows an explicit empty state instead of high-confidence save messaging", () => {
    render(
      <ExtractionPreview
        preview={emptyPreview}
        onSaveComplete={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByText("No extractable knowledge found")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Extraction finished, but no entities or relations were found in the selected text.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No entities or relations are available to save from this extraction."),
    ).toBeInTheDocument();

    expect(screen.queryByText("High-confidence extraction detected.")).not.toBeInTheDocument();
    expect(screen.queryByText("Quick Save")).not.toBeInTheDocument();
    expect(screen.queryByText("Save to Graph")).not.toBeInTheDocument();
    expect(
      screen.queryByText("No entities selected. Please select at least one entity to create or link before saving."),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("All entities skipped. Adjust decisions above to enable saving."),
    ).not.toBeInTheDocument();
    expect(extractionApi.saveExtraction).not.toHaveBeenCalled();
  });
});
