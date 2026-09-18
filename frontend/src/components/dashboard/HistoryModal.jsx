import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import ErrorState from "./ErrorState";

/**
 * Past-runs panel opened from the sidebar's History entry.
 *
 * Two axes for the active resume: the resumes you've uploaded (switch back to
 * any of them) and this resume's past gap maps / mock interviews / profile
 * drafts. Selecting a module entry fetches it in full and renders it read-only
 * here — the live GapSection/InterviewSection/ProfileSection stay untouched.
 */

function formatDate(iso) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

// -- read-only detail viewers -------------------------------------------------

function GapDetail({ report }) {
  const chip = (skill, tone) => (
    <li
      key={skill}
      className={`rounded-full border px-3 py-1 text-sm font-medium ${
        tone === "matched"
          ? "border-emerald-500/30 bg-emerald-900/40 text-emerald-300"
          : "border-red-500/30 bg-red-900/40 text-red-300"
      }`}
    >
      {tone === "matched" ? "✓ " : "+ "}
      {skill}
    </li>
  );
  return (
    <div>
      <div className="flex items-end justify-between">
        <p className="text-sm font-semibold text-paper-200">Match strength</p>
        <p className="font-display text-2xl font-semibold text-paper-50">
          {report.match_percentage}
          <span className="text-sm font-medium text-paper-200/60">%</span>
        </p>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink-700">
        <div
          className="h-full rounded-full bg-gradient-to-r from-gold-600 to-gold-400"
          style={{ width: `${report.match_percentage}%` }}
        />
      </div>
      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        <div>
          <h4 className="text-sm font-semibold text-paper-200">
            You already cover{" "}
            <span className="font-normal text-paper-200/50">({report.matched.length})</span>
          </h4>
          <ul className="mt-2 flex flex-wrap gap-2">
            {report.matched.length === 0 && <li className="text-sm text-paper-200/60">None</li>}
            {report.matched.map((skill) => chip(skill, "matched"))}
          </ul>
        </div>
        <div>
          <h4 className="text-sm font-semibold text-paper-200">
            Missing for this role{" "}
            <span className="font-normal text-paper-200/50">({report.missing.length})</span>
          </h4>
          <ul className="mt-2 flex flex-wrap gap-2">
            {report.missing.length === 0 && <li className="text-sm text-paper-200/60">None</li>}
            {report.missing.map((skill) => chip(skill, "missing"))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function InterviewDetail({ set }) {
  return (
    <ol className="space-y-3">
      {set.questions.map((item, index) => (
        <li key={item.question} className="rounded-xl border border-ink-700 bg-ink-900 p-4">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-paper-200/50">Q{index + 1}</span>
            <span className="rounded-full bg-ink-700 px-2.5 py-0.5 text-xs font-semibold text-paper-200">
              {item.category}
            </span>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-paper-50">{item.question}</p>
        </li>
      ))}
    </ol>
  );
}

function ProfileDetail({ draft }) {
  const block = (title, text) => (
    <div key={title} className="rounded-xl border border-ink-700 bg-ink-900 p-4">
      <h4 className="text-sm font-semibold text-paper-200">{title}</h4>
      <p className="mt-1.5 whitespace-pre-line text-sm leading-relaxed text-paper-50">{text}</p>
    </div>
  );
  return (
    <div className="space-y-3">
      {block("LinkedIn headline", draft.headline.concise)}
      {block("About section", draft.about.concise)}
      {draft.project_descriptions.map((project) =>
        block(`Project — ${project.title}`, project.concise),
      )}
      <p className="text-xs text-paper-200/60">
        Showing the concise tone — open the Profile section for the tone toggle.
      </p>
    </div>
  );
}

// -- history list -------------------------------------------------------------

function EntryRow({ label, sublabel, onClick }) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className="flex w-full items-center justify-between gap-3 rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-left transition-colors hover:border-ink-500"
      >
        <span className="text-sm font-medium text-paper-50">{label}</span>
        <span className="text-xs text-paper-200/50">{sublabel}</span>
      </button>
    </li>
  );
}

function Group({ title, children, empty }) {
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-paper-200/50">{title}</h3>
      {empty ? (
        <p className="mt-2 text-sm text-paper-200/60">{empty}</p>
      ) : (
        <ul className="mt-2 space-y-2">{children}</ul>
      )}
    </section>
  );
}

