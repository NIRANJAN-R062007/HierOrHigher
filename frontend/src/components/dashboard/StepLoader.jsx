import { useEffect, useState } from "react";

/**
 * Purposeful loading state: walks through what is actually happening during
 * a Gemini call (e.g. "Parsing your resume…" → "Scoring against ATS rules…")
 * instead of a generic spinner. Advances on a timer and holds on the last
 * step until the request resolves.
 */
export default function StepLoader({ steps, stepMs = 1500 }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
    const id = setInterval(
      () => setIndex((current) => Math.min(current + 1, steps.length - 1)),
      stepMs,
    );
    return () => clearInterval(id);
  }, [steps, stepMs]);

  return (
    <ol aria-live="polite" className="space-y-2.5">
      {steps.map((step, stepIndex) => {
        const state =
          stepIndex < index ? "done" : stepIndex === index ? "current" : "next";
        return (
          <li key={step} className="flex items-center gap-3 text-sm">
            {state === "done" && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-900/40 text-emerald-300">
                <svg aria-hidden="true" viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m5 13 4 4L19 7" />
                </svg>
              </span>
            )}
            {state === "current" && (
              <span className="flex h-5 w-5 items-center justify-center">
                <span className="h-2.5 w-2.5 animate-pulse-dot rounded-full bg-gold-500" />
              </span>
            )}
            {state === "next" && (
              <span className="flex h-5 w-5 items-center justify-center">
                <span className="h-2 w-2 rounded-full bg-ink-600" />
              </span>
            )}
            <span
              className={
                state === "current"
                  ? "font-medium text-paper-50"
                  : state === "done"
                    ? "text-paper-200/70"
                    : "text-paper-200/50"
              }
            >
              {step}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
