"""Org membership: the recruiter side's entire authorization model.

There is no recruiter account type. A recruiter is a Supabase auth user who
holds an ``org_members`` row, so every recruiter-facing route funnels through
``require_membership``/``require_admin`` here before touching a posting,
candidate, or application. Uses no Gemini key.

Two failure modes, kept distinct on purpose:

* ``OrgAccessError`` → 404. A non-member gets the same answer for "this org
  does not exist" and "this org exists but isn't yours", so org and posting
  ids can't be probed for existence.
* ``OrgPermissionError`` → 403. The caller is a member; the action is
  admin-only. Existence is already known to them, so naming the reason is
  safe and far more useful.
"""

from app.models.organization import OrganizationResponse, OrgMemberResponse


class OrgAccessError(LookupError):
    """No such org/posting, or the caller isn't a member — reported as 404."""


class OrgPermissionError(PermissionError):
    """The caller is a member but the action requires an admin."""


def _membership_email(row: dict) -> str:
    return (row.get("email") or "").lower()


def create_organization(
    user_id: str, email: str | None, name: str, repo
) -> OrganizationResponse:
    """Create an org and make its creator the first admin.

    The membership row is what actually grants access, so it is written
    immediately — an org whose creator wasn't a member would be unreachable by
    anyone, including them.
    """
    org = repo.insert_organization({"name": name, "created_by": user_id})
    repo.insert_org_member(
        {
            "org_id": org["id"],
            "user_id": user_id,
            "email": (email or "").lower(),
            "role": "admin",
            "invited_by": user_id,
        }
    )
    return OrganizationResponse(
        id=str(org["id"]),
        name=org["name"],
        role="admin",
        created_at=str(org["created_at"]),
    )


def list_organizations(user_id: str, email: str | None, repo) -> list[OrganizationResponse]:
    """Every org the caller belongs to, including ones they were invited to
    before signing up (matched by their verified session email)."""
    memberships = repo.list_memberships_for_user(user_id, (email or "").lower())
    if not memberships:
        return []

    orgs = {
        str(org["id"]): org
        for org in repo.list_organizations_by_ids(
            [str(m["org_id"]) for m in memberships]
        )
    }
    response = []
    for membership in memberships:
        org = orgs.get(str(membership["org_id"]))
        if org is None:  # org deleted out from under a stale membership row
            continue
        response.append(
            OrganizationResponse(
                id=str(org["id"]),
                name=org["name"],
                role=membership["role"],
                created_at=str(org["created_at"]),
            )
        )
    return response


def require_membership(user_id: str, email: str | None, org_id: str, repo) -> dict:
    """Return the caller's membership row for ``org_id`` or raise.

    Also claims a pending invite: a row addressed to this email with no linked
    auth user gets bound to the caller here, on their first authenticated
    request, so later lookups match on ``user_id`` directly. The email is the
    one Supabase verified for the session — never a client-supplied value.
    """
    membership = repo.get_org_membership(org_id, user_id, (email or "").lower())
    if membership is None:
        raise OrgAccessError("Organization not found.")
    if membership.get("user_id") is None:
        membership = repo.claim_org_membership(str(membership["id"]), user_id)
    return membership


def require_admin(user_id: str, email: str | None, org_id: str, repo) -> dict:
    membership = require_membership(user_id, email, org_id, repo)
    if membership["role"] != "admin":
        raise OrgPermissionError(
            "Only an organization admin can do this. Ask an admin on your team."
        )
    return membership


def require_posting_access(user_id: str, email: str | None, posting_id: str, repo) -> dict:
    """Resolve a posting the caller may act on, gated by its org.

    ``repo.get_job_posting`` is unscoped (the public apply route needs it with
    no caller at all), so this is the checkpoint that turns a posting id into
    an authorized read for a signed-in recruiter.
    """
    posting = repo.get_job_posting(posting_id)
    if posting is None:
        raise OrgAccessError("Job posting not found.")
    require_membership(user_id, email, str(posting["org_id"]), repo)
    return posting


def list_members(user_id: str, email: str | None, org_id: str, repo) -> list[OrgMemberResponse]:
    """The org's roster. Any member may see who else is on the team."""
    require_membership(user_id, email, org_id, repo)
    return [
        OrgMemberResponse(
            id=str(row["id"]),
            email=_membership_email(row),
            role=row["role"],
            pending=row.get("user_id") is None,
            created_at=str(row["created_at"]),
        )
        for row in repo.list_org_members(org_id)
    ]


def invite_member(
    user_id: str, email: str | None, org_id: str, invitee_email: str, role: str, repo
) -> OrgMemberResponse:
    """Invite a teammate by email (admin-only).

    Creates no auth user and sends no mail: it writes a membership row with no
    linked user, which the invitee claims by signing up through the normal
    Supabase flow with that address. Re-inviting someone already on the roster
    returns their existing row rather than failing, so a duplicate invite is
    harmless.
    """
    require_admin(user_id, email, org_id, repo)

    invitee_email = invitee_email.strip().lower()
    existing = repo.get_org_member_by_email(org_id, invitee_email)
    if existing is not None:
        return OrgMemberResponse(
            id=str(existing["id"]),
            email=_membership_email(existing),
            role=existing["role"],
            pending=existing.get("user_id") is None,
            created_at=str(existing["created_at"]),
        )

    row = repo.insert_org_member(
        {
            "org_id": org_id,
            "user_id": None,
            "email": invitee_email,
            "role": role,
            "invited_by": user_id,
        }
    )
    return OrgMemberResponse(
        id=str(row["id"]),
        email=_membership_email(row),
        role=row["role"],
        pending=True,
        created_at=str(row["created_at"]),
    )
