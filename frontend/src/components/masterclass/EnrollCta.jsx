import { Link } from "react-router-dom";
import Reveal from "../landing/Reveal";

/** Closing enrollment CTA: ambient glow, cohort badge, gold-glow button. */
export default function EnrollCta() {
  return (
    <section className="relative isolate overflow-hidden bg-ink-950 py-28 sm:py-36">
      <div
        aria-hidden="true"
        className="absolute inset-0 animate-glow-pan opacity-80"
        style={{
          background:
            "radial-gradient(50% 65% at 50% 100%, rgba(201,169,97,0.14), transparent 60%)," +
            "radial-gradient(45% 60% at 20% 20%, rgba(58,71,99,0.4), transparent 65%)",
          backgroundSize: "180% 180%",
        }}
      />
      <Reveal className="relative mx-auto max-w-3xl px-5 text-center sm:px-8">
        <p className="inline-flex items-center gap-2.5 rounded-full border border-gold-600/40 bg-gold-500/10 px-4 py-2 text-eyebrow font-semibold uppercase text-gold-300">
          <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-gold-400" />
          Next cohort · Sat, July 25 · Online
        </p>
        <h2 className="mt-8 font-display text-display-lg font-medium text-paper-50">
          One evening. Everything the rejection emails
          <span className="text-gold-400"> never explained.</span>
        </h2>
        <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-paper-200/80">
          Ninety-two minutes live, your questions answered on air, and the full
          replay in your HireOrHigher account. Cohorts cap at 500 seats so the
          teardown stays personal.
        </p>
        <Link
          to="/signup"
          className="mt-10 inline-block rounded-full bg-gold-500 px-9 py-4 text-base font-semibold text-ink-950 shadow-gold-glow transition-all hover:-translate-y-0.5 hover:bg-gold-400 active:translate-y-0 active:scale-95"
        >
          Reserve your free seat
        </Link>
        <p className="mt-6 text-xs font-medium uppercase tracking-[0.18em] text-paper-200/45">
          Free · No resume required to attend · Replay included
        </p>
      </Reveal>
    </section>
  );
}
