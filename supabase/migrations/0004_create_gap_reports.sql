-- gap_reports: module 5.2 output per (resume, JD) pair.
-- content_hash = sha256(resume hash + JD hash) for the cross-module cache.
-- RLS is enabled here, scoped to the owner via the parent resume.

create table public.gap_reports (
  id uuid primary key default gen_random_uuid(),
  resume_id uuid not null references public.resumes (id) on delete cascade,
  jd_id uuid not null references public.job_descriptions (id) on delete cascade,
  content_hash text not null,
  matched jsonb not null,
  missing jsonb not null,
  match_percentage integer not null,
  created_at timestamptz not null default now(),
  unique (resume_id, content_hash)
);

create index gap_reports_content_hash_idx on public.gap_reports (content_hash);
create index gap_reports_resume_id_idx on public.gap_reports (resume_id);

alter table public.gap_reports enable row level security;

create policy "gap_reports_select_own"
  on public.gap_reports for select
  using (
    exists (
      select 1 from public.resumes r
      where r.id = gap_reports.resume_id and r.user_id = auth.uid()
    )
  );

create policy "gap_reports_insert_own"
  on public.gap_reports for insert
  with check (
    exists (
      select 1 from public.resumes r
      where r.id = gap_reports.resume_id and r.user_id = auth.uid()
    )
  );

create policy "gap_reports_delete_own"
  on public.gap_reports for delete
  using (
    exists (
      select 1 from public.resumes r
      where r.id = gap_reports.resume_id and r.user_id = auth.uid()
    )
  );
