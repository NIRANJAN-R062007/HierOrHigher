import { useRef, useState } from "react";
import ErrorState from "./ErrorState";
import StepLoader from "./StepLoader";

const UPLOAD_STEPS = [
  "Validating your file…",
  "Parsing your resume…",
  "Scoring against ATS rules…",
  "Generating readability feedback…",
];

const MAX_MB = 5;
const ACCEPTED = [".pdf", ".docx"];

/** Resume intake: drag & drop or browse, with inline validation. */
export default function UploadPanel({ resume, uploading, error, onUpload, onRetry }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState(null);

  function handleFile(file) {
    setLocalError(null);
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!ACCEPTED.some((extension) => name.endsWith(extension))) {
      setLocalError("Please upload a PDF or DOCX file.");
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setLocalError(`That file is over the ${MAX_MB}MB limit.`);
      return;
    }
    onUpload(file);
  }

  return (
    <section aria-labelledby="upload-heading">
      <div
        className={`rounded-2xl border-2 border-dashed bg-white p-6 shadow-card transition-colors sm:p-8 ${
          dragging ? "border-gold-500 bg-gold-500/5" : "border-paper-300"
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          handleFile(event.dataTransfer.files?.[0]);
        }}
      >
        {uploading ? (
          <div className="mx-auto max-w-sm py-2">
            <h2 id="upload-heading" className="mb-4 font-display text-lg font-semibold text-ink-900">
              Reading your resume
            </h2>
            <StepLoader steps={UPLOAD_STEPS} />
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-paper-100 text-ink-500">
              <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 16V4m0 0 4 4m-4-4-4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
              </svg>
            </span>
            <h2 id="upload-heading" className="font-display text-lg font-semibold text-ink-900">
              {resume ? "Replace your resume" : "Upload your resume"}
            </h2>
            <p className="max-w-sm text-sm text-ink-500">
              {resume
                ? "Uploading a new file re-runs everything against it. Identical files return instantly from cache."
                : `Drag and drop a PDF or DOCX (max ${MAX_MB}MB) — every module runs from this single upload.`}
            </p>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="mt-1 rounded-full bg-ink-900 px-6 py-2.5 text-sm font-semibold text-paper-50 transition-all hover:bg-ink-700 active:scale-95"
            >
              Browse files
            </button>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED.join(",")}
              className="hidden"
              aria-label="Resume file"
              onChange={(event) => {
                handleFile(event.target.files?.[0]);
                event.target.value = "";
              }}
            />
          </div>
        )}
      </div>
      {(localError || error) && (
        <div className="mt-3">
          <ErrorState message={localError || error} onRetry={localError ? null : onRetry} />
        </div>
      )}
      {resume?.cached && !uploading && (
        <p role="status" className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Loaded instantly from cache — this exact file was already scored, so
          no AI credits were spent.
        </p>
      )}
    </section>
  );
}
