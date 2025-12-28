/**
 * Cache management utilities for localStorage-based caching.
 */

const FILTER_OPTIONS_CACHE_KEY = 'source-filter-options-cache';

/**
 * Invalidate (clear) the source filter options cache.
 * Should be called when sources are created, updated, or deleted.
 */
export function invalidateSourceFilterCache(): void {
  localStorage.removeItem(FILTER_OPTIONS_CACHE_KEY);
}

/**
 * Invalidate all caches.
 * Useful for logout or major data changes.
 */
export function invalidateAllCaches(): void {
  invalidateSourceFilterCache();
  // Add other cache invalidations here as needed
}
