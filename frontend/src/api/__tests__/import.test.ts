import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../client", () => ({
  apiFetchFormData: vi.fn(),
}));

import { apiFetchFormData } from "../client";
import {
  executeEntityImport,
  executeSourceImport,
  previewEntityImport,
  previewSourceImport,
} from "../import";

describe("import api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uses the multipart client for entity preview and execution", async () => {
    (apiFetchFormData as any).mockResolvedValue({ ok: true });

    const file = new File(["slug,summary_en\naspirin,Drug"], "entities.csv", { type: "text/csv" });

    await previewEntityImport(file, "csv");
    await executeEntityImport(file, "csv");

    expect(apiFetchFormData).toHaveBeenCalledTimes(2);
    expect((apiFetchFormData as any).mock.calls[0][0]).toBe("/import/entities/preview");
    expect((apiFetchFormData as any).mock.calls[0][1].body).toBeInstanceOf(FormData);
    expect((apiFetchFormData as any).mock.calls[1][0]).toBe("/import/entities");
    expect((apiFetchFormData as any).mock.calls[1][1].body).toBeInstanceOf(FormData);
  });

  it("uses the multipart client for source preview and execution", async () => {
    (apiFetchFormData as any).mockResolvedValue({ ok: true });

    const file = new File(["@article{key,title={Example}}"], "sources.bib", { type: "text/plain" });

    await previewSourceImport(file, "bibtex");
    await executeSourceImport(file, "bibtex");

    expect(apiFetchFormData).toHaveBeenCalledTimes(2);
    expect((apiFetchFormData as any).mock.calls[0][0]).toBe("/import/sources/preview");
    expect((apiFetchFormData as any).mock.calls[0][1].body).toBeInstanceOf(FormData);
    expect((apiFetchFormData as any).mock.calls[1][0]).toBe("/import/sources");
    expect((apiFetchFormData as any).mock.calls[1][1].body).toBeInstanceOf(FormData);
  });
});
