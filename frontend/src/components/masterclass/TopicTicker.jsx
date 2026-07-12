const TOPICS = [
  "ATS parsing rules",
  "The six-second scan",
  "Gap math, done honestly",
  "Outcome-first bullets",
  "Interviews from your own resume",
  "Headlines that get found",
  "Live resume teardown",
  "Recruiter screen recordings",
];

/** Infinite marquee of session topics; the track is duplicated for a seamless loop. */
export default function TopicTicker() {
  const track = [...TOPICS, ...TOPICS];

  return (
    <section
      aria-label="Masterclass topics"
      className="overflow-hidden border-y border-ink-800/70 bg-ink-900 py-5 [mask-image:linear-gradient(90deg,transparent,black_10%,black_90%,transparent)]"
    >
      <div className="flex w-max animate-marquee">
        {track.map((topic, index) => (
          <span
            key={`${topic}-${index}`}
            aria-hidden={index >= TOPICS.length ? "true" : undefined}
            className="flex items-center whitespace-nowrap"
          >
            <span className="text-xs font-semibold uppercase tracking-[0.22em] text-paper-200/55">
              {topic}
            </span>
            <span aria-hidden="true" className="px-8 text-[0.5rem] text-gold-600">
              ◆
            </span>
          </span>
        ))}
      </div>
    </section>
  );
}
