import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import ErrorState from "../components/dashboard/ErrorState";
import { SkeletonCard } from "../components/dashboard/Skeleton";
import StepLoader from "../components/dashboard/StepLoader";
import { api } from "../lib/api";

const SUBMIT_STEPS = [
  "Checking your file…",
  "Reading your resume…",
  "Sending it to the hiring team…",
];

const MAX_MB = 5;
const ACCEPTED = [".pdf", ".docx"];

const FIELD_CLASSES =
  "mt-1.5 w-full rounded-xl border border-ink-700 bg-ink-900 px-4 py-2.5 " +
  "text-sm text-paper-50 placeholder-paper-200/40 transition-colors focus:border-gold-500";

/**
 * The public apply page — the one page in the app that needs no account.
 *
 * A candidate opens the link, attaches a resume, optionally says who they
 * are, and submits. Nothing is created for them: no login, no dashboard, no
 * profile they'd have to come back to. The screening result goes to the
 * hiring team only, which is why this page never shows a score.
 */
export default function Apply() {
  const { postingId } = useParams();
  const inputRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [posting, setPosting] = useState(null);

  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [receipt, setReceipt] = useState(null);

  useEffect(() => {
    let live = true;
    api
      .getPublicPosting(postingId)
      .then((row) => live && setPosting(row))
      .catch((err) => live && setLoadError(err.message))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [postingId]);

  function chooseFile(candidate) {
    setSubmitError(null);
    if (!candidate) return;
    if (!ACCEPTED.some((ext) => candidate.name.toLowerCase().endsWith(ext))) {
      setSubmitError("Please attach a PDF or DOCX résumé.");
      return;
    }
    if (candidate.size > MAX_MB * 1024 * 1024) {
      setSubmitError(`That file is over the ${MAX_MB}MB limit.`);
      return;
    }
    setFile(candidate);
  }

  async function submit(event) {
    event.preventDefault();
    if (!file || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      setReceipt(await api.submitApplication(postingId, file, { name, email }));
    } catch (err) {
      setSubmitError(err.message);
    }
    setSubmitting(false);
  }

  return (
    <div className="min-h-screen bg-ink-950">
      <header className="border-b border-ink-800">
        <div className="mx-auto flex h-16 max-w-2xl items-center px-5 sm:px-8">
          <span className="font-display text-lg font-semibold text-paper-50">
            Hire<span className="text-gold-400">Or</span>Higher
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-5 pb-24 pt-10 sm:px-8">
        {loading ? (
          <SkeletonCard />
        ) : loadError ? (
          <div className="rounded-2xl border border-ink-700 bg-ink-800 p-10 text-center shadow-card">
            <h1 className="font-display text-2xl font-semibold text-paper-50">
              This link isn't active
            </h1>
            <p className="mt-2 text-sm text-paper-200/70">{loadError}</p>
          </div>
        ) : receipt ? (
          <div className="rounded-2xl border border-ink-700 bg-ink-800 p-10 text-center shadow-card">
            <span
              aria-hidden
              className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-900/40 text-2xl text-emerald-300"
            >
              ✓
            </span>
            <h1 className="mt-4 font-display text-2xl font-semibold text-paper-50">
              {receipt.already_applied
                ? "You've already applied"
                : "Application received"}
            </h1>
            <p className="mt-2 text-sm text-paper-200/70">
              {receipt.candidate_name ? `Thanks, ${receipt.candidate_name}. ` : ""}
              {receipt.already_applied
                ? `We already have this résumé on file for ${receipt.posting_title}.`
                : `${posting.organization_name} has your résumé for ${receipt.posting_title}.`}
            </p>
            <p className="mt-4 text-xs text-paper-200/50">
              There's no account to create and nothing to sign in to — the
              hiring team will reach out directly.
            </p>
          </div>
        ) : (
          <>
            <p className="text-sm font-medium text-gold-400">
              {posting.organization_name}
            </p>
            <h1 className="mt-1 font-display text-3xl font-semibold text-paper-50">
              {posting.title}
            </h1>

            <div className="mt-6 rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card">
              <h2 className="text-sm font-semibold text-paper-200">
                About this role
              </h2>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-paper-200/80">
                {posting.description}
              </p>
            </div>

            <form
              onSubmit={submit}
              className="mt-6 rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card"
            >
              <h2 className="font-display text-lg font-semibold text-paper-50">
                Apply
              </h2>
              <p className="mt-1 text-sm text-paper-200/70">
                Attach your résumé. No account needed.
              </p>

              {submitting ? (
                <div className="mt-6 max-w-sm">
                  <StepLoader steps={SUBMIT_STEPS} />
                </div>
              ) : (
                <>
                  <div className="mt-5 flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => inputRef.current?.click()}
                      className="rounded-full border border-ink-600 px-5 py-2.5 text-sm font-medium text-paper-200 transition-colors hover:border-gold-500 hover:text-gold-300"
                    >
                      {file ? "Choose a different file" : "Attach résumé"}
                    </button>
                    <span className="text-sm text-paper-200/60">
                      {file ? file.name : `PDF or DOCX, up to ${MAX_MB}MB`}
                    </span>
                    <input
                      ref={inputRef}
                      type="file"
                      accept={ACCEPTED.join(",")}
                      className="hidden"
                      aria-label="Résumé file"
                      onChange={(event) => {
                        chooseFile(event.target.files?.[0]);
                        event.target.value = "";
                      }}
                    />
                  </div>

                  <div className="mt-5 grid gap-4 sm:grid-cols-2">
                    <label className="block text-sm font-semibold text-paper-200">
                      Name <span className="font-normal text-paper-200/50">(optional)</span>
                      <input
                        type="text"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="Your name"
                        className={FIELD_CLASSES}
                      />
                    </label>
                    <label className="block text-sm font-semibold text-paper-200">
                      Email <span className="font-normal text-paper-200/50">(optional)</span>
                      <input
                        type="email"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        placeholder="you@example.com"
                        className={FIELD_CLASSES}
                      />
                    </label>
                  </div>
                  <p className="mt-2 text-xs text-paper-200/50">
                    Left blank, we'll use whatever your résumé lists.
                  </p>

                  <button
                    type="submit"
                    disabled={!file}
                    className="mt-5 rounded-full bg-gold-500 px-6 py-2.5 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Submit application
                  </button>
                </>
              )}

              {submitError && !submitting && (
                <div className="mt-4">
                  <ErrorState message={submitError} />
                </div>
              )}
            </form>
          </>
        )}
      </main>
    </div>
  );
}
