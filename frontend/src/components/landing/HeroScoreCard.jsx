import { useEffect, useState } from "react";
import { useCountUp } from "../../hooks/useCountUp";

const SCORE = 86;
const BARS = [
  { label: "Human readability", pct: 82 },
  { label: "Keyword match", pct: 74 },
];

/**
 * Floating hero visual: an example resume score card whose ring fills, number
 * counts up, and breakdown bars sweep in on mount — a preview of the product.
 * Decorative but labelled for screen readers.
 */
export default function HeroScoreCard() {
  const [armed, setArmed] = useState(false);
  const score = useCountUp(armed ? SCORE : 0);

  useEffect(() => {
    // Arm on the next frame so the ring/bars animate from empty on first paint.
    const frame = requestAnimationFrame(() => setArmed(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  const size = 176;
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - (armed ? SCORE : 0) / 100);

  return (
    <figure className="relative w-full max-w-sm animate-float rounded-3xl border border-ink-700/70 bg-ink-800/60 p-8 shadow-lift backdrop-blur-sm">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -inset-px rounded-3xl bg-gradient-to-b from-gold-500/10 to-transparent"
      />

      <div className="relative flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-gold-400" />
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-paper-200/60">
            Resume score
          </span>
        </div>
        <span className="rounded-full bg-gold-500/15 px-2.5 py-1 text-[0.65rem] font-semibold uppercase tracking-wide text-gold-300">
          Live
        </span>
      </div>

      <div className="relative mt-6 flex justify-center">
        <div className="relative" style={{ width: size, height: size }}>
          <svg
            width={size}
            height={size}
            viewBox={`0 0 ${size} ${size}`}
            role="img"
            aria-label={`Example resume ATS score: ${SCORE} out of 100`}
          >
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="#1B2334"
              strokeWidth={strokeWidth}
            />
            <circle
              className="gauge-progress"
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="#C9A961"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display text-5xl font-semibold text-gold-400">
              {score}
            </span>
            <span className="text-[0.65rem] font-medium uppercase tracking-[0.2em] text-paper-200/50">
              ATS ready
            </span>
          </div>
        </div>
      </div>

      <figcaption className="relative mt-8 space-y-4">
        {BARS.map((bar, index) => (
          <div key={bar.label}>
            <div className="flex items-center justify-between text-xs">
              <span className="text-paper-200/70">{bar.label}</span>
              <span className="font-semibold text-paper-200/90">{bar.pct}%</span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-ink-700/80">
              <div
                className="h-full rounded-full bg-gradient-to-r from-gold-500 to-gold-300"
                style={{
                  width: `${armed ? bar.pct : 0}%`,
                  transition: "width 1.1s cubic-bezier(0.22, 1, 0.36, 1)",
                  transitionDelay: `${220 + index * 150}ms`,
                }}
              />
            </div>
          </div>
        ))}
      </figcaption>
    </figure>
  );
}
