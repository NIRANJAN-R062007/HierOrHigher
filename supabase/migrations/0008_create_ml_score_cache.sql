-- ml_score_cache: offline ML match-score results keyed by content hash.
-- content_hash = sha256(resume_text + job_description); identical inputs
-- never re-run the model (mirrors the check-cache-before-Gemini strategy).
-- Not user-scoped: scores are pure functions of the two texts, so any
-- user hitting the same pair can share the row. Only the backend's
-- service role touches this table; RLS with no policies blocks anon access.

create table public.ml_score_cache (
  content_hash text primary key,
  response jsonb not null,
  created_at timestamptz not null default now()
);

alter table public.ml_score_cache enable row level security;
