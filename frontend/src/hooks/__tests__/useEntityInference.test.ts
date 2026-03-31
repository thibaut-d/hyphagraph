import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEntityInference } from "../useEntityInference";
import type { InferenceRead } from "../../types/inference";
import type { SourceRead } from "../../types/source";

vi.mock("../../api/inferences", () => ({
  getInferenceForEntity: vi.fn(),
}));

vi.mock("../../api/sources", () => ({
  getSource: vi.fn(),
}));

const showError = vi.fn();

vi.mock("../../notifications/NotificationContext", () => ({
  useNotification: () => ({
    showError,
    showInfo: vi.fn(),
    showSuccess: vi.fn(),
    showWarning: vi.fn(),
  }),
}));

import { getInferenceForEntity } from "../../api/inferences";
import { getSource } from "../../api/sources";

describe("useEntityInference", () => {
  const initialInference: InferenceRead = {
    entity_id: "entity-1",
    relations_by_kind: {
      treats: [
        {
          id: "rel-1",
          source_id: "source-1",
          kind: "treats",
          direction: "supports",
          confidence: 0.8,
          roles: [],
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
          status: "confirmed" as const,
        },
      ],
    },
  };

  const emptyInference: InferenceRead = {
    entity_id: "entity-1",
    relations_by_kind: {},
  };

  const mockSource: SourceRead = {
    id: "source-1",
    title: "Clinical trial",
    authors: ["Smith"],
    year: 2024,
    kind: "paper",
    origin: "journal",
    url: "https://example.com/source-1",
    trust_level: 0.9,
    created_at: "2025-01-01T00:00:00Z",
    status: "confirmed",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("clears cached sources when a refetch returns no source-backed relations", async () => {
    vi.mocked(getInferenceForEntity)
      .mockResolvedValueOnce(initialInference)
      .mockResolvedValueOnce(emptyInference);
    vi.mocked(getSource).mockResolvedValue(mockSource);

    const { result } = renderHook(() => useEntityInference("entity-1"));

    await waitFor(() => {
      expect(result.current.inference).toEqual(initialInference);
      expect(result.current.sources).toEqual({ "source-1": mockSource });
    });

    await act(async () => {
      await result.current.loadInference({ population: "adults" });
    });

    expect(result.current.inference).toEqual(emptyInference);
    expect(result.current.sources).toEqual({});
    expect(result.current.error).toBeNull();
  });

  it("clears stale inference data after a failed refetch", async () => {
    vi.mocked(getInferenceForEntity)
      .mockResolvedValueOnce(initialInference)
      .mockRejectedValueOnce(new Error("Inference refresh failed"));
    vi.mocked(getSource).mockResolvedValue(mockSource);

    const { result } = renderHook(() => useEntityInference("entity-1"));

    await waitFor(() => {
      expect(result.current.inference).toEqual(initialInference);
      expect(result.current.sources).toEqual({ "source-1": mockSource });
    });

    await act(async () => {
      await result.current.loadInference({});
    });

    expect(result.current.inference).toBeNull();
    expect(result.current.sources).toEqual({});
    expect(result.current.error?.message).toBe("Inference refresh failed");
    expect(showError).toHaveBeenCalledWith(expect.any(Error));
  });

  it("surfaces degraded source loading when some source lookups fail", async () => {
    vi.mocked(getInferenceForEntity).mockResolvedValue(initialInference);
    vi.mocked(getSource).mockRejectedValue(new Error("Source load failed"));

    const { result } = renderHook(() => useEntityInference("entity-1"));

    await waitFor(() => {
      expect(result.current.inference).toEqual(initialInference);
      expect(result.current.loadingSources).toBe(false);
    });

    expect(result.current.sources).toEqual({});
    expect(result.current.sourceWarning?.message).toMatch(
      /Some source details could not be loaded/
    );
    expect(result.current.error).toBeNull();
  });
});
