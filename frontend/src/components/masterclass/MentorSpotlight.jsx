import { useRef } from "react";
import Reveal from "../landing/Reveal";

const CREDENTIALS = [
  "Ex-recruiting lead across enterprise SaaS and fintech",
  "Built the screening rubric her old team still uses",
  "Guest resume reviewer for three university career centers",
];

/** Instructor spotlight with a cursor-tracking 3D tilt on the profile card. */
export default function MentorSpotlight() {
  const cardRef = useRef(null);

  const handleMove = (event) => {
    const node = cardRef.current;
    if (!node || window.matchMedia("(prefers-reduced-motion: reduce)").matches)
      return;
    const rect = node.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    node.style.transform = `perspective(900px) rotateX(${(-y * 6).toFixed(2)}deg) rotateY(${(x * 8).toFixed(2)}deg)`;
  };

  const handleLeave = () => {
    if (cardRef.current) cardRef.current.style.transform = "";
  };

  return (
    <section className="relative overflow-hidden bg-ink-950 py-24 sm:py-32">
      <div
        aria-hidden="true"
        className="absolute right-[6%] top-[12%] h-64 w-64 animate-float-slow rounded-full bg-gold-500/[0.07] blur-3xl"
      />
      <div className="relative mx-auto grid max-w-6xl items-center gap-14 px-5 sm:px-8 lg:grid-cols-2">
        <Reveal>
          <p className="text-eyebrow font-semibold uppercase text-gold-400">
            Your instructor
          </p>
          <h2 className="mt-4 font-display text-display-lg font-medium text-paper-50">
            Taught by someone whose job was saying no.
          </h2>
          <p className="mt-6 max-w-xl text-base leading-relaxed text-paper-200/80">
            Leah Fernandes ran recruiting pipelines for nine years — more than
            40,000 resumes across two Fortune 500 hiring loops. She teaches the
            read from the other side of the desk: what gets skipped, what gets
            circled, and what gets forwarded to the hiring manager with a note.
          </p>
          <ul className="mt-8 space-y-3">
            {CREDENTIALS.map((credential) => (
              <li
                key={credential}
                className="flex items-start gap-3 text-sm text-paper-200/75"
              >
                <span
                  aria-hidden="true"
                  className="mt-1.5 text-[0.5rem] text-gold-500"
                >
                  ◆
                </span>
                {credential}
              </li>
            ))}
          </ul>
        </Reveal>

        <Reveal delay={120}>
          <figure
            ref={cardRef}
            onMouseMove={handleMove}
            onMouseLeave={handleLeave}
            className="rounded-3xl border border-ink-700/70 bg-ink-800/60 p-10 shadow-lift transition-transform duration-200 ease-out will-change-transform"
          >
            <div className="flex items-center gap-5">
              <span className="flex h-16 w-16 items-center justify-center rounded-full border border-gold-600/50 bg-gold-500/10 font-display text-xl font-semibold text-gold-300">
                LF
              </span>
              <figcaption>
                <p className="font-display text-xl font-semibold text-paper-50">
                  Leah Fernandes
                </p>
                <p className="mt-1 text-sm text-paper-200/60">
                  Ex-recruiting lead · 40,000+ resumes read
                </p>
              </figcaption>
            </div>
            <blockquote className="mt-8 border-t border-ink-700/70 pt-8 text-lg leading-relaxed text-paper-200/85">
              “I rejected thousands of qualified people because their resumes
              hid the evidence. This session is everything I wish I could have
              told them on the way out.”
            </blockquote>
          </figure>
        </Reveal>
      </div>
    </section>
  );
}
