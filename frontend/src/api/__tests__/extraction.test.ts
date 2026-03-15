import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../client", () => ({
  apiFetch: vi.fn(),
  apiFetchFormData: vi.fn(),
}));

import { apiFetch, apiFetchFormData } from "../client";
import { extractFromDocument, extractFromUrl, saveExtraction, uploadAndExtract, uploadDocument } from "../extraction";

describe("extraction api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uses shared multipart client for document upload", async () => {
    (apiFetchFormData as any).mockResolvedValue({ ok: true });

    const file = new File(["hello"], "source.txt", { type: "text/plain" });
    await uploadDocument("source-1", file);

    expect(apiFetchFormData).toHaveBeenCalledOnce();
    const [path, options] = (apiFetchFormData as any).mock.calls[0];
    expect(path).toBe("/sources/source-1/upload-document");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
  });

  it("uses shared multipart client for upload-and-extract", async () => {
    (apiFetchFormData as any).mockResolvedValue({ ok: true });

    const file = new File(["hello"], "source.txt", { type: "text/plain" });
    await uploadAndExtract("source-1", file);

    expect(apiFetchFormData).toHaveBeenCalledOnce();
    const [path] = (apiFetchFormData as any).mock.calls[0];
    expect(path).toBe("/sources/source-1/upload-and-extract");
  });

  it("keeps json extraction endpoints on the shared api client", async () => {
    (apiFetch as any).mockResolvedValue({ ok: true });

    await extractFromDocument("source-1");
    await extractFromUrl("source-1", "https://example.com");
    await saveExtraction("source-1", { entities: [], relations: [], links: [] } as any);

    expect(apiFetch).toHaveBeenCalledTimes(3);
  });
});