export default function HistoryModal({
  resumeId,
  resumes,
  activeResumeId,
  onSwitchResume,
  onClose,
  initialGapReportId,
}) {
  const [lists, setLists] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    if (!resumeId) return undefined;
    let alive = true;
    setLoading(true);
    setError(null);
    Promise.all([
      api.listGapReports(resumeId),
      api.listInterviewSets(resumeId),
      api.listProfileDrafts(resumeId),
    ])
      .then(([gap, interview, profile]) => {
        if (alive) {
          setLists({ gap, interview, profile });
          setLoading(false);
        }
      })
      .catch((err) => {
        if (alive) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => {
      alive = false;
    };
  }, [resumeId]);

  const openDetail = useCallback(
    async (type, id) => {
      const fetchers = {
        gap: api.getGapReport,
        interview: api.getInterviewSet,
        profile: api.getProfileDraft,
      };
      setDetailLoading(true);
      setError(null);
      try {
        setSelected({ type, data: await fetchers[type](id, resumeId) });
      } catch (err) {
        setError(err.message);
      }
      setDetailLoading(false);
    },
    [resumeId],
  );

  // Job Radar rows jump straight into this modal's existing gap detail view
  // instead of a separate one — the history list load still runs in the
  // background beneath it.
  useEffect(() => {
    if (initialGapReportId && resumeId) {
      openDetail("gap", initialGapReportId);
    }
  }, [initialGapReportId, resumeId, openDetail]);

  const detailTitle = {
    gap: "Gap map",
    interview: "Mock interview",
    profile: "Profile draft",
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Run history"
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink-950/70 p-4 backdrop-blur-sm sm:p-8"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl border border-ink-700 bg-ink-900 shadow-lift"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-ink-700 px-6 py-4">
          <div className="flex items-center gap-3">
            {selected && (
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="rounded-full px-2 py-1 text-sm text-paper-200/70 hover:text-paper-50"
              >
                ← Back
              </button>
            )}
            <h2 className="font-display text-lg font-semibold text-paper-50">
              {selected ? detailTitle[selected.type] : "History"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close history"
            className="rounded-full px-2 py-1 text-xl leading-none text-paper-200/60 hover:text-paper-50"
          >
            ×
          </button>
        </header>

        <div className="max-h-[70vh] overflow-y-auto px-6 py-5">
          {error && <ErrorState message={error} />}

          {!selected && (loading || detailLoading) && (
            <p className="text-sm text-paper-200/60">Loading…</p>
          )}

          {selected && (
            <div>
              {selected.type === "gap" && <GapDetail report={selected.data} />}
              {selected.type === "interview" && <InterviewDetail set={selected.data} />}
              {selected.type === "profile" && <ProfileDetail draft={selected.data} />}
            </div>
          )}

          {!selected && lists && !loading && (
            <div className="space-y-6">
              <Group title="Your resumes" empty={resumes.length === 0 ? "No resumes yet." : null}>
                {resumes.map((resume) => (
                  <EntryRow
                    key={resume.id}
                    label={`${resume.name || "Untitled resume"}${
                      resume.id === activeResumeId ? "  ·  active" : ""
                    }`}
                    sublabel={formatDate(resume.created_at)}
                    onClick={() => {
                      if (resume.id !== activeResumeId) onSwitchResume(resume.id);
                      onClose();
                    }}
                  />
                ))}
              </Group>

              <Group title="Gap maps" empty={lists.gap.length === 0 ? "No gap maps run yet." : null}>
                {lists.gap.map((item) => (
                  <EntryRow
                    key={item.id}
                    label={`${item.match_percentage}% match`}
                    sublabel={formatDate(item.created_at)}
                    onClick={() => openDetail("gap", item.id)}
                  />
                ))}
              </Group>

              <Group
                title="Mock interviews"
                empty={lists.interview.length === 0 ? "No interviews generated yet." : null}
              >
                {lists.interview.map((item) => (
                  <EntryRow
                    key={item.id}
                    label="Interview set"
                    sublabel={formatDate(item.created_at)}
                    onClick={() => openDetail("interview", item.id)}
                  />
                ))}
              </Group>

              <Group
                title="Profile drafts"
                empty={lists.profile.length === 0 ? "No profile drafts yet." : null}
              >
                {lists.profile.map((item) => (
                  <EntryRow
                    key={item.id}
                    label="Profile draft"
                    sublabel={formatDate(item.created_at)}
                    onClick={() => openDetail("profile", item.id)}
                  />
                ))}
              </Group>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
