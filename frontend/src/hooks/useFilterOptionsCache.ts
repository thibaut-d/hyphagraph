import { useState, useEffect } from "react";

const DEFAULT_TTL_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Fetch and cache filter options in localStorage with a TTL.
 *
 * Drop-in replacement for the inline getCachedFilterOptions / setCachedFilterOptions
 * pattern used in list views. The fetcher is called at most once per TTL window.
 */
export function useFilterOptionsCache<T>(
  cacheKey: string,
  fetcher: () => Promise<T>,
  ttlMs: number = DEFAULT_TTL_MS,
): T | null {
  const [options, setOptions] = useState<T | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem(cacheKey);
    if (raw) {
      try {
        const { data, timestamp }: { data: T; timestamp: number } = JSON.parse(raw);
        if (Date.now() - timestamp <= ttlMs) {
          setOptions(data);
          return;
        }
        localStorage.removeItem(cacheKey);
      } catch {
        localStorage.removeItem(cacheKey);
      }
    }

    fetcher().then((data) => {
      setOptions(data);
      try {
        localStorage.setItem(cacheKey, JSON.stringify({ data, timestamp: Date.now() }));
      } catch {
        // localStorage may be full or unavailable — silently skip caching
      }
    });
    // fetcher and ttlMs are expected to be stable references
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cacheKey]);

  return options;
}
