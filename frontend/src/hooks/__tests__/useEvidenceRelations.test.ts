import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEvidenceRelations } from "../useEvidenceRelations";
import type { InferenceRead } from "../../types/inference";

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

import { getSource } from "../../api/sources";

describe("useEvidenceRelations", () => {
  const inference: InferenceRead = {
    entity_id: "entity-1",
    relations_by_kind: {
      treats: [
        {
          id: "rel-1",
          source_id: "source-1",
          kind: "treats",
          direction: "supports",
          confidence: 0.8,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
          status: "confirmed" as const,
          roles: [{ id: "role-1", relation_revision_id: "rev-1", entity_id: "entity-1", role_type: "agent" }],
        },
        {
          id: "rel-2",
          source_id: "source-2",
          kind: "treats",
          direction: "supports",
          confidence: 0.7,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
          status: "confirmed" as const,
          roles: [{ id: "role-2", relation_revision_id: "rev-2", entity_id: "entity-1", role_type: "agent" }],
        },
      ],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("surfaces partial source enrichment failures without dropping relation rows", async () => {
    vi.mocked(getSource)
      .mockResolvedValueOnce({
        id: "source-1",
        title: "Loaded source",
        created_at: "2025-01-01T00:00:00Z",
      } as any)
      .mockRejectedValueOnce(new Error("source lookup failed"));

    const { result } = renderHook(() =>
      useEvidenceRelations("entity-1", undefined, inference)
    );

    await waitFor(() => {
      expect(result.current.relations).toHaveLength(2);
    });

    expect(result.current.sourceLoadFailures).toEqual(["source-2"]);
    expect(result.current.relations[0].source?.id).toBe("source-1");
    expect(result.current.relations[1].source).toBeUndefined();
  });
});
