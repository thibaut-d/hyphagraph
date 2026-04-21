import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";

import { SourceExtractionSection } from "../SourceExtractionSection";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (
      _key: string,
      defaultValueOrOptions?: string | { defaultValue?: string },
      interpolation?: Record<string, string | number>,
    ) => {
      const value =
        typeof defaultValueOrOptions === "string"
          ? defaultValueOrOptions
          : defaultValueOrOptions?.defaultValue || _key;

      if (!interpolation) {
        return value;
      }

      return Object.entries(interpolation).reduce(
        (result, [token, replacement]) =>
          result.replaceAll(`{{${token}}}`, String(replacement)),
        value,
      );
    },
  }),
}));

function renderSection(overrides: Partial<ComponentProps<typeof SourceExtractionSection>> = {}) {
  const props: ComponentProps<typeof SourceExtractionSection> = {
    hasUrl: true,
    hasRelations: false,
    relationsCount: 0,
    relationsError: null,
    isHighQuality: true,
    autoExtracting: false,
    uploading: false,
    urlExtracting: false,
    uploadedFileName: null,
    saveResult: null,
    onClearSaveResult: vi.fn(),
    onAutoExtract: vi.fn(),
    onFileUpload: vi.fn(),
    onOpenUrlDialog: vi.fn(),
    onClearUploadedFile: vi.fn(),
    ...overrides,
  };

  render(<SourceExtractionSection {...props} />);

  return props;
}

describe("SourceExtractionSection", () => {
  it("calls the primary auto-extract handler when the source has a URL", async () => {
    const user = userEvent.setup();
    const onAutoExtract = vi.fn();

    renderSection({ onAutoExtract });

    await user.click(screen.getByRole("button", { name: "Auto-Extract Knowledge from URL" }));

    expect(onAutoExtract).toHaveBeenCalledTimes(1);
  });

  it("disables auto-extract while another extraction action is running", () => {
    renderSection({ autoExtracting: true });

    expect(screen.getByRole("button", { name: "Extracting knowledge..." })).toBeDisabled();
  });
});
