import { useState } from "react";
import ErrorState from "./ErrorState";
import StepLoader from "./StepLoader";

const PROFILE_STEPS = [
  "Re-reading your achievements…",
  "Drafting concise and detailed variants…",
];

function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      aria-label={`Copy ${label}`}
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1600);
      }}
      className="rounded-full border border-ink-700 px-3 py-1 text-xs font-medium text-paper-200/70 transition-all hover:border-ink-500 hover:text-paper-50 active:scale-95"
    >
      {copied ? "Copied ✓" : "Copy"}
    </button>
  );
}

function DraftBlock({ title, text, label }) {
  return (
    <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-paper-200">{title}</h4>
        <CopyButton text={text} label={label} />
      </div>
      <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-paper-50">
        {text}
      </p>
    </div>
  );
}

/** Module 5.4: LinkedIn drafts with a Concise/Detailed tone toggle. */
export default function ProfileSection({
  resume,
  profileDraft,
  running,
  error,
  onGenerate,
}) {
  const [tone, setTone] = useState("concise");
  const ready = Boolean(resume);

  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card">
      {!ready && (
        <p className="text-sm text-paper-200/60">
          Upload a resume first — the optimizer rewrites your parsed
          achievements into LinkedIn-ready copy.
        </p>
      )}
      {ready && !profileDraft && !running && (
        <div className="flex flex-col items-start gap-3">
          <p className="text-sm text-paper-200/70">
            A headline, an About section, and outcome-first project rewrites —
            each in two tones, ready to paste into LinkedIn.
          </p>
          <button
            type="button"
            onClick={onGenerate}
            className="rounded-full bg-gold-500 px-6 py-2.5 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-95"
          >
            Write my profile
          </button>
        </div>
      )}
      {running && (
        <div className="max-w-sm">
          <StepLoader steps={PROFILE_STEPS} />
        </div>
      )}
      {error && !running && (
        <div className="mt-2">
          <ErrorState message={error} onRetry={onGenerate} />
        </div>
      )}
      {profileDraft && !running && (
        <>
          <div
            role="radiogroup"
            aria-label="Tone"
            className="inline-flex rounded-full border border-ink-700 bg-ink-900 p-1"
          >
            {["concise", "detailed"].map((option) => (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={tone === option}
                onClick={() => setTone(option)}
                className={`rounded-full px-4 py-1.5 text-sm font-medium capitalize transition-all ${
                  tone === option
                    ? "bg-gold-500 text-ink-950 shadow-sm"
                    : "text-paper-200/60 hover:text-paper-50"
                }`}
              >
                {option}
              </button>
            ))}
          </div>

          <div className="mt-4 space-y-4">
            <DraftBlock
              title="LinkedIn headline"
              label="headline"
              text={profileDraft.headline[tone]}
            />
            <DraftBlock
              title="About section"
              label="about section"
              text={profileDraft.about[tone]}
            />
            {profileDraft.project_descriptions.map((project) => (
              <DraftBlock
                key={project.title}
                title={`Project — ${project.title}`}
                label={`${project.title} description`}
                text={project[tone]}
              />
            ))}
          </div>
          {profileDraft.cached && (
            <p role="status" className="mt-4 text-xs text-paper-200/60">
              Served from cache — drafts were already generated for this resume.
            </p>
          )}
        </>
      )}
    </div>
  );
}
