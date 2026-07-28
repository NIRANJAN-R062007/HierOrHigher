"""Routes for recruiter organizations and their members.

Every route here is authenticated and org-membership-gated by the service
layer (app/services/org_service.py), which raises ``OrgAccessError`` /
``OrgPermissionError``; app/main.py maps those to 404 / 403 once, so no
handler repeats the check. Uses no Gemini key.
"""

from fastapi import APIRouter, Depends

from app.api.deps import AuthenticatedUser, get_current_user, get_repository
from app.models.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrgMemberInvite,
    OrgMemberResponse,
)
from app.services import org_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationResponse)
def create_organization(
    payload: OrganizationCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> OrganizationResponse:
    """Create an org; the caller becomes its first admin.

    This is how an existing account becomes a recruiter — there is no separate
    recruiter sign-up, just the Supabase session the app already has.
    """
    return org_service.create_organization(user.id, user.email, payload.name, repo)


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> list[OrganizationResponse]:
    """Orgs the caller belongs to, including any they were invited to before
    signing up (matched on their verified session email)."""
    return org_service.list_organizations(user.id, user.email, repo)


@router.get("/{org_id}/members", response_model=list[OrgMemberResponse])
def list_members(
    org_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> list[OrgMemberResponse]:
    """The org's roster, visible to any member."""
    return org_service.list_members(user.id, user.email, org_id, repo)


@router.post("/{org_id}/members", response_model=OrgMemberResponse)
def invite_member(
    org_id: str,
    payload: OrgMemberInvite,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> OrgMemberResponse:
    """Invite a teammate by email (admin-only).

    Creates no account for them: the invite is a membership row they claim by
    signing up through the normal flow with that address.
    """
    return org_service.invite_member(
        user.id, user.email, org_id, payload.email, payload.role, repo
    )
