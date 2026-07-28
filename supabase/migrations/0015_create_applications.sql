-- applications: one candidate against one job posting, carrying that pair's
-- screening score.
--
-- The score is stored inline rather than as an FK into ``gap_reports``:
-- gap_reports.resume_id points at the student-facing resumes table, which
-- candidates deliberately have no row in. The columns mirror that table's
-- shape (matched/missing/match_percentage/categories) because both are
-- produced by the same matching core in app/services/gap_service.py.
--
-- content_hash = sha256(candidate resume hash + posting JD hash), the same
-- cross-input cache key gap_reports uses: re-submitting an identical resume to
-- an unchanged posting re-scores nothing.
--
-- RLS: enabled with NO policies (default-deny), for the same reason as
-- candidates — there is no auth.uid() owner; recruiters read these only
-- through the backend's org-membership-gated routes.

create table public.applications (
  id uuid primary key default gen_random_uuid(),
  posting_id uuid not null references public.job_postings (id) on delete cascade,
  candidate_id uuid not null references public.candidates (id) on delete cascade,
  content_hash text not null,
  match_percentage integer not null default 0,
  matched jsonb not null default '[]'::jsonb,
  missing jsonb not null default '[]'::jsonb,
  categories jsonb,
  created_at timestamptz not null default now(),
  unique (posting_id, candidate_id)
);

-- The screening view reads one posting's applicants ranked by match.
create index applications_posting_rank_idx
  on public.applications (posting_id, match_percentage desc);
create index applications_candidate_id_idx on public.applications (candidate_id);

alter table public.applications enable row level security;
