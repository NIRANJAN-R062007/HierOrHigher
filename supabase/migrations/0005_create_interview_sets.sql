-- interview_sets: module 5.3 output per (resume, JD) pair.
-- RLS is enabled here, scoped to the owner via the parent resume.

create table public.interview_sets (
  id uuid primary key default gen_random_uuid(),
  resume_id uuid not null references public.resumes (id) on delete cascade,
  jd_id uuid not null references public.job_descriptions (id) on delete cascade,
  content_hash text not null,
  questions jsonb not null,
  created_at timestamptz not null default now(),
  unique (resume_id, content_hash)
);

create index interview_sets_content_hash_idx
  on public.interview_sets (content_hash);
create index interview_sets_resume_id_idx on public.interview_sets (resume_id);

alter table public.interview_sets enable row level security;

create policy "interview_sets_select_own"
  on public.interview_sets for select
  using (
    exists (
      select 1 from public.resumes r
      where r.id = interview_sets.resume_id and r.user_id = auth.uid()
    )
  );

create policy "interview_sets_insert_own"
  on public.interview_sets for insert
  with check (
    exists (
      select 1 from public.resumes r
      where r.id = interview_sets.resume_id and r.user_id = auth.uid()
    )
  );

create policy "interview_sets_delete_own"
  on public.interview_sets for delete
  using (
    exists (
      select 1 from public.resumes r
      where r.id = interview_sets.resume_id and r.user_id = auth.uid()
    )
  );
