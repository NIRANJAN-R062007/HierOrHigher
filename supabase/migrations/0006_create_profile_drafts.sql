-- profile_drafts: module 5.4 output per resume (LinkedIn/portfolio copy).
-- content_hash = the resume's content hash (this module has no JD input).
-- RLS is enabled here, scoped to the owner via the parent resume.

create table public.profile_drafts (
  id uuid primary key default gen_random_uuid(),
  resume_id uuid not null references public.resumes (id) on delete cascade,
  content_hash text not null,
  headline jsonb not null,
  about jsonb not null,
  project_descriptions jsonb not null,
  created_at timestamptz not null default now(),
  unique (resume_id, content_hash)
);

create index profile_drafts_content_hash_idx
  on public.profile_drafts (content_hash);
create index profile_drafts_resume_id_idx on public.profile_drafts (resume_id);

alter table public.profile_drafts enable row level security;

create policy "profile_drafts_select_own"
  on public.profile_drafts for select
  using (
    exists (
      select 1 from public.resumes r
      where r.id = profile_drafts.resume_id and r.user_id = auth.uid()
    )
  );

create policy "profile_drafts_insert_own"
  on public.profile_drafts for insert
  with check (
    exists (
      select 1 from public.resumes r
      where r.id = profile_drafts.resume_id and r.user_id = auth.uid()
    )
  );

create policy "profile_drafts_delete_own"
  on public.profile_drafts for delete
  using (
    exists (
      select 1 from public.resumes r
      where r.id = profile_drafts.resume_id and r.user_id = auth.uid()
    )
  );
