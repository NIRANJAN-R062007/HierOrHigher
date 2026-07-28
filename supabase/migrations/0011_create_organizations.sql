-- organizations: the recruiter-side tenant. Every job posting, candidate, and
-- application belongs to exactly one org; nothing is ever visible across orgs.
-- RLS is enabled here, in the same migration that creates the table.
--
-- Note on policy ordering: the member-scoped select/update policies for this
-- table need the org_members table to exist, so they are created in 0012
-- alongside it. Until then RLS is on with only the insert policy below, which
-- default-denies every other direct anon/authenticated read (fail closed).

create table public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_by uuid not null references public.users (id) on delete cascade,
  created_at timestamptz not null default now()
);

create index organizations_created_by_idx on public.organizations (created_by);

alter table public.organizations enable row level security;

-- A recruiter may only create an org under their own identity; the backend
-- then writes the creator's admin membership row (see 0012).
create policy "organizations_insert_own"
  on public.organizations for insert
  with check (auth.uid() = created_by);
