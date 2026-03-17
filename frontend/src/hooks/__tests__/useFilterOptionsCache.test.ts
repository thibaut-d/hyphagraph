/**
 * Tests for useFilterOptionsCache hook.
 *
 * Verifies the TTL-based localStorage caching contract: fresh cache is served
 * without calling the fetcher, stale or missing cache triggers a fetch and
 * re-populates localStorage, and malformed entries are evicted gracefully.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useFilterOptionsCache } from '../useFilterOptionsCache';

const CACHE_KEY = 'test-cache-key';
const TTL_MS = 5 * 60 * 1000; // 5 minutes (default)
const SHORT_TTL_MS = 100; // 100ms for stale tests

type TestOptions = { kinds: string[] };

describe('useFilterOptionsCache', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('returns null initially when cache is empty', () => {
    const fetcher = vi.fn().mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() =>
      useFilterOptionsCache<TestOptions>(CACHE_KEY, fetcher)
    );
    expect(result.current).toBeNull();
  });

  it('calls fetcher when cache is empty and returns fetched data', async () => {
    const mockData: TestOptions = { kinds: ['article', 'book'] };
    const fetcher = vi.fn().mockResolvedValue(mockData);

    const { result } = renderHook(() =>
      useFilterOptionsCache<TestOptions>(CACHE_KEY, fetcher)
    );

    await waitFor(() => {
      expect(result.current).toEqual(mockData);
    });

    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('persists fetched data to localStorage', async () => {
    const mockData: TestOptions = { kinds: ['article'] };
    const fetcher = vi.fn().mockResolvedValue(mockData);

    renderHook(() => useFilterOptionsCache<TestOptions>(CACHE_KEY, fetcher));

    await waitFor(() => {
      const raw = localStorage.getItem(CACHE_KEY);
      expect(raw).not.toBeNull();
      const parsed = JSON.parse(raw!);
      expect(parsed.data).toEqual(mockData);
      expect(typeof parsed.timestamp).toBe('number');
    });
  });

  it('returns cached data without calling fetcher when cache is fresh', async () => {
    const cachedData: TestOptions = { kinds: ['cached'] };
    localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ data: cachedData, timestamp: Date.now() })
    );

    const fetcher = vi.fn();

    const { result } = renderHook(() =>
      useFilterOptionsCache<TestOptions>(CACHE_KEY, fetcher)
    );

    await waitFor(() => {
      expect(result.current).toEqual(cachedData);
    });

    expect(fetcher).not.toHaveBeenCalled();
  });

  it('evicts stale cache entry and calls fetcher when TTL has expired', async () => {
    const staleData: TestOptions = { kinds: ['stale'] };
    const freshData: TestOptions = { kinds: ['fresh'] };
    const expiredTimestamp = Date.now() - SHORT_TTL_MS - 1;

    localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ data: staleData, timestamp: expiredTimestamp })
    );

    const fetcher = vi.fn().mockResolvedValue(freshData);

    const { result } = renderHook(() =>
      useFilterOptionsCache<TestOptions>(CACHE_KEY, fetcher, SHORT_TTL_MS)
    );

    await waitFor(() => {
      expect(result.current).toEqual(freshData);
    });

    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(CACHE_KEY)).not.toContain('stale');
  });

  it('evicts malformed cache entry and calls fetcher', async () => {
    localStorage.setItem(CACHE_KEY, 'not-valid-json{{{');

    const mockData: TestOptions = { kinds: ['recovered'] };
    const fetcher = vi.fn().mockResolvedValue(mockData);

    const { result } = renderHook(() =>
      useFilterOptionsCache<TestOptions>(CACHE_KEY, fetcher)
    );

    await waitFor(() => {
      expect(result.current).toEqual(mockData);
    });

    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('removes malformed cache entry from localStorage', async () => {
    localStorage.setItem(CACHE_KEY, 'not-valid-json{{{');

    const fetcher = vi.fn().mockResolvedValue({ kinds: [] });

    renderHook(() => useFilterOptionsCache<TestOptions>(CACHE_KEY, fetcher));

    await waitFor(() => {
      // After fetch, the localStorage entry should be valid JSON (re-written)
      const raw = localStorage.getItem(CACHE_KEY);
      expect(() => JSON.parse(raw!)).not.toThrow();
    });
  });

  it('uses custom TTL when provided', async () => {
    const customTtl = 1000;
    const cachedData: TestOptions = { kinds: ['custom'] };
    const freshTimestamp = Date.now() - 500; // 500ms ago, within 1000ms TTL

    localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ data: cachedData, timestamp: freshTimestamp })
    );

    const fetcher = vi.fn();

    const { result } = renderHook(() =>
      useFilterOptionsCache<TestOptions>(CACHE_KEY, fetcher, customTtl)
    );

    await waitFor(() => {
      expect(result.current).toEqual(cachedData);
    });

    expect(fetcher).not.toHaveBeenCalled();
  });
});
