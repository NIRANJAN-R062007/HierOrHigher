"""Recruiter orgs: creation, membership gating, and email invites.

The gating assertions here are the load-bearing ones for the whole recruiter
side — every posting, candidate, and application route sits behind the same
membership check, so if an org leaks, everything under it leaks.
"""

from app.api import deps
from app.main import app
from tests.conftest import TEST_USER_ID

TEAMMATE_ID = "22222222-2222-2222-2222-222222222222"
TEAMMATE_EMAIL = "teammate@example.com"
OUTSIDER_ID = "33333333-3333-3333-3333-333333333333"


def as_user(user_id: str, email: str) -> None:
    """Swap the authenticated identity for the rest of the test.

    The client fixture clears dependency_overrides on teardown, so this never
    leaks into another test.
    """
    app.dependency_overrides[deps.get_current_user] = lambda: deps.AuthenticatedUser(
        id=user_id, email=email
    )


def create_org(client, name="CloudCore Recruiting"):
    return client.post("/api/organizations", json={"name": name})


def test_creating_an_org_makes_the_creator_an_admin(client):
    response = create_org(client)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "CloudCore Recruiting"
    assert body["role"] == "admin"
    assert body["id"]

    listing = client.get("/api/organizations")
    assert [o["id"] for o in listing.json()] == [body["id"]]


def test_org_name_is_trimmed_and_length_checked(client):
    assert create_org(client, "  Acme   Talent  ").json()["name"] == "Acme Talent"
    assert create_org(client, "A").status_code == 422


def test_an_org_is_invisible_to_non_members(client):
    org_id = create_org(client).json()["id"]

    as_user(OUTSIDER_ID, "outsider@example.com")
    assert client.get("/api/organizations").json() == []
    # 404 rather than 403: a non-member must not be able to tell an existing
    # org from one that never existed.
    assert client.get(f"/api/organizations/{org_id}/members").status_code == 404


def test_creator_is_listed_as_a_claimed_member(client):
    org_id = create_org(client).json()["id"]
    members = client.get(f"/api/organizations/{org_id}/members").json()

    assert len(members) == 1
    assert members[0]["email"] == "test@example.com"
    assert members[0]["role"] == "admin"
    assert members[0]["pending"] is False


def test_invite_stays_pending_until_the_invitee_signs_in(client):
    org_id = create_org(client).json()["id"]
    invite = client.post(
        f"/api/organizations/{org_id}/members",
        json={"email": "Teammate@Example.com", "role": "member"},
    )
    assert invite.status_code == 200
    assert invite.json()["email"] == TEAMMATE_EMAIL, "email is normalized"
    assert invite.json()["pending"] is True

    # No auth user was created for the invitee: the row is claimed the first
    # time that address signs in through the normal Supabase flow.
    as_user(TEAMMATE_ID, TEAMMATE_EMAIL)
    orgs = client.get("/api/organizations").json()
    assert [o["id"] for o in orgs] == [org_id]
    assert orgs[0]["role"] == "member"

    members = client.get(f"/api/organizations/{org_id}/members").json()
    claimed = next(m for m in members if m["email"] == TEAMMATE_EMAIL)
    assert claimed["pending"] is False, "signing in claims the invite"


def test_reinviting_an_existing_member_is_idempotent(client):
    org_id = create_org(client).json()["id"]
    first = client.post(
        f"/api/organizations/{org_id}/members", json={"email": TEAMMATE_EMAIL}
    )
    second = client.post(
        f"/api/organizations/{org_id}/members", json={"email": TEAMMATE_EMAIL}
    )

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(client.get(f"/api/organizations/{org_id}/members").json()) == 2


def test_only_admins_can_invite(client):
    org_id = create_org(client).json()["id"]
    client.post(
        f"/api/organizations/{org_id}/members",
        json={"email": TEAMMATE_EMAIL, "role": "member"},
    )

    as_user(TEAMMATE_ID, TEAMMATE_EMAIL)
    response = client.post(
        f"/api/organizations/{org_id}/members", json={"email": "someone@example.com"}
    )
    # 403, not 404: a member already knows the org exists, so naming the
    # reason is safe and more useful than pretending it is missing.
    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()


def test_non_members_cannot_invite_themselves_in(client):
    org_id = create_org(client).json()["id"]

    as_user(OUTSIDER_ID, "outsider@example.com")
    response = client.post(
        f"/api/organizations/{org_id}/members",
        json={"email": "outsider@example.com", "role": "admin"},
    )
    assert response.status_code == 404


def test_invalid_invite_email_is_rejected(client):
    org_id = create_org(client).json()["id"]
    response = client.post(
        f"/api/organizations/{org_id}/members", json={"email": "not-an-email"}
    )
    assert response.status_code == 422


def test_orgs_do_not_leak_across_accounts(client):
    mine = create_org(client, "Mine").json()["id"]

    as_user(OUTSIDER_ID, "outsider@example.com")
    theirs = create_org(client, "Theirs").json()["id"]
    assert [o["id"] for o in client.get("/api/organizations").json()] == [theirs]

    as_user(TEST_USER_ID, "test@example.com")
    assert [o["id"] for o in client.get("/api/organizations").json()] == [mine]
