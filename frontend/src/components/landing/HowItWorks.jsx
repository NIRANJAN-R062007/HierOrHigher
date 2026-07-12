import Reveal from "./Reveal";

const STEPS = [
  {
    number: "01",
    title: "Upload once",
    body: "Drop in your resume — PDF or DOCX. We parse it into structured data, so nothing ever gets retyped.",
  },
  {
    number: "02",
    title: "See where you stand",
    body: "Two scores — ATS and human — plus your exact gaps against any job description, together on one dashboard.",
  },
  {
    number: "03",
    title: "Fix, rehearse, apply",
    body: "Rewrite bullets, drill a mock interview built from your own resume, and ship a profile that actually gets read.",
  },
];

/** Three-step explainer bridging the hero promise into the feature cards. */
export default function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="bg-gradient-to-b from-transparent to-ink-900 py-24 sm:py-32"
    >
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <p className="text-eyebrow font-semibold uppercase text-gold-400">
            How it works
          </p>
          <h2 className="mt-4 max-w-2xl font-display text-display-lg font-medium text-paper-50">
            Three steps from upload to shortlist.
          </h2>
        </Reveal>

        <div className="relative mt-16 grid gap-10 sm:grid-cols-3">
          {/* Hairline connector threading the three step markers on desktop. */}
          <div
            aria-hidden="true"
            className="absolute inset-x-0 top-7 hidden h-px bg-gradient-to-r from-transparent via-ink-600/60 to-transparent sm:block"
          />
          {STEPS.map((step, index) => (
            <Reveal key={step.number} delay={index * 110}>
              <div className="relative">
                <span className="relative z-10 flex h-14 w-14 items-center justify-center rounded-2xl border border-gold-600/40 bg-ink-900 font-display text-lg font-semibold text-gold-400">
                  {step.number}
                </span>
                <h3 className="mt-6 font-display text-xl font-semibold text-paper-50">
                  {step.title}
                </h3>
                <p className="mt-3 max-w-xs text-sm leading-relaxed text-paper-200/75">
                  {step.body}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
