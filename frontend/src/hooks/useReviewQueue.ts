import { useState, useCallback, useEffect } from "react";
import {
  listPendingExtractions,
  getReviewStats,
  type StagedExtractionRead,
  type ReviewStats,
  type StagedExtractionFilters,
} from "../api/extractionReview";
import { useNotification } from "../notifications/NotificationContext";

/**
 * Hook for managing review queue data and pagination.
 *
 * Handles extraction list fetching, stats loading, pagination,
 * and filtering (min score, flagged only).
 *
 * @param pageSize - Number of extractions per page
 * @returns Review queue state and actions
 */
export interface UseReviewQueueOptions {
  pageSize?: number;
  minScore?: number;
  onlyFlagged?: boolean;
}

export interface UseReviewQueueReturn {
  extractions: StagedExtractionRead[];
  stats: ReviewStats | null;
  isLoading: boolean;
  page: number;
  hasMore: boolean;
  loadMore: () => void;
  refresh: () => void;
  applyFilters: (minScore?: number, onlyFlagged?: boolean) => void;
}

export function useReviewQueue(
  options: UseReviewQueueOptions = {}
): UseReviewQueueReturn {
  const { pageSize = 20, minScore: initialMinScore, onlyFlagged: initialOnlyFlagged } = options;
  const { showError } = useNotification();

  const [extractions, setExtractions] = useState<StagedExtractionRead[]>([]);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [minScore, setMinScore] = useState<number | undefined>(initialMinScore);
  const [onlyFlagged, setOnlyFlagged] = useState(initialOnlyFlagged || false);

  const loadExtractions = useCallback(
    async (reset: boolean = false) => {
      setIsLoading(true);

      try {
        const filters: StagedExtractionFilters = {
          page: reset ? 1 : page,
          page_size: pageSize,
          min_validation_score: minScore,
          has_flags: onlyFlagged || undefined,
        };

        const response = await listPendingExtractions(filters);

        if (reset) {
          setExtractions(response.extractions);
          setPage(1);
        } else {
          setExtractions((prev) => [...prev, ...response.extractions]);
        }

        setHasMore(response.has_more);
      } catch (err) {
        showError(err);
      } finally {
        setIsLoading(false);
      }
    },
    [page, pageSize, minScore, onlyFlagged, showError]
  );

  const loadStats = useCallback(async () => {
    try {
      const statsData = await getReviewStats();
      setStats(statsData);
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
  }, []);

  const loadMore = useCallback(() => {
    if (!isLoading && hasMore) {
      setPage((prev) => prev + 1);
    }
  }, [isLoading, hasMore]);

  const refresh = useCallback(() => {
    loadExtractions(true);
    loadStats();
  }, [loadExtractions, loadStats]);

  const applyFilters = useCallback((newMinScore?: number, newOnlyFlagged?: boolean) => {
    setMinScore(newMinScore);
    setOnlyFlagged(newOnlyFlagged || false);
    setPage(1);
  }, []);

  // Load initial data
  useEffect(() => {
    loadExtractions(false);
  }, [page, minScore, onlyFlagged]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return {
    extractions,
    stats,
    isLoading,
    page,
    hasMore,
    loadMore,
    refresh,
    applyFilters,
  };
}
