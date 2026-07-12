import { Link } from "react-router-dom";
import Reveal from "./Reveal";

export default function Footer() {
  return (
    <footer className="border-t border-ink-800">
      <Reveal>
        <div className="mx-auto max-w-6xl px-5 py-20 text-center sm:px-8">
          <h2 className="mx-auto max-w-2xl font-display text-display-lg font-medium text-paper-50">
            The job you want already has a shortlist.
            <span className="text-gold-400"> Get on it.</span>
          </h2>
          <Link
            to="/signup"
            className="mt-8 inline-block rounded-full bg-gold-500 px-8 py-3.5 text-base font-semibold text-ink-950 shadow-gold-glow transition-all hover:-translate-y-0.5 hover:bg-gold-400 active:translate-y-0 active:scale-95"
          >
            Upload your resume
          </Link>
        </div>
      </Reveal>
      <div className="border-t border-ink-800/70">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-5 py-6 text-xs text-paper-200/45 sm:flex-row sm:px-8">
          <p className="font-display text-sm text-paper-200/70">
            Hire<span className="text-gold-500">Or</span>Higher
          </p>
          <p>Built as an internship design project. Powered by Gemini + Supabase.</p>
        </div>
      </div>
    </footer>
  );
}
