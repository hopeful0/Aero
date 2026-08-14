import pytest

BASE = "http://test/api/v1"


@pytest.mark.asyncio
async def test_full_api_flow(client):
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
    assert resp.status_code == 401
