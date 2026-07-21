/** Clear, specific inline error — never a blank screen (spec 9). */
export default function ErrorState({ message, onRetry }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-xl border border-red-500/30 bg-red-900/40 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-center gap-2.5">
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="h-5 w-5 shrink-0 text-red-300"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v4m0 4h.01" />
        </svg>
        <p className="text-sm text-red-200">{message}</p>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-full border border-red-500/40 px-4 py-1.5 text-sm font-medium text-red-200 transition-colors hover:bg-red-500/20 active:scale-95"
        >
          Try again
        </button>
      )}
    </div>
  );
}
