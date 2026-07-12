import Reveal from "./Reveal";

const MODULES = [
  {
    title: "Resume Parser + Score",
    tagline: "Two scores. Zero guesswork.",
    body: "A deterministic ATS score built on real screening rules, and a human-readability score judged like a hiring manager would — each with a line-by-line breakdown of what to fix.",
    icon: (
      <path d="M9 12h6m-6 4h6M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm7 0v5h5" />
    ),
  },
  {
    title: "Gap-to-Job Mapper",
    tagline: "The exact skills between you and the offer.",
    body: "Paste the job description. Semantic matching — not keyword bingo — shows what you already cover, what's genuinely missing, and your true match percentage.",
    icon: (
      <path d="M12 3v18m0-18 4 4m-4-4-4 4m4 14 4-4m-4 4-4-4M3 12h4m10 0h4" />
    ),
  },
  {
    title: "Mock Interview Generator",
    tagline: "Questions written from your resume, not a bank.",
    body: "8–10 questions built from your actual projects, your work history, and your identified gaps — tagged Technical, Behavioral, and Role-Fit so you can drill deliberately.",
    icon: (
      <path d="M8 10h8m-8 4h5m-9 7V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H8l-4 4Z" />
    ),
  },
  {
    title: "LinkedIn / Portfolio Optimizer",
    tagline: "Your wins, rewritten to be read.",
    body: "Headline, About section, and project descriptions rebuilt in an outcome-first tone — each in two variants, concise and detailed, ready to paste.",
    icon: (
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4V9h4v1.5A6 6 0 0 1 16 8ZM2 9h4v12H2V9Zm2-7a2 2 0 1 1 0 4 2 2 0 0 1 0-4Z" />
    ),
  },
];

/** Four premium cards with hover elevation — one per module. */
export default function ModuleShowcase() {
  return (
    <section id="modules" className="bg-ink-900 py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <p className="text-eyebrow font-semibold uppercase text-gold-400">
            One resume in. Four weapons out.
          </p>
          <h2 className="mt-4 max-w-2xl font-display text-display-lg font-medium text-paper-50">
            Everything reads from a single parsed resume — you never re-enter
            anything.
          </h2>
        </Reveal>
        <div className="mt-14 grid gap-6 sm:grid-cols-2">
          {MODULES.map((module, index) => (
            <Reveal key={module.title} delay={index * 90}>
              <article className="group relative h-full overflow-hidden rounded-2xl border border-ink-700/70 bg-ink-800/60 p-8 transition-all duration-300 hover:-translate-y-1.5 hover:border-gold-600/50 hover:shadow-lift">
                <span
                  aria-hidden="true"
                  className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gold-500/70 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100"
                />
                <span
                  aria-hidden="true"
                  className="absolute right-7 top-7 font-display text-5xl font-semibold text-ink-700/40 transition-colors duration-300 group-hover:text-gold-600/30"
                >
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-ink-700/70 text-gold-400 transition-all duration-300 group-hover:scale-105 group-hover:bg-gold-500/15">
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 24 24"
                    className="h-5 w-5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    {module.icon}
                  </svg>
                </div>
                <h3 className="mt-6 font-display text-xl font-semibold text-paper-50">
                  {module.title}
                </h3>
                <p className="mt-1.5 text-sm font-semibold text-gold-400">
                  {module.tagline}
                </p>
                <p className="mt-4 text-sm leading-relaxed text-paper-200/75">
                  {module.body}
                </p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
