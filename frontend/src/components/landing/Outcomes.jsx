import { useEffect, useState } from "react";
import { useCountUp } from "../../hooks/useCountUp";
import Reveal from "./Reveal";

/**
 * The score line for one testimonial: the "after" number counts up and a lift
 * bar sweeps from the before score to the after score. Remounts per testimonial
 * (the parent figure is keyed on index), so it re-animates on every rotation.
 */
function ScoreDelta({ before, after }) {
  const [armed, setArmed] = useState(false);
  const shown = useCountUp(armed ? after : 0, 1400);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setArmed(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <>
      <div className="flex items-center justify-center gap-5 font-display">
        <span className="text-4xl font-medium text-paper-200/50 line-through decoration-2">
          {before}
        </span>
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="h-6 w-6 text-gold-500"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M5 12h14m-6-6 6 6-6 6" />
        </svg>
        <span className="text-6xl font-semibold text-gold-400">{shown}</span>
      </div>
      <div className="mx-auto mt-8 h-1.5 max-w-sm overflow-hidden rounded-full bg-ink-700/70">
        <div
          className="h-full rounded-full bg-gradient-to-r from-gold-600 via-gold-400 to-gold-300"
          style={{
            width: `${armed ? after : before}%`,
            transition: "width 1.4s cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        />
      </div>
    </>
  );
}

const OUTCOMES = [
  {
    before: 54,
    after: 86,
    quote:
      "The breakdown told me exactly which bullets had no numbers. Two evenings of edits and my callbacks tripled.",
    name: "Priya",
    role: "Backend Engineer",
  },
  {
    before: 61,
    after: 90,
    quote:
      "The gap map showed three skills I kept ignoring. I closed one, addressed the other two in interviews — offer signed.",
    name: "Daniel",
    role: "Data Analyst",
  },
  {
    before: 47,
    after: 81,
    quote:
      "The mock interview asked about my own projects — harder than my real interview. I walked in over-prepared.",
    name: "Sana",
    role: "Product Designer",
  },
];

/** Before/after score testimonials, auto-rotating with manual dots. */
export default function Outcomes() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    // Keyed on index so a manual dot click restarts the 6s rotation window.
    const id = setInterval(
      () => setIndex((current) => (current + 1) % OUTCOMES.length),
      6000,
    );
    return () => clearInterval(id);
  }, [index]);

  const active = OUTCOMES[index];

  return (
    <section id="outcomes" className="bg-ink-950 py-24 sm:py-32">
      <div className="mx-auto max-w-4xl px-5 text-center sm:px-8">
        <Reveal>
          <p className="text-eyebrow font-semibold uppercase text-gold-400">
            Before / After
          </p>
          <h2 className="mt-4 font-display text-display-lg font-medium text-paper-50">
            Scores move when you know what to fix.
          </h2>
        </Reveal>

        <Reveal className="mt-14">
          <figure
            key={index}
            aria-live="polite"
            className="animate-fade-in rounded-3xl border border-ink-700/70 bg-ink-800/50 px-6 py-12 sm:px-14"
          >
            <ScoreDelta before={active.before} after={active.after} />
            <blockquote className="mx-auto mt-8 max-w-xl text-lg leading-relaxed text-paper-200/85">
              “{active.quote}”
            </blockquote>
            <figcaption className="mt-6 text-sm font-medium text-paper-200/60">
              {active.name} · {active.role}
            </figcaption>
          </figure>
        </Reveal>

        <div className="mt-8 flex justify-center gap-2.5" role="tablist" aria-label="Testimonials">
          {OUTCOMES.map((outcome, dotIndex) => (
            <button
              key={outcome.name}
              type="button"
              role="tab"
              aria-selected={dotIndex === index}
              aria-label={`Show testimonial from ${outcome.name}`}
              onClick={() => setIndex(dotIndex)}
              className={`h-2.5 rounded-full transition-all ${
                dotIndex === index
                  ? "w-8 bg-gold-500"
                  : "w-2.5 bg-ink-600 hover:bg-ink-500"
              }`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
