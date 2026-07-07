import { useCallback, useState } from "react";

/**
 * Wrap an async handler with loading/error state — every module action on
 * the dashboard uses this so failures render as clear inline error states,
 * never blank screens or console-only errors.
 */
export function useAsyncAction(handler) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const run = useCallback(
    async (...args) => {
      setLoading(true);
      setError(null);
      try {
        return await handler(...args);
      } catch (err) {
        setError(err.message || "Something went wrong. Please try again.");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [handler],
  );

  return { run, loading, error, clearError: () => setError(null) };
}
