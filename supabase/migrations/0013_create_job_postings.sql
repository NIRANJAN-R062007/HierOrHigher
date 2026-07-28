-- job_postings: one open role at an org. ``description`` is JD text — the same
-- shape of input the student-side Gap-to-Job Mapper consumes, so a posting can
-- be scored against a candidate resume with no extra input.
--
-- parsed_requirements/requirements_hash are this table's content-hash cache
-- (spec 3.3): the gap-mapper Gemini key is only spent re-extracting when the
-- description text actually changed.
--
-- The public /apply/{posting_id} page reads a posting WITHOUT authentication,
-- but it does so through the backend's service-role client, so the policies
-- here stay member-only — anon clients get nothing directly.
-- RLS is enabled here, in the same migration that creates the table.

create table public.job_postings (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations (id) on delete cascade,
  title text not null,
  description text not null,
  status text not null default 'draft'
    check (status in ('draft', 'open', 'closed')),
  parsed_requirements jsonb,
  requirements_hash text,
  created_by uuid references public.users (id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index job_postings_org_id_idx on public.job_postings (org_id);
create index job_postings_status_idx on public.job_postings (org_id, status);

alter table public.job_postings enable row level security;

create policy "job_postings_select_member"
  on public.job_postings for select
  using (public.is_org_member(org_id));

create policy "job_postings_insert_member"
  on public.job_postings for insert
  with check (public.is_org_member(org_id));

create policy "job_postings_update_member"
  on public.job_postings for update
  using (public.is_org_member(org_id))
  with check (public.is_org_member(org_id));

create policy "job_postings_delete_admin"
  on public.job_postings for delete
  using (public.is_org_admin(org_id));
