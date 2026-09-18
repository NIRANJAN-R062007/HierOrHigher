import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import ErrorState from "./ErrorState";
import Skeleton from "./Skeleton";
import StepLoader from "./StepLoader";

const RADAR_STEPS = [
  "Searching live postings…",
  "Running each through the Gap Mapper…",
  "Ranking by match strength…",
];

function matchTone(pct) {
  if (pct >= 70) return "text-emerald-300";
  if (pct >= 40) return "text-gold-400";
  return "text-paper-200/70";
}

function ResultsTable({ results, onSelect }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-ink-700 text-left text-xs font-semibold uppercase tracking-wider text-paper-200/50">
            <th className="py-2 pr-4">Job title</th>
            <th className="py-2 pr-4">Company</th>
            <th className="py-2 pr-4 text-right">Match</th>
          </tr>
        </thead>
        <tbody>
          {results.map((item) => (
            <tr
              key={item.gap_report_id}
              onClick={() => onSelect(item.gap_report_id)}
              className="cursor-pointer border-b border-ink-800 transition-colors hover:bg-ink-700/50"
            >
              <td className="py-3 pr-4 font-medium text-paper-50">{item.job_title}</td>
              <td className="py-3 pr-4 text-paper-200/70">{item.company}</td>
              <td className={`py-3 pr-4 text-right font-display font-semibold ${matchTone(item.match_percentage)}`}>
                {Math.round(item.match_percentage)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SearchHistory({ resumeId, onSelectSearch }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searches, setSearches] = useState(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .listJobRadarSearches(resumeId)
      .then((rows) => alive && setSearches(rows))
      .catch((err) => alive && setError(err.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [resumeId]);

  if (loading) return <Skeleton className="h-9 w-48" />;
  if (error) return null;
  if (!searches || searches.length === 0) return null;

  return (
    <div className="mb-6">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-2 text-sm font-medium text-paper-200/70 hover:text-paper-50"
      >
        <span aria-hidden>{open ? "▾" : "▸"}</span>
        Past searches ({searches.length})
      </button>
      {open && (
        <ul className="mt-3 space-y-2">
          {searches.map((search) => (
            <li key={search.id}>
              <button
                type="button"
                onClick={() => onSelectSearch(search.id)}
                className="flex w-full items-center justify-between gap-3 rounded-xl border border-ink-700 bg-ink-900 px-4 py-2.5 text-left transition-colors hover:border-ink-500"
              >
                <span className="text-sm font-medium text-paper-50">
                  {search.role} — {search.location}
                </span>
                <span className="text-xs text-paper-200/50">
                  {search.result_count} result{search.result_count === 1 ? "" : "s"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Job Radar: auto-discovers live postings for a role+location and runs each
 * through the existing Gap-to-Job Mapper — a ranked shortlist instead of one
 * manually pasted JD. Each row opens the existing Gap Mapper detail view. */
export default function JobRadarSection({ resume, onOpenGapReport }) {
  const [role, setRole] = useState("");
  const [location, setLocation] = useState("");
  const [search, setSearch] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [historyKey, setHistoryKey] = useState(0);

  const ready = Boolean(resume);
  const canRun = ready && role.trim().length >= 2 && location.trim().length >= 2 && !running;

  const runSearch = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await api.createJobRadarSearch(resume.resume_id, role.trim(), location.trim());
      setSearch(result);
      setHistoryKey((key) => key + 1);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setRunning(false);
    }
  };

  const openPastSearch = async (searchId) => {
    setRunning(true);
    setError(null);
    try {
      setSearch(await api.getJobRadarSearch(searchId, resume.resume_id));
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card">
      {!ready && (
        <p className="text-sm text-paper-200/60">
          Upload a resume first — Job Radar scores live postings against your
          parsed resume, same as the gap mapper.
        </p>
      )}
      {ready && (
        <>
          <SearchHistory key={historyKey} resumeId={resume.resume_id} onSelectSearch={openPastSearch} />

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="radar-role" className="block text-sm font-semibold text-paper-200">
                Role
              </label>
              <input
                id="radar-role"
                type="text"
                value={role}
                onChange={(event) => setRole(event.target.value)}
                placeholder="e.g. backend engineer"
                className="mt-2 w-full rounded-xl border border-ink-700 bg-ink-900 px-4 py-2.5 text-sm text-paper-50 placeholder-paper-200/40 transition-colors focus:border-gold-500"
              />
            </div>
            <div>
              <label htmlFor="radar-location" className="block text-sm font-semibold text-paper-200">
                Location
              </label>
              <input
                id="radar-location"
                type="text"
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                placeholder="e.g. Chennai, Tamil Nadu, India"
                className="mt-2 w-full rounded-xl border border-ink-700 bg-ink-900 px-4 py-2.5 text-sm text-paper-50 placeholder-paper-200/40 transition-colors focus:border-gold-500"
              />
            </div>
          </div>

          <div className="mt-3">
            <button
              type="button"
              disabled={!canRun}
              onClick={runSearch}
              className="rounded-full bg-gold-500 px-6 py-2.5 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Scan live postings
            </button>
          </div>

          {running && (
            <div className="mt-5 max-w-sm">
              <StepLoader steps={RADAR_STEPS} />
            </div>
          )}
          {error && !running && (
            <div className="mt-4">
              <ErrorState message={error} onRetry={canRun ? runSearch : null} />
            </div>
          )}

          {search && !running && (
            <div className="mt-6 border-t border-ink-700 pt-6">
              {search.skipped_count > 0 && (
                <p role="status" className="mb-4 text-xs text-paper-200/60">
                  {search.skipped_count} listing{search.skipped_count === 1 ? "" : "s"} couldn't be scored.
                </p>
              )}
              {search.results.length === 0 ? (
                <p className="text-sm text-paper-200/60">
                  No live postings found for this search — try a broader role or location.
                </p>
              ) : (
                <ResultsTable results={search.results} onSelect={onOpenGapReport} />
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
