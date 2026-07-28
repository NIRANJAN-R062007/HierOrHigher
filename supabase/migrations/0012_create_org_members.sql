-- org_members: which Supabase auth users belong to which org, and as what.
-- Recruiters are ordinary auth.users (the same sign-in flow the student side
-- uses); this table is the only thing that makes one a recruiter.
--
-- Invites are by email, so a membership row may exist BEFORE the invitee has
-- ever signed up: user_id stays null until they do, and the backend claims the
-- row (sets user_id) the first time that email signs in and hits an org route.
-- RLS is enabled here, in the same migration that creates the table.

create table public.org_members (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations (id) on delete cascade,
  user_id uuid references public.users (id) on delete cascade,
  email text not null check (email <> ''),
  role text not null default 'member' check (role in ('admin', 'member')),
  invited_by uuid references public.users (id) on delete set null,
  created_at timestamptz not null default now()
);

-- One membership per email per org (invite twice = same row), and one per
-- auth user per org once claimed.
create unique index org_members_org_email_idx
  on public.org_members (org_id, lower(email));
create unique index org_members_org_user_idx
  on public.org_members (org_id, user_id)
  where user_id is not null;
create index org_members_user_id_idx on public.org_members (user_id);

-- Membership tests used by every org-scoped RLS policy in this schema.
-- SECURITY DEFINER so the lookup itself bypasses RLS on org_members —
-- a policy on org_members that queried org_members directly would recurse.
-- Matches a claimed row by auth.uid(), or an unclaimed invite by JWT email.
create or replace function public.is_org_member(target_org uuid)
returns boolean
language sql
stable
security definer set search_path = public
as $$
  select exists (
    select 1 from public.org_members m
    where m.org_id = target_org
      and (
        m.user_id = auth.uid()
        or (
          m.user_id is null
          and lower(m.email) = lower(coalesce(auth.jwt() ->> 'email', ''))
        )
      )
  );
$$;

create or replace function public.is_org_admin(target_org uuid)
returns boolean
language sql
stable
security definer set search_path = public
as $$
  select exists (
    select 1 from public.org_members m
    where m.org_id = target_org
      and m.role = 'admin'
      and (
        m.user_id = auth.uid()
        or (
          m.user_id is null
          and lower(m.email) = lower(coalesce(auth.jwt() ->> 'email', ''))
        )
      )
  );
$$;

alter table public.org_members enable row level security;

create policy "org_members_select_same_org"
  on public.org_members for select
  using (public.is_org_member(org_id));

-- Only an admin may invite teammates or change roles.
create policy "org_members_insert_admin"
  on public.org_members for insert
  with check (public.is_org_admin(org_id));

create policy "org_members_update_admin"
  on public.org_members for update
  using (public.is_org_admin(org_id))
  with check (public.is_org_admin(org_id));

create policy "org_members_delete_admin"
  on public.org_members for delete
  using (public.is_org_admin(org_id));

-- Deferred from 0011: organizations reads/writes scoped to membership, which
-- could only be expressed once org_members (above) existed.
create policy "organizations_select_member"
  on public.organizations for select
  using (public.is_org_member(id));

create policy "organizations_update_admin"
  on public.organizations for update
  using (public.is_org_admin(id))
  with check (public.is_org_admin(id));

create policy "organizations_delete_admin"
  on public.organizations for delete
  using (public.is_org_admin(id));
