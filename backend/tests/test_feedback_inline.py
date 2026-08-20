import pytest

BASE = "http://test/api/v1"

from app.repos.human import HumanRepo  # noqa: E402
from app.repos.project import ProjectRepo  # noqa: E402


async def _setup_human_project_agent(client):
    resp = await client.post(
        f"{BASE}/humans",
        json={"name": "fb-user", "email": "fb@example.com", "password": "s3cret-pass"},
    )
    assert resp.status_code == 201, resp.text
    human_id = resp.json()["data"]["human_id"]

    resp = await client.post(
        f"{BASE}/auth/login",
        json={"email": "fb@example.com", "password": "s3cret-pass"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(f"{BASE}/projects", json={"name": "fb-proj"})
    assert resp.status_code == 201, resp.text
    project_id = resp.json()["data"]["project_id"]

    resp = await client.post(
        f"{BASE}/agents",
        json={
            "name": "fb-agent",
            "owner_human_id": human_id,
            "project_id": project_id,
            "role": "both",
        },
    )
    assert resp.status_code == 201, resp.text
    agent_headers = {"Authorization": f"Bearer {resp.json()['data']['token']}"}
    return human_id, project_id, agent_headers


@pytest.mark.asyncio
async def test_feedback_create_with_valid_block_id(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_id,
            "title": "Doc",
            "artifact_type": "markdown",
            "content": "# Title\n\nhello world\n",
        },
        headers=agent_headers,
    )
    assert resp.status_code == 201, resp.text
    artifact_id = resp.json()["data"]["artifact_id"]

    blocks = await _get_blocks(client, artifact_id, 1)
    para_block = next(b for b in blocks if b["block_path"].endswith("p[0]"))
    block_id = para_block["block_id"]

    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/feedback",
        json={
            "kind": "comment",
            "body": "nice paragraph",
            "block_id": block_id,
            "version_no": 1,
            "selector": "p:nth-child(2)",
        },
    )
    assert resp.status_code == 201, resp.text
    fb = resp.json()["data"]
    assert fb["inline_anchor"]["block_id"] == block_id
    assert fb["inline_anchor"]["block_path"] == para_block["block_path"]
    assert fb["inline_anchor"]["block_text"] == para_block["block_text"]
    assert fb["inline_anchor"]["selector"] == "p:nth-child(2)"
    assert fb["inline_anchor"]["version_no"] == 1


