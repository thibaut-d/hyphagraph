import { useEffect, useRef, useCallback } from 'react';

interface UseInfiniteScrollOptions {
  /**
   * Callback function to load more data
   */
  onLoadMore: () => void;

  /**
   * Whether data is currently being loaded
   */
  isLoading: boolean;

  /**
   * Whether there is more data to load
   */
  hasMore: boolean;

  /**
   * Distance from bottom in pixels to trigger load more (default: 200)
   */
  threshold?: number;
}

/**
 * Custom hook for implementing infinite scroll behavior.
 *
 * Automatically loads more data when user scrolls near the bottom of the page.
 * Falls back to manual "Load More" button when scroll detection fails.
 *
 * @param options - Configuration options
 * @returns Ref to attach to the scrollable container
 */
export function useInfiniteScroll({
  onLoadMore,
  isLoading,
  hasMore,
  threshold = 200,
}: UseInfiniteScrollOptions) {
  const observerRef = useRef<IntersectionObserver | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const handleIntersection = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;

      if (entry.isIntersecting && hasMore && !isLoading) {
        onLoadMore();
      }
    },
    [hasMore, isLoading, onLoadMore]
  );

  useEffect(() => {
    const options = {
      root: null,
      rootMargin: `${threshold}px`,
      threshold: 0.1,
    };

    observerRef.current = new IntersectionObserver(handleIntersection, options);

    const currentSentinel = sentinelRef.current;
    if (currentSentinel) {
      observerRef.current.observe(currentSentinel);
    }

    return () => {
      if (observerRef.current && currentSentinel) {
        observerRef.current.unobserve(currentSentinel);
      }
    };
  }, [handleIntersection, threshold]);

  return sentinelRef;
}
