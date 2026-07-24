import { useEffect, useState } from "react";

// Fixed match-percentage buckets — the histogram's x-axis.
const BUCKETS = [
  { label: "0–20", min: 0, max: 20 },
  { label: "21–40", min: 21, max: 40 },
  { label: "41–60", min: 41, max: 60 },
  { label: "61–80", min: 61, max: 80 },
  { label: "81–100", min: 81, max: 100 },
];

/**
 * Match-percentage distribution: how many of the user's gap reports fall into
 * each 20-point band. Hand-rolled Tailwind bars (gold gradient, like the gap
 * match bar) that grow from the baseline on reveal, with reduced-motion honored.
 */
export default function MatchHistogram({ items }) {
  const reduce =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [armed, setArmed] = useState(reduce);
  useEffect(() => {
    if (reduce) return undefined;
    const frame = requestAnimationFrame(() => setArmed(true));
    return () => cancelAnimationFrame(frame);
  }, [reduce]);

  const counts = BUCKETS.map(
    (bucket) =>
      items.filter(
        (item) =>
          item.match_percentage >= bucket.min &&
          item.match_percentage <= bucket.max,
      ).length,
  );
  const max = Math.max(1, ...counts);

  return (
    <div>
      <div className="flex h-56 items-end gap-3 sm:gap-5">
        {BUCKETS.map((bucket, i) => {
          const count = counts[i];
          const heightPct = (count / max) * 100;
          return (
            <div
              key={bucket.label}
              className="flex flex-1 flex-col items-center gap-2"
            >
              <span className="h-4 text-xs font-semibold text-paper-200/70">
                {count || ""}
              </span>
              <div className="flex w-full flex-1 items-end">
                <div
                  role="img"
                  aria-label={`${count} report${count === 1 ? "" : "s"} in the ${bucket.label}% match range`}
                  className="w-full rounded-t-md bg-gradient-to-t from-gold-600 to-gold-400 transition-all duration-700 ease-out"
                  style={{
                    height: armed ? `${heightPct}%` : "0%",
                    transition: reduce ? "none" : undefined,
                  }}
                />
              </div>
              <span className="text-xs font-medium text-paper-200/60">
                {bucket.label}
              </span>
            </div>
          );
        })}
      </div>
      <p className="mt-4 text-center text-xs text-paper-200/50">
        Match % across all your job descriptions
      </p>
    </div>
  );
}
