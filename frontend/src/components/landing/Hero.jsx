import { Link } from "react-router-dom";
import HeroScoreCard from "./HeroScoreCard";

/** Cinematic full-bleed hero: layered gold-on-ink gradients, editorial type. */
export default function Hero() {
  return (
    <section className="relative isolate overflow-hidden bg-ink-950">
      {/* Slow-panning ambient glow in place of hero video. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 animate-glow-pan opacity-90"
        style={{
          background:
            "radial-gradient(60% 80% at 20% 10%, rgba(201,169,97,0.14), transparent 60%)," +
            "radial-gradient(50% 70% at 85% 30%, rgba(58,71,99,0.5), transparent 65%)," +
            "radial-gradient(70% 90% at 50% 110%, rgba(201,169,97,0.10), transparent 55%)",
          backgroundSize: "180% 180%",
        }}
      />
      <div
        aria-hidden="true"
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, rgba(6,8,13,0.2) 0%, rgba(6,8,13,0) 40%, rgba(6,8,13,0.9) 100%)",
        }}
      />

      <div className="relative mx-auto grid min-h-screen max-w-6xl grid-cols-1 items-center gap-12 px-5 pb-28 pt-32 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8">
        <div className="flex flex-col items-start">
          <p className="animate-fade-up text-eyebrow font-semibold uppercase text-gold-400">
            AI Career Readiness
          </p>
          <h1
            className="mt-6 animate-fade-up font-display text-display-xl font-medium text-paper-50"
            style={{ animationDelay: "120ms" }}
          >
            Know exactly where you stand — before the recruiter decides.
          </h1>
          <p
            className="mt-6 max-w-xl animate-fade-up text-lg leading-relaxed text-paper-200/85"
            style={{ animationDelay: "240ms" }}
          >
            Upload your resume once. HireOrHigher scores it the way ATS software
            and humans read it, maps the exact gaps to the job you want, writes
            your mock interview, and rewrites your profile — in minutes.
          </p>
          <div
            className="mt-10 flex animate-fade-up flex-col gap-4 sm:flex-row sm:items-center"
            style={{ animationDelay: "360ms" }}
          >
            <Link
              to="/signup"
              className="rounded-full bg-gold-500 px-8 py-3.5 text-center text-base font-semibold text-ink-950 shadow-gold-glow transition-all hover:-translate-y-0.5 hover:bg-gold-400 active:translate-y-0 active:scale-95"
            >
              Get your free score
            </Link>
            <a
              href="#how-it-works"
              className="px-2 py-3 text-center text-sm font-medium text-paper-200/75 transition-colors hover:text-paper-50"
            >
              See how it works ↓
            </a>
          </div>
        </div>

        <div
          className="hidden animate-fade-up justify-center lg:flex lg:justify-end"
          style={{ animationDelay: "480ms" }}
        >
          <HeroScoreCard />
        </div>
      </div>
    </section>
  );
}
