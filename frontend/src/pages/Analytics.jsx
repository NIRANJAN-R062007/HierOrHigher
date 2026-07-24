import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ErrorState from "../components/dashboard/ErrorState";
import MatchHistogram from "../components/dashboard/MatchHistogram";
import { SkeletonCard } from "../components/dashboard/Skeleton";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

function Stat({ label, value }) {
  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-800 p-5 shadow-card">
      <p className="font-display text-3xl font-semibold text-paper-50">{value}</p>
      <p className="mt-1 text-xs font-medium text-paper-200/60">{label}</p>
    </div>
  );
}

/**
 * Cross-run analytics: the distribution of match percentages across every
 * job description the user has mapped, aggregated from GET
 * /analytics/gap-distribution (persisted data only — no re-processing).
 */
export default function Analytics() {
  const { signOut } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [items, setItems] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        setItems(await api.getGapDistribution());
      } catch (err) {
        setError(err.message);
      }
      setLoading(false);
    })();
  }, []);

  const count = items.length;
  const average = count
    ? Math.round(items.reduce((sum, i) => sum + i.match_percentage, 0) / count)
    : 0;
  const best = count ? Math.max(...items.map((i) => i.match_percentage)) : 0;

  return (
    <div className="min-h-screen bg-ink-950">
      <header className="border-b border-ink-800">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
          <Link to="/" className="font-display text-lg font-semibold text-paper-50">
            Hire<span className="text-gold-400">Or</span>Higher
          </Link>
          <div className="flex items-center gap-4">
            <Link
              to="/dashboard"
              className="text-sm font-medium text-paper-200 transition-colors hover:text-paper-50"
            >
              ← Dashboard
            </Link>
            <button
              type="button"
              onClick={signOut}
              className="rounded-full border border-ink-700 px-4 py-1.5 text-sm font-medium text-paper-200 transition-colors hover:border-ink-500 active:scale-95"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-5 pb-24 pt-10 sm:px-8">
        <h1 className="font-display text-3xl font-semibold text-paper-50">
          Analytics
        </h1>
        <p className="mb-8 mt-1 text-sm text-paper-200/70">
          How your resumes stack up against every job description you've mapped.
        </p>

        {loading ? (
          <SkeletonCard />
        ) : error ? (
          <ErrorState message={error} onRetry={() => window.location.reload()} />
        ) : count === 0 ? (
          <div className="rounded-2xl border border-ink-700 bg-ink-800 p-10 text-center shadow-card">
            <p className="text-sm text-paper-200/70">
              No gap reports yet. Map a resume against a job description on the{" "}
              <Link
                to="/dashboard"
                className="font-semibold text-gold-400 hover:text-gold-300"
              >
                dashboard
              </Link>{" "}
              and your match distribution will appear here.
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-4">
              <Stat label="Reports" value={count} />
              <Stat label="Average match" value={`${average}%`} />
              <Stat label="Best match" value={`${best}%`} />
            </div>
            <div className="mt-8 rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card">
              <h2 className="mb-6 text-sm font-semibold text-paper-200">
                Match distribution
              </h2>
              <MatchHistogram items={items} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
