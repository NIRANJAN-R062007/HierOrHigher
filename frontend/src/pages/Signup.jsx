import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthShell from "../components/AuthShell";
import GoogleAuthButton from "../components/GoogleAuthButton";
import { useAuth } from "../context/AuthContext";

const INPUT_CLASSES =
  "mt-1.5 w-full rounded-lg border border-ink-600 bg-ink-900/80 px-4 py-2.5 " +
  "text-paper-50 placeholder-ink-400 transition-colors focus:border-gold-500";

export default function Signup() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmationSent, setConfirmationSent] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const { data, error: authError } = await signUp(email, password);
    setSubmitting(false);
    if (authError) {
      setError(authError.message);
      return;
    }
    // With email confirmation enabled Supabase returns no session yet.
    if (data.session) {
      navigate("/dashboard");
    } else {
      setConfirmationSent(true);
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="One resume upload unlocks all four modules — free."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-gold-400 hover:text-gold-300">
            Sign in
          </Link>
        </>
      }
    >
      {confirmationSent ? (
        <p role="status" className="mt-6 rounded-lg bg-gold-500/10 px-4 py-3 text-sm text-gold-200">
          Almost there — we sent a confirmation link to <strong>{email}</strong>.
          Confirm your email, then sign in.
        </p>
      ) : (
        <>
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <label className="block text-sm font-medium text-paper-200/85">
            Email
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={INPUT_CLASSES}
              placeholder="you@example.com"
            />
          </label>
          <label className="block text-sm font-medium text-paper-200/85">
            Password
            <input
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={INPUT_CLASSES}
              placeholder="At least 8 characters"
            />
          </label>
          {error && (
            <p role="alert" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-full bg-gold-500 py-3 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Creating account…" : "Create account"}
          </button>
          </form>
          <GoogleAuthButton label="Sign up with Google" />
        </>
      )}
    </AuthShell>
  );
}
