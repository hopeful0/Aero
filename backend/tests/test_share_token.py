import hashlib

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.share_token import ShareToken

BASE = "http://test/api/v1"


async def _setup_human_project_agent(client):
    resp = await client.post(
        f"{BASE}/humans",
        json={"name": "st-owner", "email": "st-owner@example.com", "password": "s3cret-pass"},
    )
    assert resp.status_code == 201, resp.text
    human_id = resp.json()["data"]["human_id"]

    resp = await client.post(
        f"{BASE}/auth/login",
        json={"email": "st-owner@example.com", "password": "s3cret-pass"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(f"{BASE}/projects", json={"name": "st-proj"})
    assert resp.status_code == 201, resp.text
    project_id = resp.json()["data"]["project_id"]

    resp = await client.post(
        f"{BASE}/agents",
        json={
            "name": "st-agent",
            "owner_human_id": human_id,
            "project_id": project_id,
            "role": "both",
        },
    )
    assert resp.status_code == 201, resp.text
    agent_headers = {"Authorization": f"Bearer {resp.json()['data']['token']}"}
    return human_id, project_id, agent_headers


async def _create_artifact(client, agent_headers, project_id, *, visibility="private", title="Doc"):
    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_id,
            "title": title,
            "artifact_type": "markdown",
            "content": "# Title\n\nhello open-aero",
            "visibility": visibility,
            "context": {
                "prompt_snapshot": "gen a doc",
                "external_refs": {"task_id": "T-A1"},
            },
        },
        headers=agent_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["artifact_id"]


async def _create_share_token(client, agent_headers, artifact_id):
    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/share-tokens",
        headers=agent_headers,
        json={},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_share_token_anon_read_private_200(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)
    artifact_id = await _create_artifact(client, agent_headers, project_id, visibility="private")
    created = await _create_share_token(client, agent_headers, artifact_id)

    client.cookies.clear()
    url = created["url"]
    resp = await client.get(f"{BASE}{url}")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["artifact_id"] == artifact_id
    assert data["content"] == "# Title\n\nhello open-aero"
    assert data["context"] is not None
    assert data["context"]["prompt_snapshot"] == "gen a doc"


@pytest.mark.asyncio
async def test_share_token_revoked_403(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)
    artifact_id = await _create_artifact(client, agent_headers, project_id, visibility="private")
    created = await _create_share_token(client, agent_headers, artifact_id)

    client.cookies.clear()
    revoke = await client.delete(
        f"{BASE}/artifacts/{artifact_id}/share-tokens/{created['share_token_id']}",
        headers=agent_headers,
    )
    assert revoke.status_code == 200, revoke.text

    resp = await client.get(f"{BASE}{created['url']}")
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_share_token_anon_without_token_404(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)
    artifact_id = await _create_artifact(client, agent_headers, project_id, visibility="private")

    client.cookies.clear()
    resp = await client.get(f"{BASE}/artifacts/{artifact_id}")
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_share_token_private_not_in_anon_list(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)
    artifact_id = await _create_artifact(client, agent_headers, project_id, visibility="private")
    await _create_share_token(client, agent_headers, artifact_id)

    client.cookies.clear()
    resp = await client.get(f"{BASE}/artifacts")
    assert resp.status_code == 200, resp.text
    ids = {item["artifact_id"] for item in resp.json()["data"]}
    assert artifact_id not in ids


@pytest.mark.asyncio
async def test_share_token_public_still_listed_and_readable(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)
    artifact_id = await _create_artifact(client, agent_headers, project_id, visibility="public")
    created = await _create_share_token(client, agent_headers, artifact_id)

    client.cookies.clear()
    resp = await client.get(f"{BASE}/artifacts")
    assert resp.status_code == 200, resp.text
    ids = {item["artifact_id"] for item in resp.json()["data"]}
    assert artifact_id in ids

    resp = await client.get(f"{BASE}{created['url']}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["artifact_id"] == artifact_id


@pytest.mark.asyncio
async def test_share_token_write_auth_401_and_403(client, session):
    _, project_id, agent_headers = await _setup_human_project_agent(client)
    artifact_id = await _create_artifact(client, agent_headers, project_id, visibility="private")

    client.cookies.clear()
    resp = await client.post(f"{BASE}/artifacts/{artifact_id}/share-tokens", json={})
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    created = await _create_share_token(client, agent_headers, artifact_id)
    client.cookies.clear()
    resp = await client.delete(
        f"{BASE}/artifacts/{artifact_id}/share-tokens/{created['share_token_id']}"
    )
    assert resp.status_code == 401, resp.text

    ro_resp = await client.post(
        f"{BASE}/humans",
        json={"name": "st-ro", "email": "st-ro@example.com", "password": "s3cret-pass"},
    )
    assert ro_resp.status_code == 201, ro_resp.text
    from app.repos.human import HumanRepo
    from app.repos.project import ProjectRepo

    ro_human = await HumanRepo(session).get_by_human_id(ro_resp.json()["data"]["human_id"])
    project = await ProjectRepo(session).get_by_project_id(project_id)
    await ProjectRepo(session).grant_human_scope(ro_human.id, project.id, role="consumer")
    await session.commit()
    login = await client.post(
        f"{BASE}/auth/login",
        json={"email": "st-ro@example.com", "password": "s3cret-pass"},
    )
    assert login.status_code == 200, login.text

    resp = await client.post(f"{BASE}/artifacts/{artifact_id}/share-tokens", json={})
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_share_token_lineage_feedback_anon_still_401(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)
    artifact_id = await _create_artifact(client, agent_headers, project_id, visibility="public")

    client.cookies.clear()
    resp = await client.get(f"{BASE}/artifacts/{artifact_id}/lineage")
    assert resp.status_code == 401, resp.text
    resp = await client.get(f"{BASE}/artifacts/{artifact_id}/feedback")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_share_token_audit_events(client, session):
    _, project_id, agent_headers = await _setup_human_project_agent(client)
    artifact_id = await _create_artifact(client, agent_headers, project_id, visibility="private")
    created = await _create_share_token(client, agent_headers, artifact_id)

    client.cookies.clear()
    resp = await client.get(f"{BASE}{created['url']}")
    assert resp.status_code == 200, resp.text

    client.cookies.clear()
    revoke = await client.delete(
        f"{BASE}/artifacts/{artifact_id}/share-tokens/{created['share_token_id']}",
        headers=agent_headers,
    )
    assert revoke.status_code == 200, revoke.text

    events = {
        row.event: row
        for row in (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.event.in_(
                        ["share_token_created", "share_token_revoked", "share_token_access"]
                    )
                )
            )
        ).scalars()
    }
    assert set(events) == {"share_token_created", "share_token_revoked", "share_token_access"}
    assert events["share_token_created"].payload["share_token_id"] == created["share_token_id"]
    assert events["share_token_revoked"].payload["share_token_id"] == created["share_token_id"]
    access = events["share_token_access"]
    assert access.payload["share_token_id"] == created["share_token_id"]
    assert access.actor_agent_id is None
    assert access.actor_human_id is None
    assert access.on_behalf_of_human_id is None
    for row in events.values():
        assert created["token"] not in str(row.payload)


@pytest.mark.asyncio
async def test_share_token_stores_hash_not_plaintext(client, session):
    _, project_id, agent_headers = await _setup_human_project_agent(client)
    artifact_id = await _create_artifact(client, agent_headers, project_id, visibility="private")
    created = await _create_share_token(client, agent_headers, artifact_id)

    rows = (
        (
            await session.execute(
                select(ShareToken).where(ShareToken.share_token_id == created["share_token_id"])
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    token_hash = rows[0].token_hash
    assert token_hash != created["token"]
    assert token_hash == hashlib.sha256(created["token"].encode("utf-8")).hexdigest()


@pytest.mark.asyncio
async def test_share_token_revoke_idempotent_200(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)
    artifact_id = await _create_artifact(client, agent_headers, project_id, visibility="private")
    created = await _create_share_token(client, agent_headers, artifact_id)

    first = await client.delete(
        f"{BASE}/artifacts/{artifact_id}/share-tokens/{created['share_token_id']}",
        headers=agent_headers,
    )
    assert first.status_code == 200, first.text
    second = await client.delete(
        f"{BASE}/artifacts/{artifact_id}/share-tokens/{created['share_token_id']}",
        headers=agent_headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["data"]["revoked_at"] is not None
