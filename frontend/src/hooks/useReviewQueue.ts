import { useState, useCallback, useEffect } from "react";
import {
  listPendingExtractions,
  getReviewStats,
  type ExtractionType,
  type StagedExtractionRead,
  type ReviewStats,
  type StagedExtractionFilters,
} from "../api/extractionReview";
import { usePageErrorHandler } from "./usePageErrorHandler";

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
  extractionType?: ExtractionType;
}

export interface UseReviewQueueReturn {
  extractions: StagedExtractionRead[];
  stats: ReviewStats | null;
  isLoading: boolean;
  page: number;
  hasMore: boolean;
  loadMore: () => void;
  refresh: () => void;
  applyFilters: (minScore?: number, onlyFlagged?: boolean, extractionType?: ExtractionType) => void;
}

export function useReviewQueue(
  options: UseReviewQueueOptions = {}
): UseReviewQueueReturn {
  const { pageSize = 20, minScore, onlyFlagged = false, extractionType } = options;
  const handlePageError = usePageErrorHandler();

  const [extractions, setExtractions] = useState<StagedExtractionRead[]>([]);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  // Reset to page 1 and reload fresh whenever filters change
  useEffect(() => {
    setPage(1);
    loadExtractions(true); // eslint-disable-line react-hooks/exhaustive-deps
  }, [minScore, onlyFlagged, extractionType]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadExtractions = useCallback(
    async (reset: boolean = false) => {
      setIsLoading(true);

      try {
        const filters: StagedExtractionFilters = {
          page: reset ? 1 : page,
          page_size: pageSize,
          extraction_type: extractionType,
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
        handlePageError(err, "Failed to load review queue");
      } finally {
        setIsLoading(false);
      }
    },
    [handlePageError, page, pageSize, extractionType, minScore, onlyFlagged]
  );

  const loadStats = useCallback(async () => {
    try {
      const statsData = await getReviewStats();
      setStats(statsData);
    } catch (err) {
      handlePageError(err, "Failed to load review stats");
    }
  }, [handlePageError]);

  const loadMore = useCallback(() => {
    if (!isLoading && hasMore) {
      setPage((prev) => prev + 1);
    }
  }, [isLoading, hasMore]);

  const refresh = useCallback(() => {
    loadExtractions(true);
    loadStats();
  }, [loadExtractions, loadStats]);

  // applyFilters is kept for backward compatibility; prefer passing options directly.
  const applyFilters = useCallback((_minScore?: number, _onlyFlagged?: boolean, _extractionType?: ExtractionType) => {
    // Filter state is owned by the caller via options; this is a no-op.
  }, []);

  // Append when page increments (load more)
  useEffect(() => {
    if (page > 1) {
      loadExtractions(false); // eslint-disable-line react-hooks/exhaustive-deps
    }
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

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
