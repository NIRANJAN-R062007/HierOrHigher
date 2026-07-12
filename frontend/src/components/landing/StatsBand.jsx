import { useEffect, useRef, useState } from "react";
import { useCountUp } from "../../hooks/useCountUp";

const STATS = [
  { target: 12400, prefix: "", suffix: "+", label: "resumes scored and counting" },
  { target: 87, prefix: "", suffix: "%", label: "report more callbacks within a month" },
  { target: 31, prefix: "+", suffix: "", label: "average score lift, before to after" },
  { target: 4, prefix: "", suffix: "", label: "modules from a single upload" },
];

function Stat({ target, prefix, suffix, label, started }) {
  // Target stays 0 until the band scrolls into view, then the count-up runs.
  const value = useCountUp(started ? target : 0, 1500);

  return (
    <div className="text-center">
      <p className="font-display text-4xl font-semibold text-gold-400 sm:text-5xl">
        {prefix}
        {value.toLocaleString()}
        <span className="text-2xl sm:text-3xl">{suffix}</span>
      </p>
      <p className="mx-auto mt-3 max-w-[15rem] text-sm text-paper-200/65">
        {label}
      </p>
    </div>
  );
}

/** Count-up proof band bridging the feature cards into the testimonials. */
export default function StatsBand() {
  const ref = useRef(null);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setStarted(true);
          observer.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <section
      ref={ref}
      className="border-y border-ink-800/70 bg-gradient-to-b from-ink-900 to-ink-950 py-16 sm:py-20"
    >
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-10 px-5 sm:px-8 lg:grid-cols-4">
        {STATS.map((stat) => (
          <Stat key={stat.label} {...stat} started={started} />
        ))}
      </div>
    </section>
  );
}
