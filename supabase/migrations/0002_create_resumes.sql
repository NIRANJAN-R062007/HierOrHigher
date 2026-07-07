-- resumes: one row per parsed upload; content_hash powers the Gemini cache.
-- RLS is enabled here, in the same migration that creates the table.

create table public.resumes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  file_url text,
  content_hash text not null,
  parsed_json jsonb not null,
  ats_score jsonb not null,
  human_score jsonb not null,
  created_at timestamptz not null default now(),
  unique (user_id, content_hash)
);

-- Fast cache lookup on identical re-uploads (spec 3.3).
create index resumes_content_hash_idx on public.resumes (content_hash);
create index resumes_user_id_idx on public.resumes (user_id);

alter table public.resumes enable row level security;

create policy "resumes_select_own"
  on public.resumes for select
  using (auth.uid() = user_id);

create policy "resumes_insert_own"
  on public.resumes for insert
  with check (auth.uid() = user_id);

create policy "resumes_delete_own"
  on public.resumes for delete
  using (auth.uid() = user_id);
