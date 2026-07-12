import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

/** Transparent on load; solidifies with blur + border once the user scrolls. */
export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled
          ? "border-b border-ink-700/60 bg-ink-900/85 backdrop-blur-md"
          : "bg-transparent"
      }`}
    >
      <nav
        aria-label="Main"
        className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8"
      >
        <Link
          to="/"
          className="font-display text-lg font-semibold tracking-tight text-paper-50"
        >
          Hire<span className="text-gold-500">Or</span>Higher
        </Link>
        <div className="flex items-center gap-3 sm:gap-6">
          <a
            href="/#how-it-works"
            className="hidden text-sm text-paper-200/80 transition-colors hover:text-paper-50 sm:block"
          >
            How it works
          </a>
          <a
            href="/#modules"
            className="hidden text-sm text-paper-200/80 transition-colors hover:text-paper-50 sm:block"
          >
            What you get
          </a>
          <a
            href="/#outcomes"
            className="hidden text-sm text-paper-200/80 transition-colors hover:text-paper-50 sm:block"
          >
            Outcomes
          </a>
          {user ? (
            <Link
              to="/dashboard"
              className="rounded-full bg-gold-500 px-5 py-2 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-95"
            >
              Dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className="text-sm text-paper-200/80 transition-colors hover:text-paper-50"
              >
                Sign in
              </Link>
              <Link
                to="/signup"
                className="rounded-full bg-gold-500 px-5 py-2 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-95"
              >
                Get started
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
