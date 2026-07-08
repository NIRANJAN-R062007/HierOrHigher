/**
 * Switch the active resume when more than one has been uploaded — every
 * section below re-renders from the selected resume's persisted results.
 */
export default function ResumeSwitcher({ resumes, activeId, onSelect, busy }) {
  if (resumes.length < 2) return null;

  return (
    <nav aria-label="Your resumes" className="flex flex-wrap items-center gap-2">
      <span className="mr-1 text-sm font-semibold text-ink-700">Resumes:</span>
      {resumes.map((resume) => {
        const active = resume.id === activeId;
        return (
          <button
            key={resume.id}
            type="button"
            aria-pressed={active}
            disabled={busy}
            onClick={() => onSelect(resume.id)}
            className={`flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm transition-all active:scale-95 disabled:cursor-wait disabled:opacity-60 ${
              active
                ? "border-ink-900 bg-ink-900 text-paper-50"
                : "border-paper-300 bg-white text-ink-700 hover:border-ink-400"
            }`}
          >
            <span className="font-medium">{resume.name || "Untitled resume"}</span>
            <span className={active ? "text-xs text-gold-300" : "text-xs text-ink-400"}>
              ATS {resume.ats_score.value}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
