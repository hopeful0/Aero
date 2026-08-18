import pytest
from sqlalchemy import select

from app.models.agent import Agent
from app.models.artifact import Artifact
from app.models.audit import AuditLog
from app.models.project import HumanUser

BASE = "http://test/api/v1"


@pytest.mark.asyncio
async def test_full_api_flow(client, session):
    human_email = "alice@example.com"

    resp = await client.post(
        f"{BASE}/humans",
        json={"name": "alice", "email": human_email, "password": "s3cret-pass"},
    )
    assert resp.status_code == 201, resp.text
    human_id = resp.json()["data"]["human_id"]
    assert human_id.startswith("user_")
    assert "password_hash" not in resp.json()["data"]

    resp = await client.post(
        f"{BASE}/auth/login",
        json={"email": human_email, "password": "s3cret-pass"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["human_id"] == human_id
    assert "aero_session" in resp.cookies

    resp = await client.post(f"{BASE}/projects", json={"name": "alpha-project"})
    assert resp.status_code == 201, resp.text
    project_id = resp.json()["data"]["project_id"]
    assert project_id.startswith("proj_")

    resp = await client.get(f"{BASE}/projects")
    assert resp.status_code == 200, resp.text
    projects = resp.json()["data"]
    assert len(projects) == 1
    assert projects[0]["project_id"] == project_id

    resp = await client.post(
        f"{BASE}/agents",
        json={
            "name": "builder-agent",
            "owner_human_id": human_id,
            "project_id": project_id,
            "role": "both",
        },
    )
    assert resp.status_code == 201, resp.text
    agent_data = resp.json()["data"]
    agent_id = agent_data["agent_id"]
    token = agent_data["token"]
    assert agent_id.startswith("agent_")
    assert "." in token
    assert token.split(".", 1)[0] == agent_id

    agent_headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_id,
            "title": "Design Doc",
            "summary": "initial design",
            "artifact_type": "markdown",
            "content": "# Hello\n\nworld",
            "tags": ["design", "backend"],
            "context": {
                "prompt_snapshot": "generate a design doc",
                "external_refs": {"task_id": "T-8821"},
            },
        },
        headers=agent_headers,
    )
    assert resp.status_code == 201, resp.text
    art = resp.json()["data"]
    artifact_id = art["artifact_id"]
    assert art["version"] == 1
    assert art["web_url"] == f"/artifacts/{artifact_id}"
    assert artifact_id.startswith("art_")

    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/fork",
        json={"new_title": "Design Doc (fork)", "from_version": 1},
        headers=agent_headers,
    )
    assert resp.status_code == 201, resp.text
    fork_data = resp.json()["data"]
    forked_id = fork_data["artifact_id"]
    assert forked_id != artifact_id
    assert fork_data["parent_artifact_id"] == artifact_id
    assert fork_data["parent_version_no"] == 1
    assert forked_id.startswith("art_")

    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/versions",
        json={
            "base_version": 99,
            "content": "stale version content",
        },
        headers=agent_headers,
    )
    assert resp.status_code == 409, resp.text
    err = resp.json()["error"]
    assert err["code"] == "VERSION_CONFLICT"
    assert err["details"]["current_version"] == 1

    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/versions",
        json={
            "base_version": 1,
            "title": "Design Doc v2",
            "summary": "revised design",
            "content": "# Hello v2\n\nadded error handling",
            "changelog": "added error handling section",
            "context": {
                "prompt_snapshot": "revise with error handling",
                "external_refs": {"task_id": "T-8821", "trace_id": "tr-v2"},
            },
        },
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    v2_data = resp.json()["data"]
    assert v2_data["version"] == 2

    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/feedback",
        json={
            "kind": "comment",
            "body": "missing error handling section",
        },
    )
    assert resp.status_code == 201, resp.text
    fb = resp.json()["data"]
    assert fb["kind"] == "comment"
    assert fb["body"] == "missing error handling section"
    assert fb["version_no"] == 2

    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/feedback",
        json={"kind": "thumbs_up"},
    )
    assert resp.status_code == 201, resp.text

    resp = await client.get(
        f"{BASE}/artifacts/{artifact_id}",
        params={"include_context": True, "include_feedback": True},
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["artifact_id"] == artifact_id
    assert data["version"] == 2
    assert data["content"] == "# Hello v2\n\nadded error handling"
    assert data["context"] is not None
    assert data["context"]["prompt_snapshot"] == "revise with error handling"
    assert data["context"]["external_refs"]["trace_id"] == "tr-v2"
    assert len(data["feedback"]) == 2
    kinds = {f["kind"] for f in data["feedback"]}
    assert kinds == {"comment", "thumbs_up"}

    agent_row = (
        await session.execute(select(Agent).where(Agent.agent_id == agent_id))
    ).scalar_one()
    art_row = (
        await session.execute(
            select(Artifact).where(Artifact.artifact_id == artifact_id)
        )
    ).scalar_one()
    fetch_row = (
        await session.execute(select(AuditLog).where(AuditLog.event == "fetch"))
    ).scalar_one()
    assert fetch_row.actor_agent_id == agent_row.id
    assert fetch_row.on_behalf_of_human_id == agent_row.owner_human_id
    assert fetch_row.target_artifact_id == art_row.id
    assert fetch_row.target_version_no == 2
    assert fetch_row.payload["include_feedback"] is True
    assert fetch_row.actor_human_id is None

    resp = await client.get(f"{BASE}/artifacts/{artifact_id}")
    assert resp.status_code == 200, resp.text
    human_row = (
        await session.execute(
            select(HumanUser).where(HumanUser.human_id == human_id)
        )
    ).scalar_one()
    view_row = (
        await session.execute(select(AuditLog).where(AuditLog.event == "view"))
    ).scalar_one()
    assert view_row.actor_human_id == human_row.id
    assert view_row.target_artifact_id == art_row.id
    assert view_row.target_version_no == 2
    assert view_row.on_behalf_of_human_id is None
    assert view_row.actor_agent_id is None

    resp = await client.get(
        f"{BASE}/artifacts/{artifact_id}/versions",
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    versions = resp.json()["data"]
    assert len(versions) == 2
    assert versions[0]["version_no"] == 1
    assert versions[1]["version_no"] == 2

    resp = await client.get(
        f"{BASE}/artifacts",
        params={"project_id": project_id},
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    search_results = resp.json()["data"]
    artifact_ids = {r["artifact_id"] for r in search_results}
    assert artifact_id in artifact_ids
    assert forked_id in artifact_ids
    assert len(search_results) == 2

    resp = await client.get(
        f"{BASE}/artifacts",
        params={"project_id": project_id, "type": "markdown", "tags": ["backend"]},
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    filtered = resp.json()["data"]
    assert len(filtered) == 2

    resp = await client.get(
        f"{BASE}/artifacts",
        params={"project_id": project_id, "tags": ["nonexistent"]},
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["data"]) == 0

    resp = await client.get(
        f"{BASE}/artifacts",
        params={"project_id": project_id, "type": "code"},
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["data"]) == 0

    resp = await client.get(
        f"{BASE}/artifacts/{forked_id}/lineage",
    )
    assert resp.status_code == 200, resp.text
    chain = resp.json()["data"]
    assert len(chain) == 2
    assert chain[0]["artifact_id"] == forked_id
    assert chain[0]["parent"]["artifact_id"] == artifact_id
    assert chain[1]["artifact_id"] == artifact_id
    assert chain[1]["parent"] is None

    resp = await client.get(
        f"{BASE}/artifacts/{artifact_id}/feedback",
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    fbs = resp.json()["data"]
    assert len(fbs) == 2
    assert all(f["author_human_id"].startswith("user_") for f in fbs)


@pytest.mark.asyncio
async def test_agent_self_introspection(client):
    human_email = "carol@example.com"

    resp = await client.post(
        f"{BASE}/humans",
        json={"name": "carol", "email": human_email, "password": "s3cret-pass"},
    )
    assert resp.status_code == 201
    human_id = resp.json()["data"]["human_id"]

    resp = await client.post(
        f"{BASE}/auth/login",
        json={"email": human_email, "password": "s3cret-pass"},
    )
    assert resp.status_code == 200

    resp = await client.post(f"{BASE}/projects", json={"name": "introspect-proj"})
    assert resp.status_code == 201
    project_id = resp.json()["data"]["project_id"]

    resp = await client.post(
        f"{BASE}/agents",
        json={
            "name": "self-aware-agent",
            "owner_human_id": human_id,
            "project_id": project_id,
            "role": "both",
        },
    )
    assert resp.status_code == 201
    agent_data = resp.json()["data"]
    agent_id = agent_data["agent_id"]
    token = agent_data["token"]

    resp = await client.get(
        f"{BASE}/agents/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["agent_id"] == agent_id
    assert data["name"] == "self-aware-agent"
    assert data["owner_human_id"] == human_id
    assert data["is_active"] is True
    assert len(data["projects"]) == 1
    scope = data["projects"][0]
    assert scope["project_id"] == project_id
    assert scope["name"] == "introspect-proj"
    assert scope["role"] == "both"

    resp = await client.get(
        f"{BASE}/agents/me",
        headers={"Authorization": "Bearer bad-token"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_failures(client):
    resp = await client.post(
        f"{BASE}/humans",
        json={"name": "bob", "email": "bob@example.com", "password": "pw1"},
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"{BASE}/auth/login",
        json={"email": "bob@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    resp = await client.post(
        f"{BASE}/projects",
        json={"name": "no-auth"},
    )
    assert resp.status_code == 401

    resp = await client.get(
        f"{BASE}/artifacts/some-id",
        headers={"Authorization": "Bearer bad-token"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_visibility(client, session):
    resp = await client.post(
        f"{BASE}/humans",
        json={"name": "vis-user", "email": "vis@example.com", "password": "s3cret-pass"},
    )
    assert resp.status_code == 201
    human_id = resp.json()["data"]["human_id"]

    resp = await client.post(
        f"{BASE}/auth/login",
        json={"email": "vis@example.com", "password": "s3cret-pass"},
    )
    assert resp.status_code == 200

    resp = await client.post(f"{BASE}/projects", json={"name": "vis-proj-a"})
    assert resp.status_code == 201
    project_a_id = resp.json()["data"]["project_id"]

    resp = await client.post(f"{BASE}/projects", json={"name": "vis-proj-b"})
    assert resp.status_code == 201
    project_b_id = resp.json()["data"]["project_id"]

    resp = await client.post(
        f"{BASE}/agents",
        json={
            "name": "vis-agent-a",
            "owner_human_id": human_id,
            "project_id": project_a_id,
            "role": "both",
        },
    )
    assert resp.status_code == 201
    agent_a_headers = {"Authorization": f"Bearer {resp.json()['data']['token']}"}

    resp = await client.post(
        f"{BASE}/agents",
        json={
            "name": "vis-agent-b",
            "owner_human_id": human_id,
            "project_id": project_b_id,
            "role": "both",
        },
    )
    assert resp.status_code == 201
    agent_b_headers = {"Authorization": f"Bearer {resp.json()['data']['token']}"}

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_a_id,
            "title": "Public Doc",
            "artifact_type": "markdown",
            "content": "# Public",
            "tags": ["public-tag"],
            "context": {
                "prompt_snapshot": "public prompt",
                "external_refs": {"task_id": "T-pub"},
            },
            "visibility": "public",
        },
        headers=agent_a_headers,
    )
    assert resp.status_code == 201
    public_art_id = resp.json()["data"]["artifact_id"]
    assert resp.json()["data"]["visibility"] == "public"

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_a_id,
            "title": "Private Doc",
            "artifact_type": "markdown",
            "content": "# Private",
            "visibility": "private",
        },
        headers=agent_a_headers,
    )
    assert resp.status_code == 201
    private_art_id = resp.json()["data"]["artifact_id"]
    assert resp.json()["data"]["visibility"] == "private"

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_a_id,
            "title": "Default Doc",
            "artifact_type": "markdown",
            "content": "# Default",
        },
        headers=agent_a_headers,
    )
    assert resp.status_code == 201
    default_art_id = resp.json()["data"]["artifact_id"]
    assert resp.json()["data"]["visibility"] == "private"

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_a_id,
            "title": "Bad Vis",
            "artifact_type": "markdown",
            "content": "# bad",
            "visibility": "org",
        },
        headers=agent_a_headers,
    )
    assert resp.status_code == 422

    client.cookies.clear()

    resp = await client.get(f"{BASE}/artifacts")
    assert resp.status_code == 200
    items = resp.json()["data"]
    art_ids = {i["artifact_id"] for i in items}
    assert public_art_id in art_ids
    assert private_art_id not in art_ids
    assert default_art_id not in art_ids
    assert all(i["visibility"] == "public" for i in items)

    resp = await client.get(
        f"{BASE}/artifacts/{public_art_id}",
        params={"include_context": True, "include_feedback": True},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["artifact_id"] == public_art_id
    assert data["content"] == "# Public"
    assert data["visibility"] == "public"
    assert data["context"] is not None
    assert data["context"]["prompt_snapshot"] == "public prompt"
    assert "feedback" not in data

    anon_audit = (
        await session.execute(
            select(AuditLog).where(AuditLog.event.in_(["fetch", "view"]))
        )
    ).all()
    assert anon_audit == []

    resp = await client.get(f"{BASE}/artifacts/{private_art_id}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"

    resp = await client.get(f"{BASE}/artifacts/{private_art_id}/versions")
    assert resp.status_code == 404

    resp = await client.get(f"{BASE}/artifacts/{public_art_id}/versions")
    assert resp.status_code == 200
    versions = resp.json()["data"]
    assert len(versions) == 1
    assert versions[0]["version_no"] == 1

    resp = await client.get(f"{BASE}/artifacts/{public_art_id}/lineage")
    assert resp.status_code == 401

    resp = await client.get(f"{BASE}/artifacts/{public_art_id}/feedback")
    assert resp.status_code == 401

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_a_id,
            "title": "Anon Attempt",
            "content": "# anon",
        },
    )
    assert resp.status_code == 401

    resp = await client.post(
        f"{BASE}/artifacts/{public_art_id}/fork",
        json={"new_title": "Anon Fork"},
    )
    assert resp.status_code == 401

    resp = await client.get(f"{BASE}/artifacts", headers=agent_a_headers)
    assert resp.status_code == 200
    items = resp.json()["data"]
    art_ids = {i["artifact_id"] for i in items}
    assert public_art_id in art_ids
    assert private_art_id in art_ids
    assert default_art_id in art_ids

    resp = await client.get(
        f"{BASE}/artifacts/{public_art_id}",
        headers=agent_b_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["artifact_id"] == public_art_id

    resp = await client.get(
        f"{BASE}/artifacts/{private_art_id}",
        headers=agent_b_headers,
    )
    assert resp.status_code == 403

    resp = await client.get(f"{BASE}/artifacts", headers=agent_b_headers)
    assert resp.status_code == 200
    items = resp.json()["data"]
    art_ids = {i["artifact_id"] for i in items}
    assert public_art_id in art_ids
    assert private_art_id not in art_ids

    resp = await client.post(
        f"{BASE}/artifacts/{public_art_id}/fork",
        json={"new_title": "Forked Public"},
        headers=agent_a_headers,
    )
    assert resp.status_code == 201
    forked_id = resp.json()["data"]["artifact_id"]

    resp = await client.get(
        f"{BASE}/artifacts/{forked_id}",
        headers=agent_a_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["visibility"] == "private"

    client.cookies.clear()
    resp = await client.get(f"{BASE}/artifacts/{forked_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_change_visibility(client):
    owner_email = "cv-owner@example.com"
    resp = await client.post(
        f"{BASE}/humans",
        json={"name": "cv-owner", "email": owner_email, "password": "s3cret-pass"},
    )
    assert resp.status_code == 201
    owner_id = resp.json()["data"]["human_id"]

    resp = await client.post(
        f"{BASE}/auth/login",
        json={"email": owner_email, "password": "s3cret-pass"},
    )
    assert resp.status_code == 200

    resp = await client.post(f"{BASE}/projects", json={"name": "cv-proj"})
    assert resp.status_code == 201
    project_id = resp.json()["data"]["project_id"]

    resp = await client.post(
        f"{BASE}/agents",
        json={
            "name": "cv-agent",
            "owner_human_id": owner_id,
            "project_id": project_id,
            "role": "both",
        },
    )
    assert resp.status_code == 201
    agent_headers = {"Authorization": f"Bearer {resp.json()['data']['token']}"}

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_id,
            "title": "CV Doc",
            "artifact_type": "markdown",
            "content": "# CV",
            "visibility": "private",
        },
        headers=agent_headers,
    )
    assert resp.status_code == 201
    artifact_id = resp.json()["data"]["artifact_id"]
    assert resp.json()["data"]["visibility"] == "private"

    resp = await client.patch(
        f"{BASE}/artifacts/{artifact_id}",
        json={"visibility": "public"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {
        "artifact_id": artifact_id,
        "visibility": "public",
    }

    resp = await client.patch(
        f"{BASE}/artifacts/{artifact_id}",
        json={"visibility": "private"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["visibility"] == "private"

    reader_email = "cv-reader@example.com"
    resp = await client.post(
        f"{BASE}/humans",
        json={
            "name": "cv-reader",
            "email": reader_email,
            "password": "s3cret-pass",
        },
    )
    assert resp.status_code == 201
    resp = await client.post(
        f"{BASE}/auth/login",
        json={"email": reader_email, "password": "s3cret-pass"},
    )
    assert resp.status_code == 200
    resp = await client.patch(
        f"{BASE}/artifacts/{artifact_id}",
        json={"visibility": "public"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "FORBIDDEN"

    client.cookies.clear()
    resp = await client.patch(
        f"{BASE}/artifacts/{artifact_id}",
        json={"visibility": "public"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    resp = await client.post(
        f"{BASE}/auth/login",
        json={"email": owner_email, "password": "s3cret-pass"},
    )
    assert resp.status_code == 200
    resp = await client.patch(
        f"{BASE}/artifacts/art_nonexistent_id",
        json={"visibility": "public"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "NOT_FOUND"

    resp = await client.patch(
        f"{BASE}/artifacts/{artifact_id}",
        json={"visibility": "org"},
    )
    assert resp.status_code == 422, resp.text
