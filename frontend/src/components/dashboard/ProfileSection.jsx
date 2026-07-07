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
      className="rounded-full border border-paper-300 px-3 py-1 text-xs font-medium text-ink-500 transition-all hover:border-ink-400 hover:text-ink-900 active:scale-95"
    >
      {copied ? "Copied ✓" : "Copy"}
    </button>
  );
}

function DraftBlock({ title, text, label }) {
  return (
    <div className="rounded-xl border border-paper-200 bg-paper-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-ink-700">{title}</h4>
        <CopyButton text={text} label={label} />
      </div>
      <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink-900">
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
    <div className="rounded-2xl border border-paper-200 bg-white p-6 shadow-card">
      {!ready && (
        <p className="text-sm text-ink-400">
          Upload a resume first — the optimizer rewrites your parsed
          achievements into LinkedIn-ready copy.
        </p>
      )}
      {ready && !profileDraft && !running && (
        <div className="flex flex-col items-start gap-3">
          <p className="text-sm text-ink-500">
            A headline, an About section, and outcome-first project rewrites —
            each in two tones, ready to paste into LinkedIn.
          </p>
          <button
            type="button"
            onClick={onGenerate}
            className="rounded-full bg-ink-900 px-6 py-2.5 text-sm font-semibold text-paper-50 transition-all hover:bg-ink-700 active:scale-95"
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
            className="inline-flex rounded-full border border-paper-300 bg-paper-100 p-1"
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
                    ? "bg-ink-900 text-paper-50 shadow-sm"
                    : "text-ink-500 hover:text-ink-900"
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
            <p role="status" className="mt-4 text-xs text-ink-400">
              Served from cache — drafts were already generated for this resume.
            </p>
          )}
        </>
      )}
    </div>
  );
}
