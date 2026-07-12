import Reveal from "../landing/Reveal";

const SESSIONS = [
  {
    number: "01",
    title: "Inside the ATS black box",
    minutes: 14,
    body: "How screening software actually parses, tokenizes, and scores your resume — and the formatting choices that silently zero out entire sections.",
  },
  {
    number: "02",
    title: "The six-second human read",
    minutes: 17,
    body: "Where a hiring manager's eye really lands, replayed from anonymized screen recordings — and how to place your evidence exactly there.",
  },
  {
    number: "03",
    title: "Gap math, done honestly",
    minutes: 21,
    body: "Turn any job description into a truthful checklist: what you already cover, what you can bridge in two weeks, and what to stop pretending.",
  },
  {
    number: "04",
    title: "Interviews from your own resume",
    minutes: 19,
    body: "Practice against questions generated from your actual projects and gaps — because that is precisely how interviewers prepare for you.",
  },
  {
    number: "05",
    title: "The rewrite, live",
    minutes: 21,
    body: "A real attendee profile rebuilt on stage — headline, About section, and project bullets — with before and after scores side by side.",
  },
];

/** Numbered session timeline with scroll reveals and gold hover accents. */
export default function CurriculumTimeline() {
  return (
    <section id="curriculum" className="bg-ink-950 py-24 sm:py-32">
      <div className="mx-auto max-w-4xl px-5 sm:px-8">
        <Reveal>
          <p className="text-eyebrow font-semibold uppercase text-gold-400">
            The curriculum
          </p>
          <h2 className="mt-4 max-w-2xl font-display text-display-lg font-medium text-paper-50">
            Five sessions. Ninety-two minutes. No filler.
          </h2>
        </Reveal>

        <div className="relative mt-16 space-y-4 border-l border-ink-700/70 pl-8">
          {SESSIONS.map((session, index) => (
            <Reveal key={session.number} delay={index * 80}>
              <article className="group relative rounded-2xl border border-transparent p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-ink-700/70 hover:bg-ink-800/50">
                {/* Node dot sitting on the timeline rule. */}
                <span
                  aria-hidden="true"
                  className="absolute -left-[37px] top-8 h-2.5 w-2.5 rounded-full bg-ink-600 transition-all duration-300 group-hover:bg-gold-500 group-hover:shadow-gold-glow"
                />
                <div className="flex items-baseline justify-between gap-4">
                  <span className="font-display text-sm font-semibold text-gold-500">
                    {session.number}
                  </span>
                  <span className="text-xs font-medium uppercase tracking-widest text-paper-200/50">
                    {session.minutes} min
                  </span>
                </div>
                <h3 className="mt-2 font-display text-2xl font-medium text-paper-50 transition-colors duration-300 group-hover:text-gold-200">
                  {session.title}
                </h3>
                <p className="mt-3 max-w-xl text-sm leading-relaxed text-paper-200/75">
                  {session.body}
                </p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
