import ErrorState from "./ErrorState";
import StepLoader from "./StepLoader";

const INTERVIEW_STEPS = [
  "Reviewing your projects and history…",
  "Studying the target role…",
  "Writing questions an interviewer would actually ask…",
];

const CATEGORY_STYLES = {
  Technical: "bg-paper-50/10 text-paper-50 border border-paper-50/15",
  Behavioral: "bg-gold-500/15 text-gold-300 border border-gold-500/40",
  "Role-Fit": "bg-emerald-900/40 text-emerald-300 border border-emerald-500/30",
};

/** Module 5.3: personalized question set grouped visually by category tags. */
export default function InterviewSection({
  gap,
  interviewSet,
  running,
  error,
  onGenerate,
}) {
  const ready = Boolean(gap);

  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card">
      {!ready && (
        <p className="text-sm text-paper-200/60">
          Run the gap mapper first — your mock interview is built from your
          resume, the target job, and the gaps between them.
        </p>
      )}
      {ready && !interviewSet && !running && (
        <div className="flex flex-col items-start gap-3">
          <p className="text-sm text-paper-200/70">
            8–10 questions generated from <em>your</em> projects, work history,
            and identified gaps — tagged Technical, Behavioral, and Role-Fit.
          </p>
          <button
            type="button"
            onClick={onGenerate}
            className="rounded-full bg-gold-500 px-6 py-2.5 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-95"
          >
            Generate my interview
          </button>
        </div>
      )}
      {running && (
        <div className="max-w-sm">
          <StepLoader steps={INTERVIEW_STEPS} />
        </div>
      )}
      {error && !running && (
        <div className="mt-2">
          <ErrorState message={error} onRetry={onGenerate} />
        </div>
      )}
      {interviewSet && !running && (
        <>
          <ol className="space-y-3">
            {interviewSet.questions.map((item, index) => (
              <li
                key={item.question}
                className="rounded-xl border border-ink-700 bg-ink-900 p-4 transition-shadow hover:shadow-card"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-paper-200/50">
                    Q{index + 1}
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      CATEGORY_STYLES[item.category] || "bg-ink-700 text-paper-200"
                    }`}
                  >
                    {item.category}
                  </span>
                </div>
                <p className="mt-2.5 text-sm leading-relaxed text-paper-50">
                  {item.question}
                </p>
              </li>
            ))}
          </ol>
          {interviewSet.cached && (
            <p role="status" className="mt-4 text-xs text-paper-200/60">
              Served from cache — this set was already generated for this
              resume + JD pair.
            </p>
          )}
        </>
      )}
    </div>
  );
}
