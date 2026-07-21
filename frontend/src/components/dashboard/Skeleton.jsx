/** Shimmering placeholder block (see .skeleton in index.css). */
export default function Skeleton({ className = "" }) {
  return <div aria-hidden="true" className={`skeleton ${className}`} />;
}

/** Card-shaped skeleton used while the dashboard boots. */
export function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card">
      <Skeleton className="h-4 w-40" />
      <Skeleton className="mt-4 h-28 w-full" />
      <Skeleton className="mt-3 h-4 w-2/3" />
    </div>
  );
}
