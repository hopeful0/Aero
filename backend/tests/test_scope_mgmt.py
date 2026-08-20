"""A-2 scope 授予管理侧端点测试。

覆盖：
- GET /agents 可见集（自己创建的 agent 可见；与他人有共同 project scope 的 agent 可见）。
- POST /agents/{id}/scopes 追加/更新（幂等 upsert），并落 audit agent_scope_grant。
- DELETE /agents/{id}/scopes/{project_id} 回收（幂等），落 audit agent_scope_revoke。
- 权限：无 write scope 的 human 追加/回收 → FORBIDDEN；owner 无该 project scope → BAD_REQUEST。
- 404 语义：不存在的 agent / project 返回 BAD_REQUEST（同 create_agent 一致）。
"""

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.project import HumanProjectScope, HumanUser, Project

BASE = "http://test/api/v1"

PASSWORD = "s3cret-pass"


async def _register_login(client, name: str) -> str:
    """注册并登录一个 human，返回其 human_id；session cookie 存入 client jar。"""
    email = f"{name}@example.com"
    resp = await client.post(
        f"{BASE}/humans", json={"name": name, "email": email, "password": PASSWORD}
    )
    assert resp.status_code == 201, resp.text
    resp = await client.post(
        f"{BASE}/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["human_id"]


async def _create_project(client, name: str) -> str:
    resp = await client.post(f"{BASE}/projects", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["project_id"]


async def _create_agent(client, name: str, owner: str, project: str, role: str) -> str:
    resp = await client.post(
        f"{BASE}/agents",
        json={
            "name": name,
            "owner_human_id": owner,
            "project_id": project,
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["agent_id"]


@pytest.mark.asyncio
async def test_list_agents_visible_to_owner(client):
    human = await _register_login(client, "alice")
    project = await _create_project(client, "alpha")
    await _create_agent(client, "builder", human, project, "both")

    resp = await client.get(f"{BASE}/agents")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert len(data) == 1
    row = data[0]
    assert row["owner_human_id"] == human
    assert row["name"] == "builder"
    assert len(row["projects"]) == 1
    scope = row["projects"][0]
    assert scope["project_id"] == project
    assert scope["role"] == "both"
    assert scope["current_human_role"] == "both"


@pytest.mark.asyncio
async def test_add_scope_grant_then_list(client):
    human = await _register_login(client, "bob")
    project_a = await _create_project(client, "alpha")
    agent = await _create_agent(client, "worker", human, project_a, "consumer")
    project_b = await _create_project(client, "beta")

    resp = await client.post(
        f"{BASE}/agents/{agent}/scopes",
        json={"project_id": project_b, "role": "publisher"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    project_ids = {p["project_id"] for p in data["projects"]}
    assert {project_a, project_b}.issubset(project_ids)

    resp = await client.get(f"{BASE}/agents")
    scopes = {p["project_id"] for p in resp.json()["data"][0]["projects"]}
    assert project_b in scopes


@pytest.mark.asyncio
async def test_add_scope_updates_role_upsert(client, session):
    human = await _register_login(client, "carol")
    project = await _create_project(client, "alpha")
    agent = await _create_agent(client, "worker", human, project, "consumer")

    resp = await client.post(
        f"{BASE}/agents/{agent}/scopes",
        json={"project_id": project, "role": "both"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert len(data["projects"]) == 1  # 行数不变，仅角色更新
    assert data["projects"][0]["role"] == "both"

    grants = (
        await session.execute(
            select(AuditLog).where(AuditLog.event == "agent_scope_grant")
        )
    ).scalars().all()
    # 创建时记录的是 agent_token 事件，仅本次 upsert 落 agent_scope_grant
    assert len(grants) == 1
    assert grants[0].payload["agent_id"] == agent
    assert grants[0].payload["role"] == "both"


@pytest.mark.asyncio
async def test_revoke_scope_idempotent(client, session):
    human = await _register_login(client, "dave")
    project_a = await _create_project(client, "alpha")
    project_b = await _create_project(client, "beta")
    agent = await _create_agent(client, "worker", human, project_a, "both")

    await client.post(
        f"{BASE}/agents/{agent}/scopes",
        json={"project_id": project_b, "role": "consumer"},
    )

    resp = await client.delete(f"{BASE}/agents/{agent}/scopes/{project_b}")
    assert resp.status_code == 200, resp.text
    project_ids = {p["project_id"] for p in resp.json()["data"]["projects"]}
    assert project_b not in project_ids

    # 幂等：再次删除仍 200
    resp = await client.delete(f"{BASE}/agents/{agent}/scopes/{project_b}")
    assert resp.status_code == 200, resp.text

    revokes = (
        await session.execute(
            select(AuditLog).where(AuditLog.event == "agent_scope_revoke")
        )
    ).scalars().all()
    assert len(revokes) == 1  # 第二次为无操作，不落审计
    assert revokes[0].payload["project_id"] == project_b


@pytest.mark.asyncio
async def test_scope_visible_to_human_sharing_project(client, session):
    owner = await _register_login(client, "carol")
    project = await _create_project(client, "alpha")
    await _create_agent(client, "worker", owner, project, "both")

    # dave 登录后看不到该 agent（无共同 project scope）
    dave = await _register_login(client, "dave")
    resp = await client.get(f"{BASE}/agents")
    assert resp.json()["data"] == []

    # 模拟共享：直接给 dave 授 project scope，随后可见
    owner_row = (
        await session.execute(select(HumanUser).where(HumanUser.human_id == owner))
    ).scalar_one()
    dave_row = (
        await session.execute(select(HumanUser).where(HumanUser.human_id == dave))
    ).scalar_one()
    project_row = (
        await session.execute(select(Project).where(Project.project_id == project))
    ).scalar_one()
    session.add(
        HumanProjectScope(
            human_id=dave_row.id, project_id=project_row.id, role="publisher"
        )
    )
    await session.commit()

    resp = await client.get(f"{BASE}/agents")
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["projects"][0]["current_human_role"] == "publisher"
    assert owner_row.id is not None


@pytest.mark.asyncio
async def test_forbidden_when_actor_lacks_write(client):
    owner = await _register_login(client, "eve")
    project = await _create_project(client, "alpha")
    agent = await _create_agent(client, "worker", owner, project, "consumer")

    # 切换登录 faye（cookie jar 覆盖 session），faye 对 project 无 scope
    await _register_login(client, "faye")
    resp = await client.post(
        f"{BASE}/agents/{agent}/scopes",
        json={"project_id": project, "role": "publisher"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "FORBIDDEN"

    resp = await client.delete(f"{BASE}/agents/{agent}/scopes/{project}")
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_owner_subset_rule(client):
    owner = await _register_login(client, "grace")
    project_a = await _create_project(client, "alpha")
    agent = await _create_agent(client, "worker", owner, project_a, "both")

    # mgr 对 project_b 有写权限，但 agent owner(grace) 在 b 无 scope → 违反 subset 应 400
    await _register_login(client, "mgr")
    project_b = await _create_project(client, "beta")
    resp = await client.post(
        f"{BASE}/agents/{agent}/scopes",
        json={"project_id": project_b, "role": "publisher"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_not_found_agent_and_project(client):
    owner = await _register_login(client, "henry")
    project = await _create_project(client, "alpha")

    resp = await client.post(
        f"{BASE}/agents/no-such-agent/scopes",
        json={"project_id": project, "role": "publisher"},
    )
    assert resp.status_code == 400, resp.text

    agent = await _create_agent(client, "worker", owner, project, "both")
    resp = await client.delete(f"{BASE}/agents/{agent}/scopes/no-such-project")
    assert resp.status_code == 400, resp.text