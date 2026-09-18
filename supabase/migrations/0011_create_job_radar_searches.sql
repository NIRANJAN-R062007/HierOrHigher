-- job_radar_searches: one row per Job Radar run (role+location search over
-- live SerpApi postings, each scored through the existing Gap-to-Job Mapper).
-- gap_report_ids tracks the resulting gap_reports FKs; results additionally
-- carries the SerpApi listing metadata (title/company/job_url) that has no
-- home in gap_reports/job_descriptions, so a past search can be replayed
-- (joined against gap_reports for current match percentages) with no new
-- SerpApi or Gemini calls.
-- RLS is enabled here, in the same migration that creates the table.

create table public.job_radar_searches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  resume_id uuid not null references public.resumes (id) on delete cascade,
  role text not null,
  location text not null,
  gap_report_ids uuid[] not null default '{}',
  results jsonb not null default '[]',
  searched_at timestamptz not null default now()
);

create index job_radar_searches_resume_id_idx on public.job_radar_searches (resume_id);
create index job_radar_searches_user_id_idx on public.job_radar_searches (user_id);

alter table public.job_radar_searches enable row level security;

create policy "job_radar_searches_select_own"
  on public.job_radar_searches for select
  using (auth.uid() = user_id);

create policy "job_radar_searches_insert_own"
  on public.job_radar_searches for insert
  with check (auth.uid() = user_id);

create policy "job_radar_searches_delete_own"
  on public.job_radar_searches for delete
  using (auth.uid() = user_id);
