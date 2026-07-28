import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ErrorState from "../components/dashboard/ErrorState";
import { SkeletonCard } from "../components/dashboard/Skeleton";
import ApplicantCard from "../components/recruiter/ApplicantCard";
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
 * The screening view for one posting: every applicant, ranked by how well
 * they match the description, with matched and missing skills per candidate.
 *
 * Read-only and computed at submission time — opening this page spends no AI
 * credits no matter how many applicants there are.
 */
export default function PostingScreening() {
  const { postingId } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [posting, setPosting] = useState(null);
  const [applicants, setApplicants] = useState([]);

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const [postingRow, rows] = await Promise.all([
          api.getJobPosting(postingId),
          api.listApplications(postingId),
        ]);
        if (!live) return;
        setPosting(postingRow);
        setApplicants(rows);
      } catch (err) {
        if (live) setError(err.message);
      }
      if (live) setLoading(false);
    })();
    return () => {
      live = false;
    };
  }, [postingId]);

  const count = applicants.length;
  const best = count ? applicants[0].match_percentage : 0;
  const average = count
    ? Math.round(
        applicants.reduce((sum, a) => sum + a.match_percentage, 0) / count,
      )
    : 0;

  return (
    <div className="min-h-screen bg-ink-950">
      <header className="border-b border-ink-800">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-5 sm:px-8">
          <Link to="/" className="font-display text-lg font-semibold text-paper-50">
            Hire<span className="text-gold-400">Or</span>Higher
          </Link>
          <Link
            to="/hiring"
            className="text-sm font-medium text-paper-200 transition-colors hover:text-paper-50"
          >
            ← All postings
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-5 pb-24 pt-10 sm:px-8">
        {loading ? (
          <SkeletonCard />
        ) : error ? (
          <ErrorState message={error} onRetry={() => window.location.reload()} />
        ) : (
          <>
            <h1 className="font-display text-3xl font-semibold text-paper-50">
              {posting.title}
            </h1>
            <p className="mb-8 mt-1 text-sm text-paper-200/70">
              Applicants ranked against this posting's description.
            </p>

            {count === 0 ? (
              <div className="rounded-2xl border border-ink-700 bg-ink-800 p-10 text-center shadow-card">
                <p className="text-sm text-paper-200/70">
                  No applications yet.{" "}
                  {posting.status === "open"
                    ? "Share the apply link and they'll appear here, ranked."
                    : "This posting isn't open, so its apply link isn't accepting anyone."}
                </p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-4">
                  <Stat label="Applicants" value={count} />
                  <Stat label="Best match" value={`${best}%`} />
                  <Stat label="Average match" value={`${average}%`} />
                </div>
                <ul className="mt-8 space-y-4">
                  {applicants.map((applicant, index) => (
                    <ApplicantCard
                      key={applicant.application_id}
                      applicant={applicant}
                      rank={index + 1}
                    />
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
