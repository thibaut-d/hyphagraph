import { renderHook } from '@testing-library/react';
import { useInfiniteScroll } from '../useInfiniteScroll';

// Mock IntersectionObserver
class MockIntersectionObserver {
  callback: IntersectionObserverCallback;
  elements: Set<Element>;

  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback;
    this.elements = new Set();
  }

  observe(element: Element) {
    this.elements.add(element);
  }

  unobserve(element: Element) {
    this.elements.delete(element);
  }

  disconnect() {
    this.elements.clear();
  }

  triggerIntersection(isIntersecting: boolean) {
    const entries: IntersectionObserverEntry[] = Array.from(this.elements).map(
      (element) => ({
        isIntersecting,
        target: element,
        boundingClientRect: {} as DOMRectReadOnly,
        intersectionRatio: isIntersecting ? 1 : 0,
        intersectionRect: {} as DOMRectReadOnly,
        rootBounds: null,
        time: Date.now(),
      })
    );
    this.callback(entries, this as any);
  }
}

describe('useInfiniteScroll', () => {
  let mockObserver: MockIntersectionObserver;

  beforeEach(() => {
    mockObserver = new MockIntersectionObserver(() => {});
    global.IntersectionObserver = jest.fn((callback) => {
      mockObserver.callback = callback;
      return mockObserver as any;
    }) as any;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should create IntersectionObserver on mount', () => {
    const onLoadMore = jest.fn();

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
    const onLoadMore = jest.fn();

    const { result } = renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: false,
        hasMore: true,
      })
    );

    // Simulate element being observed
    const sentinelElement = document.createElement('div');
    result.current.current = sentinelElement;

    // Trigger intersection
    mockObserver.triggerIntersection(true);

    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it('should not call onLoadMore when isLoading is true', () => {
    const onLoadMore = jest.fn();

    const { result } = renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: true,
        hasMore: true,
      })
    );

    const sentinelElement = document.createElement('div');
    result.current.current = sentinelElement;

    mockObserver.triggerIntersection(true);

    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it('should not call onLoadMore when hasMore is false', () => {
    const onLoadMore = jest.fn();

    const { result } = renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: false,
        hasMore: false,
      })
    );

    const sentinelElement = document.createElement('div');
    result.current.current = sentinelElement;

    mockObserver.triggerIntersection(true);

    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it('should not call onLoadMore when not intersecting', () => {
    const onLoadMore = jest.fn();

    const { result } = renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: false,
        hasMore: true,
      })
    );

    const sentinelElement = document.createElement('div');
    result.current.current = sentinelElement;

    mockObserver.triggerIntersection(false);

    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it('should use custom threshold', () => {
    const onLoadMore = jest.fn();

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
    const onLoadMore = jest.fn();
    const disconnectSpy = jest.spyOn(mockObserver, 'disconnect');

    const { unmount } = renderHook(() =>
      useInfiniteScroll({
        onLoadMore,
        isLoading: false,
        hasMore: true,
      })
    );

    unmount();

    expect(disconnectSpy).toHaveBeenCalled();
  });
});
