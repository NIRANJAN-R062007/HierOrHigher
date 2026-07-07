import ScoreGauge from "./ScoreGauge";

function CheckIcon({ passed }) {
  return passed ? (
    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="m5 13 4 4L19 7" />
      </svg>
    </span>
  ) : (
    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600">
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
        <path d="M6 6l12 12M18 6 6 18" />
      </svg>
    </span>
  );
}

const CHECK_LABELS = {
  file_format: "File format",
  section_headers: "Section headers",
  contact_info: "Contact info",
  quantified_achievements: "Quantified achievements",
  action_verbs: "Action verbs",
  length: "Length",
  parseable_structure: "Parseable structure",
};

/** Module 5.1 results: dual gauges + what drove each score. */
export default function ScoreSection({ resume }) {
  if (!resume) {
    return (
      <p className="rounded-2xl border border-paper-200 bg-white p-8 text-center text-sm text-ink-400 shadow-card">
        Upload a resume above to see your ATS and readability scores.
      </p>
    );
  }

  const { parsed, ats_score: ats, human_score: human } = resume;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="rounded-2xl border border-paper-200 bg-white p-6 shadow-card">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-display text-lg font-semibold text-ink-900">ATS score</h3>
            <p className="mt-1 text-xs text-ink-400">
              Deterministic rule-based checks — the way screening software reads you.
            </p>
          </div>
          <ScoreGauge label="ATS" value={ats.value} size={110} />
        </div>
        <ul className="mt-4 space-y-2.5">
          {ats.breakdown.map((check) => (
            <li key={check.check} className="flex items-start gap-2.5 text-sm">
              <CheckIcon passed={check.passed} />
              <div>
                <span className="font-medium text-ink-900">
                  {CHECK_LABELS[check.check] || check.check}
                </span>
                {check.detail && (
                  <span className="text-ink-500"> — {check.detail}</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-2xl border border-paper-200 bg-white p-6 shadow-card">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-display text-lg font-semibold text-ink-900">
              Human readability
            </h3>
            <p className="mt-1 text-xs text-ink-400">
              AI judgment of clarity, impact statements, and quantified wins.
            </p>
          </div>
          <ScoreGauge label="Human" value={human.value} size={110} />
        </div>
        <ul className="mt-4 space-y-2.5">
          {human.breakdown.map((observation) => (
            <li key={observation} className="flex items-start gap-2.5 text-sm text-ink-700">
              <span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-gold-500" />
              {observation}
            </li>
          ))}
        </ul>
        {parsed?.name && (
          <p className="mt-5 border-t border-paper-200 pt-4 text-xs text-ink-400">
            Parsed for <span className="font-medium text-ink-700">{parsed.name}</span>
            {" · "}{parsed.skills.length} skills{" · "}
            {parsed.experience.length} roles{" · "}{parsed.projects.length} projects
          </p>
        )}
      </div>
    </div>
  );
}
