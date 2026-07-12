import { useState } from "react";
import Reveal from "./Reveal";

const FAQS = [
  {
    q: "Is it really free?",
    a: "Yes — upload a resume and get your ATS and readability scores, your gap map, and a mock interview at no cost. No card required to see where you stand.",
  },
  {
    q: "What file types can I upload?",
    a: "PDF or DOCX, up to 5MB. We detect the real file type by inspecting the bytes, not the extension, so a mislabelled file is caught before it ever reaches the parser.",
  },
  {
    q: "How accurate is the ATS score?",
    a: "The ATS score is deterministic and rule-based — built on the same screening rules real applicant-tracking systems apply — so it's repeatable, not a black-box guess. The readability score is judged separately, the way a hiring manager reads.",
  },
  {
    q: "Do I need a job description?",
    a: "Only for the gap map and mock interview, which compare your resume against a specific role. Scoring and the profile rewrite work from your resume alone.",
  },
  {
    q: "Is my data safe?",
    a: "Your resume and results are stored under row-level security, so only your account can read them. Identical uploads are recognized by content hash, so nothing is re-processed or re-sent unnecessarily.",
  },
];

/** Accordion of common objections; one panel open at a time, height-animated. */
export default function Faq() {
  const [open, setOpen] = useState(0);

  return (
    <section id="faq" className="border-t border-ink-800 py-24 sm:py-32">
      <div className="mx-auto max-w-3xl px-5 sm:px-8">
        <Reveal>
          <p className="text-eyebrow font-semibold uppercase text-gold-400">
            Questions
          </p>
          <h2 className="mt-4 font-display text-display-lg font-medium text-paper-50">
            Everything you're about to ask.
          </h2>
        </Reveal>

        <Reveal className="mt-12">
          <dl className="divide-y divide-ink-800">
            {FAQS.map((item, index) => {
              const isOpen = open === index;
              return (
                <div key={item.q}>
                  <dt>
                    <button
                      type="button"
                      onClick={() => setOpen(isOpen ? -1 : index)}
                      aria-expanded={isOpen}
                      className="flex w-full items-center justify-between gap-6 py-5 text-left"
                    >
                      <span className="font-display text-lg font-medium text-paper-50">
                        {item.q}
                      </span>
                      <span
                        aria-hidden="true"
                        className={`flex h-8 w-8 flex-none items-center justify-center rounded-full border text-gold-400 transition-all duration-300 ${
                          isOpen
                            ? "rotate-45 border-gold-600/60 bg-gold-500/10"
                            : "border-ink-600"
                        }`}
                      >
                        <svg
                          viewBox="0 0 24 24"
                          className="h-4 w-4"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                        >
                          <path d="M12 5v14M5 12h14" />
                        </svg>
                      </span>
                    </button>
                  </dt>
                  <dd
                    className={`grid transition-all duration-300 ease-out ${
                      isOpen
                        ? "grid-rows-[1fr] opacity-100"
                        : "grid-rows-[0fr] opacity-0"
                    }`}
                  >
                    <div className="overflow-hidden">
                      <p className="pb-6 pr-14 text-sm leading-relaxed text-paper-200/75">
                        {item.a}
                      </p>
                    </div>
                  </dd>
                </div>
              );
            })}
          </dl>
        </Reveal>
      </div>
    </section>
  );
}
