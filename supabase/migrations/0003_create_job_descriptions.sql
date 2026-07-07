-- job_descriptions: pasted JD text + extracted requirements.
-- RLS is enabled here, in the same migration that creates the table.

create table public.job_descriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  raw_text text not null,
  content_hash text not null,
  parsed_requirements jsonb,
  created_at timestamptz not null default now(),
  unique (user_id, content_hash)
);

create index job_descriptions_content_hash_idx
  on public.job_descriptions (content_hash);
create index job_descriptions_user_id_idx on public.job_descriptions (user_id);

alter table public.job_descriptions enable row level security;

create policy "job_descriptions_select_own"
  on public.job_descriptions for select
  using (auth.uid() = user_id);

create policy "job_descriptions_insert_own"
  on public.job_descriptions for insert
  with check (auth.uid() = user_id);

create policy "job_descriptions_delete_own"
  on public.job_descriptions for delete
  using (auth.uid() = user_id);
