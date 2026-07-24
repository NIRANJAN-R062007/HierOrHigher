import { useState } from "react";
import { useAuth } from "../context/AuthContext";

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.47.9 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"
      />
    </svg>
  );
}

/**
 * "Continue with Google" — an OAuth alternative to the email/password form,
 * shared by the sign-in and sign-up pages. On success the browser redirects
 * to Google, so there's nothing to do after the call resolves without error.
 */
export default function GoogleAuthButton({ label = "Continue with Google" }) {
  const { signInWithGoogle } = useAuth();
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleClick() {
    setError(null);
    setSubmitting(true);
    const { error: authError } = await signInWithGoogle();
    if (authError) {
      setError(authError.message);
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="my-5 flex items-center gap-3">
        <span className="h-px flex-1 bg-ink-700" />
        <span className="text-xs font-medium uppercase tracking-wide text-paper-200/40">
          or
        </span>
        <span className="h-px flex-1 bg-ink-700" />
      </div>
      <button
        type="button"
        onClick={handleClick}
        disabled={submitting}
        className="flex w-full items-center justify-center gap-3 rounded-full border border-ink-600 bg-ink-900/60 py-3 text-sm font-semibold text-paper-50 transition-colors hover:border-ink-500 hover:bg-ink-900 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
      >
        <GoogleIcon />
        {submitting ? "Redirecting…" : label}
      </button>
      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}
    </div>
  );
}
