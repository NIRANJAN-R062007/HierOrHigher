const CHIP_TONES = {
  matched: "border-emerald-500/30 bg-emerald-900/40 text-emerald-300",
  missing: "border-red-500/30 bg-red-900/40 text-red-300",
};

function Chips({ label, items, tone }) {
  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-paper-200/60">
        {label} <span className="font-normal">({items.length})</span>
      </h4>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {items.length === 0 && <li className="text-sm text-paper-200/50">None</li>}
        {items.map((skill) => (
          <li
            key={skill}
            className={`rounded-full border px-3 py-1 text-xs font-medium ${CHIP_TONES[tone]}`}
          >
            {tone === "matched" ? "✓ " : "+ "}
            {skill}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * One applicant on the ranked screening list: their match percentage, then
 * what they cover and what they don't.
 *
 * Uses the same matched/missing chip language as the student-facing gap
 * report because it is literally the same comparison — one matching core,
 * read from two sides.
 */
export default function ApplicantCard({ applicant, rank }) {
  const { name, email, match_percentage: match, matched, missing } = applicant;
  const submitted = new Date(applicant.created_at);

  return (
    <li className="rounded-2xl border border-ink-700 bg-ink-800 p-5 shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ink-700 text-xs font-semibold text-paper-200/70">
            {rank}
          </span>
          <div>
            <p className="font-display text-lg font-semibold text-paper-50">
              {name || "Unnamed candidate"}
            </p>
            <p className="text-sm text-paper-200/60">
              {email || "No email provided"}
              {Number.isNaN(submitted.valueOf())
                ? null
                : ` · applied ${submitted.toLocaleDateString()}`}
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className="font-display text-2xl font-semibold text-paper-50">
            {match}
            <span className="text-sm font-medium text-paper-200/60">%</span>
          </p>
          <p className="text-xs text-paper-200/50">match</p>
        </div>
      </div>

      <div
        role="progressbar"
        aria-valuenow={match}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${name || "Candidate"} match percentage`}
        className="mt-4 h-2 overflow-hidden rounded-full bg-ink-700"
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-gold-600 to-gold-400 transition-all duration-1000 ease-out"
          style={{ width: `${match}%` }}
        />
      </div>

      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        <Chips label="Covers" items={matched} tone="matched" />
        <Chips label="Missing" items={missing} tone="missing" />
      </div>
    </li>
  );
}
