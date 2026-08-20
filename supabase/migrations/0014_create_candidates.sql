-- candidates: one row per resume submitted through a public apply link.
--
-- Deliberately NOT the student-facing ``resumes`` table and never linked to
-- it: a candidate is a separate identity with no auth.uid() at all. Candidates
-- never sign up, never log in, and exist only inside the org they applied to.
--
-- content_hash (sha256 of the uploaded bytes) is both the dedupe key and the
-- resume-parser cache key: the same resume re-submitted to a second posting at
-- the same org reuses this row instead of re-spending Gemini.
--
-- RLS: enabled with NO policies, i.e. default-deny for every anon and
-- authenticated client. There is no auth.uid() that could own these rows, so
-- every legitimate read/write goes through the backend's org-scoped,
-- service-role-mediated routes — the same trust model the rest of the app
-- already assumes, just with no client-side escape hatch whatsoever.

create table public.candidates (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations (id) on delete cascade,
  full_name text,
  email text,
  content_hash text not null,
  parsed_json jsonb not null,
  created_at timestamptz not null default now(),
  unique (org_id, content_hash)
);

create index candidates_org_id_idx on public.candidates (org_id);

alter table public.candidates enable row level security;
