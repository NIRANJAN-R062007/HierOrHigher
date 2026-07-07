import { Link } from "react-router-dom";

/** Shared dark, centered card layout for the sign-in / sign-up pages. */
export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center bg-ink-950 px-5 py-16">
      <div
        aria-hidden="true"
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(50% 60% at 50% 0%, rgba(201,169,97,0.10), transparent 65%)",
        }}
      />
      <div className="relative w-full max-w-md animate-fade-up">
        <Link
          to="/"
          className="block text-center font-display text-2xl font-semibold text-paper-50"
        >
          Hire<span className="text-gold-500">Or</span>Higher
        </Link>
        <div className="mt-8 rounded-2xl border border-ink-700/70 bg-ink-800/60 p-8 shadow-lift backdrop-blur">
          <h1 className="font-display text-2xl font-medium text-paper-50">
            {title}
          </h1>
          <p className="mt-2 text-sm text-paper-200/70">{subtitle}</p>
          {children}
        </div>
        <p className="mt-6 text-center text-sm text-paper-200/60">{footer}</p>
      </div>
    </div>
  );
}
