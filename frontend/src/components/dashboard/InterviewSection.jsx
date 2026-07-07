import ErrorState from "./ErrorState";
import StepLoader from "./StepLoader";

const INTERVIEW_STEPS = [
  "Reviewing your projects and history…",
  "Studying the target role…",
  "Writing questions an interviewer would actually ask…",
];

const CATEGORY_STYLES = {
  Technical: "bg-ink-900 text-paper-50",
  Behavioral: "bg-gold-500/15 text-gold-700 border border-gold-500/40",
  "Role-Fit": "bg-emerald-100 text-emerald-800",
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
    <div className="rounded-2xl border border-paper-200 bg-white p-6 shadow-card">
      {!ready && (
        <p className="text-sm text-ink-400">
          Run the gap mapper first — your mock interview is built from your
          resume, the target job, and the gaps between them.
        </p>
      )}
      {ready && !interviewSet && !running && (
        <div className="flex flex-col items-start gap-3">
          <p className="text-sm text-ink-500">
            8–10 questions generated from <em>your</em> projects, work history,
            and identified gaps — tagged Technical, Behavioral, and Role-Fit.
          </p>
          <button
            type="button"
            onClick={onGenerate}
            className="rounded-full bg-ink-900 px-6 py-2.5 text-sm font-semibold text-paper-50 transition-all hover:bg-ink-700 active:scale-95"
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
                className="rounded-xl border border-paper-200 bg-paper-50 p-4 transition-shadow hover:shadow-card"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-ink-400">
                    Q{index + 1}
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      CATEGORY_STYLES[item.category] || "bg-paper-200 text-ink-700"
                    }`}
                  >
                    {item.category}
                  </span>
                </div>
                <p className="mt-2.5 text-sm leading-relaxed text-ink-900">
                  {item.question}
                </p>
              </li>
            ))}
          </ol>
          {interviewSet.cached && (
            <p role="status" className="mt-4 text-xs text-ink-400">
              Served from cache — this set was already generated for this
              resume + JD pair.
            </p>
          )}
        </>
      )}
    </div>
  );
}
