import { Link } from "react-router-dom";

const WORDS = [
  { text: "Get" },
  { text: "read." },
  { text: "Get" },
  { text: "remembered." },
  { text: "Get", gold: true },
  { text: "hired.", gold: true },
];

/** Event-style hero: staggered word reveal, floating gold orbs, shine headline. */
export default function MasterclassHero() {
  return (
    <section className="relative isolate overflow-hidden bg-ink-950">
      {/* Slow-panning ambient glow, mirrored from the main landing hero. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 animate-glow-pan opacity-90"
        style={{
          background:
            "radial-gradient(55% 75% at 50% 0%, rgba(201,169,97,0.16), transparent 60%)," +
            "radial-gradient(45% 65% at 12% 45%, rgba(58,71,99,0.45), transparent 65%)," +
            "radial-gradient(65% 85% at 88% 80%, rgba(201,169,97,0.10), transparent 55%)",
          backgroundSize: "180% 180%",
        }}
      />
      <div
        aria-hidden="true"
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,13,0.25) 0%, rgba(6,8,13,0) 40%, rgba(6,8,13,0.9) 100%)",
        }}
      />
      {/* Floating ambient orbs. */}
      <div
        aria-hidden="true"
        className="absolute left-[10%] top-[24%] h-44 w-44 animate-float rounded-full bg-gold-500/10 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="absolute right-[8%] top-[42%] h-60 w-60 animate-float-slow rounded-full bg-ink-500/30 blur-3xl"
      />

      <div className="relative mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center px-5 pb-24 pt-32 text-center sm:px-8">
        <p className="inline-flex animate-fade-up items-center gap-2.5 rounded-full border border-gold-600/40 bg-gold-500/10 px-4 py-2 text-eyebrow font-semibold uppercase text-gold-300">
          <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-gold-400" />
          Free live masterclass
        </p>

        <h1 className="mt-8 max-w-4xl font-display text-display-xl font-medium text-paper-50">
          {WORDS.map((word, index) => (
            <span
              key={`${word.text}-${index}`}
              className="mr-[0.28em] inline-block overflow-hidden pb-1 align-bottom"
            >
              <span
                className="inline-block animate-word-rise"
                style={{ animationDelay: `${160 + index * 110}ms` }}
              >
                {word.gold ? (
                  <span className="text-gold-shine">{word.text}</span>
                ) : (
                  word.text
                )}
              </span>
            </span>
          ))}
        </h1>

        <p
          className="mt-7 max-w-2xl animate-fade-up text-lg leading-relaxed text-paper-200/85"
          style={{ animationDelay: "780ms" }}
        >
          Ninety-two minutes, live: the rubrics ATS software scores you with,
          the six seconds a recruiter actually spends on your resume, and a
          real profile rebuilt on stage — so yours never gets skimmed past
          again.
        </p>

        <div
          className="mt-10 flex animate-fade-up flex-col gap-4 sm:flex-row sm:items-center"
          style={{ animationDelay: "920ms" }}
        >
          <Link
            to="/signup"
            className="rounded-full bg-gold-500 px-8 py-3.5 text-center text-base font-semibold text-ink-950 shadow-gold-glow transition-all hover:-translate-y-0.5 hover:bg-gold-400 active:translate-y-0 active:scale-95"
          >
            Reserve your free seat
          </Link>
          <a
            href="#curriculum"
            className="px-2 py-3 text-center text-sm font-medium text-paper-200/75 transition-colors hover:text-paper-50"
          >
            See the curriculum ↓
          </a>
        </div>

        <p
          className="mt-12 flex animate-fade-up flex-wrap items-center justify-center gap-x-4 gap-y-2 text-xs font-medium uppercase tracking-[0.18em] text-paper-200/55"
          style={{ animationDelay: "1060ms" }}
        >
          Sat, July 25
          <span aria-hidden="true" className="text-[0.5rem] text-gold-600">
            ◆
          </span>
          92 minutes
          <span aria-hidden="true" className="text-[0.5rem] text-gold-600">
            ◆
          </span>
          Live online + replay
        </p>
      </div>
    </section>
  );
}
