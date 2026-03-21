import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEntityData } from "../useEntityData";
import type { EntityRead } from "../../types/entity";

vi.mock("../../api/entities", () => ({
  getEntity: vi.fn(),
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

import { getEntity } from "../../api/entities";

describe("useEntityData", () => {
  const mockEntity: EntityRead = {
    id: "entity-1",
    slug: "aspirin",
    summary: { en: "Pain reliever" },
    created_at: "2025-01-01T00:00:00Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("clears stale entity data after a failed refetch", async () => {
    vi.mocked(getEntity)
      .mockResolvedValueOnce(mockEntity)
      .mockRejectedValueOnce(new Error("Entity refresh failed"));

    const { result } = renderHook(() => useEntityData("entity-1"));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.entity).toEqual(mockEntity);
    });

    await act(async () => {
      await result.current.refetch();
    });

    expect(result.current.entity).toBeNull();
    expect(result.current.error?.message).toBe("Entity refresh failed");
    expect(showError).toHaveBeenCalledWith(expect.any(Error));
  });
});