@pytest.mark.asyncio
async def test_feedback_create_denied_for_read_only_human(client, session):
    # 只读（consumer）human 有读权限但无写权限：不能提交反馈，但可以读列表。
    _, project_id, agent_headers = await _setup_human_project_agent(client)

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_id,
            "title": "ReadOnlyDoc",
            "artifact_type": "markdown",
            "content": "# Title\n\nbody\n",
        },
        headers=agent_headers,
    )
    assert resp.status_code == 201, resp.text
    artifact_id = resp.json()["data"]["artifact_id"]

    resp = await client.post(
        f"{BASE}/humans",
        json={"name": "ro-user", "email": "ro@example.com", "password": "s3cret-pass"},
    )
    assert resp.status_code == 201, resp.text
    ro_human = await HumanRepo(session).get_by_human_id(
        resp.json()["data"]["human_id"]
    )
    project = await ProjectRepo(session).get_by_project_id(project_id)
    await ProjectRepo(session).grant_human_scope(ro_human.id, project.id, role="consumer")
    await session.commit()

    resp = await client.post(
        f"{BASE}/auth/login",
        json={"email": "ro@example.com", "password": "s3cret-pass"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/feedback",
        json={"kind": "comment", "body": "should be denied"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "FORBIDDEN"

    resp = await client.get(f"{BASE}/artifacts/{artifact_id}/feedback")
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_feedback_create_with_invalid_block_id_rejected(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_id,
            "title": "Doc",
            "artifact_type": "markdown",
            "content": "# Title\n\nhello\n",
        },
        headers=agent_headers,
    )
    assert resp.status_code == 201, resp.text
    artifact_id = resp.json()["data"]["artifact_id"]

    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/feedback",
        json={
            "kind": "comment",
            "body": "bad anchor",
            "block_id": "deadbeefdeadbeef",
            "version_no": 1,
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "INVALID_ANCHOR"


@pytest.mark.asyncio
async def test_feedback_list_returns_migration_status(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)

    # v1: 一段较长的段落
    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_id,
            "title": "Doc",
            "artifact_type": "markdown",
            "content": "## A\n\nhello world this is a longer paragraph here\n",
        },
        headers=agent_headers,
    )
    assert resp.status_code == 201, resp.text
    artifact_id = resp.json()["data"]["artifact_id"]

    blocks = await _get_blocks(client, artifact_id, 1)
    para_block = next(b for b in blocks if b["block_path"].endswith("p[0]"))

    # 在 v1 上针对该段落创建行内评论
    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/feedback",
        json={
            "kind": "comment",
            "body": "comment on v1 para",
            "block_id": para_block["block_id"],
            "version_no": 1,
        },
    )
    assert resp.status_code == 201, resp.text

    # v2: 小幅编辑该段落（fuzzy）
    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/versions",
        json={
            "base_version": 1,
            "content": "## A\n\nhello world this is a longer paragraph here edited\n",
        },
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["version"] == 2

    # 列表（查看 v2）: 行内评论应带 migration_status
    resp = await client.get(
        f"{BASE}/artifacts/{artifact_id}/feedback",
        params={"version": 2},
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    fbs = resp.json()["data"]
    assert len(fbs) == 1
    inline_fb = fbs[0]
    assert inline_fb["inline_anchor"]["block_id"] == para_block["block_id"]
    status = inline_fb["migration_status"]
    assert status in {"exact", "fuzzy", "stale"}
    # 内容小幅编辑、block_path 不变 -> fuzzy
    assert status == "fuzzy"


@pytest.mark.asyncio
async def test_feedback_list_old_style_comment_without_block_id(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)

    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_id,
            "title": "Doc",
            "artifact_type": "markdown",
            "content": "# Title\n\nhello\n",
        },
        headers=agent_headers,
    )
    assert resp.status_code == 201, resp.text
    artifact_id = resp.json()["data"]["artifact_id"]

    resp = await client.post(
        f"{BASE}/artifacts/{artifact_id}/feedback",
        json={"kind": "comment", "body": "version-level comment"},
    )
    assert resp.status_code == 201, resp.text

    resp = await client.get(
        f"{BASE}/artifacts/{artifact_id}/feedback",
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    fbs = resp.json()["data"]
    assert len(fbs) == 1
    assert fbs[0]["inline_anchor"] is None
    assert fbs[0]["migration_status"] is None


@pytest.mark.asyncio
async def test_version_blocks_endpoint(client):
    _, project_id, agent_headers = await _setup_human_project_agent(client)

    content = "# Title\n\nfirst para\n\nsecond para\n"
    resp = await client.post(
        f"{BASE}/artifacts",
        json={
            "project_id": project_id,
            "title": "Doc",
            "artifact_type": "markdown",
            "content": content,
        },
        headers=agent_headers,
    )
    assert resp.status_code == 201, resp.text
    artifact_id = resp.json()["data"]["artifact_id"]

    resp = await client.get(
        f"{BASE}/artifacts/{artifact_id}/versions/1/blocks",
        headers=agent_headers,
    )
    assert resp.status_code == 200, resp.text
    blocks = resp.json()["data"]
    assert len(blocks) == 3
    assert blocks[0]["block_path"] == "h1:Title"
    assert blocks[1]["block_path"] == "h1:Title > p[0]"
    assert blocks[2]["block_path"] == "h1:Title > p[1]"
    for b in blocks:
        assert "block_id" in b
        assert "block_text" in b
        assert "content_preview" in b
        assert "block_index" in b


async def _get_blocks(client, artifact_id, version_no):
    resp = await client.get(
        f"{BASE}/artifacts/{artifact_id}/versions/{version_no}/blocks",
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]
