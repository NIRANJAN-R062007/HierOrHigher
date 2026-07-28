import { useState } from "react";
import ErrorState from "../dashboard/ErrorState";

const FIELD_CLASSES =
  "mt-1.5 w-full rounded-xl border border-ink-700 bg-ink-900 px-4 py-2.5 " +
  "text-sm text-paper-50 placeholder-paper-200/40 transition-colors focus:border-gold-500";

const MIN_DESCRIPTION = 40;

/**
 * Create or edit one job posting.
 *
 * The description field is the job description itself — the same text the
 * gap mapper reads — so there is no separate "requirements" step: whatever is
 * pasted here is what candidates get scored against.
 */
export default function PostingForm({ posting, submitting, error, onSubmit, onCancel }) {
  const [title, setTitle] = useState(posting?.title ?? "");
  const [description, setDescription] = useState(posting?.description ?? "");
  const [status, setStatus] = useState(posting?.status ?? "open");

  const short = description.trim().length < MIN_DESCRIPTION;
  const canSubmit = title.trim().length >= 2 && !short && !submitting;

  function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;
    onSubmit({ title: title.trim(), description: description.trim(), status });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card"
    >
      <h2 className="font-display text-lg font-semibold text-paper-50">
        {posting ? "Edit posting" : "New job posting"}
      </h2>

      <label className="mt-4 block text-sm font-semibold text-paper-200">
        Role title
        <input
          type="text"
          required
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Backend Engineer"
          className={FIELD_CLASSES}
        />
      </label>

      <label className="mt-4 block text-sm font-semibold text-paper-200">
        Job description
        <textarea
          rows={9}
          required
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Paste the full posting — responsibilities, requirements, nice-to-haves. Applicants are scored against exactly this text."
          className={FIELD_CLASSES}
        />
      </label>

      <fieldset className="mt-4">
        <legend className="text-sm font-semibold text-paper-200">Status</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {[
            ["draft", "Draft — link is dead"],
            ["open", "Open — accepting applicants"],
            ["closed", "Closed — link is dead"],
          ].map(([value, label]) => (
            <label
              key={value}
              className={`cursor-pointer rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
                status === value
                  ? "border-gold-500 bg-gold-500/10 text-gold-300"
                  : "border-ink-700 text-paper-200/70 hover:border-ink-500"
              }`}
            >
              <input
                type="radio"
                name="status"
                value={value}
                checked={status === value}
                onChange={() => setStatus(value)}
                className="sr-only"
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      {description.trim().length > 0 && short && (
        <p className="mt-3 text-xs text-paper-200/60">
          Paste at least a few sentences — {MIN_DESCRIPTION - description.trim().length}{" "}
          more characters.
        </p>
      )}
      {error && (
        <div className="mt-4">
          <ErrorState message={error} />
        </div>
      )}

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-full bg-gold-500 px-6 py-2.5 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? "Saving…" : posting ? "Save changes" : "Create posting"}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full border border-ink-700 px-5 py-2.5 text-sm font-medium text-paper-200 transition-colors hover:border-ink-500"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
