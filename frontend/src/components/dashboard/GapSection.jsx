import ErrorState from "./ErrorState";
import SkillRadar from "./SkillRadar";
import StepLoader from "./StepLoader";

const GAP_STEPS = [
  "Reading the job description…",
  "Extracting the real requirements…",
  "Comparing against your resume semantically…",
];

function ChipList({ title, items, tone }) {
  const toneClasses =
    tone === "matched"
      ? "border-emerald-500/30 bg-emerald-900/40 text-emerald-300"
      : "border-red-500/30 bg-red-900/40 text-red-300";
  return (
    <div>
      <h4 className="text-sm font-semibold text-paper-200">
        {title}{" "}
        <span className="font-normal text-paper-200/50">({items.length})</span>
      </h4>
      <ul className="mt-3 flex flex-wrap gap-2">
        {items.length === 0 && (
          <li className="text-sm text-paper-200/60">None</li>
        )}
        {items.map((skill) => (
          <li
            key={skill}
            className={`rounded-full border px-3.5 py-1.5 text-sm font-medium ${toneClasses}`}
          >
            {tone === "matched" ? "✓ " : "+ "}
            {skill}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Module 5.2: JD intake + matched-vs-missing comparison + match bar. */
export default function GapSection({
  resume,
  gap,
  jdText,
  onJdTextChange,
  running,
  error,
  onRun,
}) {
  const ready = Boolean(resume);
  const canRun = ready && jdText.trim().length >= 40 && !running;

  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card">
      {!ready && (
        <p className="text-sm text-paper-200/60">
          Upload a resume first — the gap mapper compares the job description
          against your parsed resume.
        </p>
      )}
      {ready && (
        <>
          <label htmlFor="jd-text" className="block text-sm font-semibold text-paper-200">
            Paste the job description
          </label>
          <textarea
            id="jd-text"
            rows={7}
            value={jdText}
            onChange={(event) => onJdTextChange(event.target.value)}
            placeholder="Paste the full posting — requirements, responsibilities, all of it. More text means a sharper map."
            className="mt-2 w-full rounded-xl border border-ink-700 bg-ink-900 px-4 py-3 text-sm text-paper-50 placeholder-paper-200/40 transition-colors focus:border-gold-500"
          />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={!canRun}
              onClick={onRun}
              className="rounded-full bg-gold-500 px-6 py-2.5 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {gap ? "Re-map against this JD" : "Map my gaps"}
            </button>
            {jdText.trim().length > 0 && jdText.trim().length < 40 && (
              <p className="text-xs text-paper-200/60">
                Paste at least a few sentences of the posting.
              </p>
            )}
          </div>

          {running && (
            <div className="mt-5 max-w-sm">
              <StepLoader steps={GAP_STEPS} />
            </div>
          )}
          {error && !running && (
            <div className="mt-4">
              <ErrorState message={error} onRetry={canRun ? onRun : null} />
            </div>
          )}

          {gap && !running && (
            <div className="mt-6 border-t border-ink-700 pt-6">
              <div className="flex items-end justify-between">
                <p className="text-sm font-semibold text-paper-200">Match strength</p>
                <p className="font-display text-3xl font-semibold text-paper-50">
                  {gap.match_percentage}
                  <span className="text-base font-medium text-paper-200/60">%</span>
                </p>
              </div>
              <div
                role="progressbar"
                aria-valuenow={gap.match_percentage}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Job match percentage"
                className="mt-2 h-2.5 overflow-hidden rounded-full bg-ink-700"
              >
                <div
                  className="h-full rounded-full bg-gradient-to-r from-gold-600 to-gold-400 transition-all duration-1000 ease-out"
                  style={{ width: `${gap.match_percentage}%` }}
                />
              </div>
              {gap.categories && (
                <div className="mt-6 flex justify-center">
                  <SkillRadar categories={gap.categories} />
                </div>
              )}
              <div className="mt-6 grid gap-6 md:grid-cols-2">
                <ChipList title="You already cover" items={gap.matched} tone="matched" />
                <ChipList title="Missing for this role" items={gap.missing} tone="missing" />
              </div>
              {gap.cached && (
                <p role="status" className="mt-4 text-xs text-paper-200/60">
                  Served from cache — this exact resume + JD pair was mapped before.
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
