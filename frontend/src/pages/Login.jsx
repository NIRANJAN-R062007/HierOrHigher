import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthShell from "../components/AuthShell";
import GoogleAuthButton from "../components/GoogleAuthButton";
import { useAuth } from "../context/AuthContext";

const INPUT_CLASSES =
  "mt-1.5 w-full rounded-lg border border-ink-600 bg-ink-900/80 px-4 py-2.5 " +
  "text-paper-50 placeholder-ink-400 transition-colors focus:border-gold-500";

export default function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const { error: authError } = await signIn(email, password);
    setSubmitting(false);
    if (authError) {
      setError(authError.message);
      return;
    }
    navigate("/dashboard");
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to see your scores and pick up where you left off."
      footer={
        <>
          New here?{" "}
          <Link to="/signup" className="font-medium text-gold-400 hover:text-gold-300">
            Create an account
          </Link>
        </>
      }
    >
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
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={INPUT_CLASSES}
            placeholder="••••••••"
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
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <GoogleAuthButton label="Sign in with Google" />
    </AuthShell>
  );
}
