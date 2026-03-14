import {
  type DependencyList,
  type Dispatch,
  type SetStateAction,
  useCallback,
  useEffect,
  useState,
} from "react";

interface UseAsyncResourceOptions<T> {
  enabled?: boolean;
  initialData?: T | null;
  deps: DependencyList;
  load: () => Promise<T>;
  onError?: (error: unknown) => string;
}

interface AsyncResourceState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  setData: Dispatch<SetStateAction<T | null>>;
}

export function useAsyncResource<T>({
  enabled = true,
  initialData = null,
  deps,
  load,
  onError,
}: UseAsyncResourceOptions<T>): AsyncResourceState<T> {
  const [data, setData] = useState<T | null>(initialData);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const nextData = await load();
      setData(nextData);
    } catch (resourceError) {
      setData(initialData);
      setError(onError ? onError(resourceError) : "An error occurred");
    } finally {
      setLoading(false);
    }
  }, [enabled, initialData, load, onError]);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      if (!enabled) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const nextData = await load();
        if (!cancelled) {
          setData(nextData);
        }
      } catch (resourceError) {
        if (!cancelled) {
          setData(initialData);
          setError(onError ? onError(resourceError) : "An error occurred");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  // `deps` is the caller-controlled invalidation contract for loading.
  // Inline `load`/`onError` closures would otherwise trigger render loops.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, initialData, ...deps]);

  return {
    data,
    loading,
    error,
    reload,
    setData,
  };
}
