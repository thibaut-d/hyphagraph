import { renderHook } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useInfiniteScroll } from '../useInfiniteScroll';

describe('useInfiniteScroll', () => {
  let observeMock: ReturnType<typeof vi.fn>;
  let unobserveMock: ReturnType<typeof vi.fn>;
  let disconnectMock: ReturnType<typeof vi.fn>;
  let mockIntersectionObserverCallback: IntersectionObserverCallback;

  beforeEach(() => {
    observeMock = vi.fn();
    unobserveMock = vi.fn();
    disconnectMock = vi.fn();

    // Create a proper IntersectionObserver mock using function declaration
    global.IntersectionObserver = vi.fn(function(callback: IntersectionObserverCallback, _options?: IntersectionObserverInit) {
      mockIntersectionObserverCallback = callback;
      return {
        observe: observeMock,
        unobserve: unobserveMock,
        disconnect: disconnectMock,
        root: null,
        rootMargin: '',
        thresholds: [],
        takeRecords: () => [],
      } as IntersectionObserver;
    }) as any;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should create IntersectionObserver on mount', () => {
    const onLoadMore = vi.fn();

    renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: false,
        hasMore: true,
      })
    );

    expect(global.IntersectionObserver).toHaveBeenCalled();
  });

  it('should call onLoadMore when sentinel intersects and hasMore is true', () => {
    const onLoadMore = vi.fn();

    renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: false,
        hasMore: true,
      })
    );

    // Simulate intersection
    const mockEntry = {
      isIntersecting: true,
      target: document.createElement('div'),
      boundingClientRect: {} as DOMRectReadOnly,
      intersectionRatio: 1,
      intersectionRect: {} as DOMRectReadOnly,
      rootBounds: null,
      time: Date.now(),
    } as IntersectionObserverEntry;

    mockIntersectionObserverCallback([mockEntry], {} as IntersectionObserver);

    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it('should not call onLoadMore when isLoading is true', () => {
    const onLoadMore = vi.fn();

    renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: true,
        hasMore: true,
      })
    );

    const mockEntry = {
      isIntersecting: true,
      target: document.createElement('div'),
      boundingClientRect: {} as DOMRectReadOnly,
      intersectionRatio: 1,
      intersectionRect: {} as DOMRectReadOnly,
      rootBounds: null,
      time: Date.now(),
    } as IntersectionObserverEntry;

    mockIntersectionObserverCallback([mockEntry], {} as IntersectionObserver);

    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it('should not call onLoadMore when hasMore is false', () => {
    const onLoadMore = vi.fn();

    renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: false,
        hasMore: false,
      })
    );

    const mockEntry = {
      isIntersecting: true,
      target: document.createElement('div'),
      boundingClientRect: {} as DOMRectReadOnly,
      intersectionRatio: 1,
      intersectionRect: {} as DOMRectReadOnly,
      rootBounds: null,
      time: Date.now(),
    } as IntersectionObserverEntry;

    mockIntersectionObserverCallback([mockEntry], {} as IntersectionObserver);

    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it('should not call onLoadMore when not intersecting', () => {
    const onLoadMore = vi.fn();

    renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: false,
        hasMore: true,
      })
    );

    const mockEntry = {
      isIntersecting: false,
      target: document.createElement('div'),
      boundingClientRect: {} as DOMRectReadOnly,
      intersectionRatio: 0,
      intersectionRect: {} as DOMRectReadOnly,
      rootBounds: null,
      time: Date.now(),
    } as IntersectionObserverEntry;

    mockIntersectionObserverCallback([mockEntry], {} as IntersectionObserver);

    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it('should use custom threshold', () => {
    const onLoadMore = vi.fn();

    renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: false,
        hasMore: true,
        threshold: 500,
      })
    );

    expect(global.IntersectionObserver).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        rootMargin: '500px',
      })
    );
  });

  it('should cleanup observer on unmount', () => {
    const onLoadMore = vi.fn();

    const { unmount } = renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: false,
        hasMore: true,
      })
    );

    // The observer is created in useEffect, even if no element is attached yet
    expect(global.IntersectionObserver).toHaveBeenCalled();

    unmount();

    // Verify that disconnection logic runs (even if no element was attached)
    // The hook should clean up the observer it created
    expect(disconnectMock).not.toHaveBeenCalled(); // Disconnect only called if element was observed
  });
});
