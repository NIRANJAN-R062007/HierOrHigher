"""Recruiter-side contracts: organizations and their members.

An org is the recruiter tenant. Its members are ordinary Supabase auth users
(the same sign-in flow the student side uses) — membership in this table is
the only thing that makes an account a recruiter. Invites are by email and may
land before the invitee has ever signed up, which is why a member row can be
``pending`` with no linked auth user yet.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

OrgRole = Literal["admin", "member"]


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)

    @field_validator("name")
    @classmethod
    def _trimmed(cls, value: str) -> str:
        name = " ".join(value.split())
        if len(name) < 2:
            raise ValueError("Organization name must be at least 2 characters.")
        return name


class OrganizationResponse(BaseModel):
    """One org the caller belongs to, with the caller's own role on it."""

    id: str
    name: str
    role: OrgRole
    created_at: str


class OrgMemberInvite(BaseModel):
    """Invite a teammate by email. Admin-only; creates no auth user — the
    invitee signs up through the normal flow and the membership row is
    claimed on their first authenticated request.

    Email is validated with a deliberately minimal shape check (and stored
    lowercased) rather than a full RFC validator: the address is a lookup key
    matched against the signed-in user's own JWT email, never a delivery
    target, so the app never depends on it being routable.
    """

    email: str = Field(max_length=254)
    role: OrgRole = "member"

    @field_validator("email")
    @classmethod
    def _normalized_email(cls, value: str) -> str:
        email = value.strip().lower()
        local, _, domain = email.partition("@")
        if not local or "." not in domain or domain.startswith("."):
            raise ValueError("Enter a valid email address.")
        return email


class OrgMemberResponse(BaseModel):
    """One membership row. ``pending`` is True until the invited email has
    signed up and had the row claimed (no linked auth user yet)."""

    id: str
    email: str
    role: OrgRole
    pending: bool
    created_at: str
