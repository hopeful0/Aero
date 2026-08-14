import pytest
from sqlalchemy import select

from app.models import (
    AuditLog,
    HumanUser,
)
from app.repos import AgentRepo, ArtifactRepo, AuditRepo, FeedbackRepo, ProjectRepo
from app.schemas.artifact import SearchParams


@pytest.mark.asyncio
async def test_create_and_query_full_flow(session):
    project_repo = ProjectRepo(session)
    agent_repo = AgentRepo(session)
    artifact_repo = ArtifactRepo(session)
    feedback_repo = FeedbackRepo(session)
    audit_repo = AuditRepo(session)

    human = HumanUser(name="alice", email="alice@example.com", password_hash="hash")
    session.add(human)
    await session.flush()

    project = await project_repo.create_project(name="alpha-project")
    agent = await agent_repo.create_agent(
        name="builder-agent",
        token_hash="hashed-token",
        owner_human_id=human.id,
    )

    assert project.project_id.startswith("proj_")
    assert agent.agent_id.startswith("agent_")
    assert human.human_id.startswith("user_")

    fetched_project = await project_repo.get_by_project_id(project.project_id)
    assert fetched_project is not None
    assert fetched_project.id == project.id

    fetched_agent = await agent_repo.get_by_token_hash("hashed-token")
    assert fetched_agent is not None
    assert fetched_agent.owner_human_id == human.id

    artifact = await artifact_repo.create_artifact(
        project_pk=project.id,
        title="Design Doc v1",
        summary="initial design",
        artifact_type="markdown",
        tags=["design", "backend"],
        creator_agent_pk=agent.id,
        owner_human_pk=human.id,
    )
    assert artifact.artifact_id.startswith("art_")
    assert artifact.current_version == 1

    v1 = await artifact_repo.insert_version(
        artifact_pk=artifact.id,
        version_no=1,
        title="Design Doc v1",
        summary="initial design",
        content="# Hello\n\nworld",
        content_format="markdown",
        changelog=None,
        created_by_agent_pk=agent.id,
    )

    fetched_v1 = await artifact_repo.get_version(artifact.id, 1)
    assert fetched_v1 is not None
    assert fetched_v1.content == "# Hello\n\nworld"
    assert fetched_v1.id == v1.id

    versions = await artifact_repo.get_versions(artifact.id)
    assert len(versions) == 1

    feedback = await feedback_repo.create_feedback(
        artifact_pk=artifact.id,
        version_no=1,
        author_human_pk=human.id,
        kind="comment",
        body="looks good but missing error handling",
        inline_anchor={"block_id": "b1", "selector": "p:nth-child(2)"},
    )
    assert feedback.id is not None

    feedbacks = await feedback_repo.list_feedback(artifact.id, version_no=1)
    assert len(feedbacks) == 1
    assert feedbacks[0].body == "looks good but missing error handling"
    assert feedbacks[0].inline_anchor["block_id"] == "b1"

    audit = await audit_repo.write_audit_log(
        event="publish",
        actor_agent_id=agent.id,
        on_behalf_of_human_id=human.id,
        target_artifact_id=artifact.id,
        target_version_no=1,
        payload={"title": "Design Doc v1"},
    )
    assert audit.id is not None
    assert audit.on_behalf_of_human_id == human.id

    result = await session.execute(
        select(AuditLog).where(AuditLog.actor_agent_id == agent.id)
    )
    logs = list(result.scalars().all())
    assert len(logs) == 1
    assert logs[0].event == "publish"

    await session.commit()


@pytest.mark.asyncio
async def test_optimistic_lock_version_increment(session):
    project_repo = ProjectRepo(session)
    agent_repo = AgentRepo(session)
    artifact_repo = ArtifactRepo(session)

    human = HumanUser(name="bob", email="bob@example.com", password_hash="hash")
    session.add(human)
    await session.flush()

    project = await project_repo.create_project(name="beta-project")
    agent = await agent_repo.create_agent(
        name="coder-agent", token_hash="token2", owner_human_id=human.id
    )
    artifact = await artifact_repo.create_artifact(
        project_pk=project.id,
        title="Report",
        summary="a report",
        artifact_type="markdown",
        tags=["report"],
        creator_agent_pk=agent.id,
        owner_human_pk=human.id,
    )
    await artifact_repo.insert_version(
        artifact_pk=artifact.id,
        version_no=1,
        title="Report",
        summary="a report",
        content="v1 content",
        content_format="markdown",
        changelog=None,
        created_by_agent_pk=agent.id,
    )

    await artifact_repo.insert_version(
        artifact_pk=artifact.id,
        version_no=2,
        title="Report v2",
        summary="a report v2",
        content="v2 content",
        content_format="markdown",
        changelog="updated",
        created_by_agent_pk=agent.id,
    )
    affected = await artifact_repo.update_current_version(artifact.id, 2)
    assert affected == 1

    refreshed = await artifact_repo.get_artifact(artifact.id)
    assert refreshed is not None
    assert refreshed.current_version == 2

    stale = await artifact_repo.update_current_version(artifact.id, 2)
    assert stale == 0

    await session.commit()


@pytest.mark.asyncio
async def test_list_artifacts_with_filters(session):
    project_repo = ProjectRepo(session)
    agent_repo = AgentRepo(session)
    artifact_repo = ArtifactRepo(session)

    human = HumanUser(name="carol", email="carol@example.com", password_hash="hash")
    session.add(human)
    await session.flush()

    project = await project_repo.create_project(name="gamma-project")
    agent = await agent_repo.create_agent(
        name="search-agent", token_hash="token3", owner_human_id=human.id
    )

    await artifact_repo.create_artifact(
        project_pk=project.id,
        title="Doc A",
        summary="a",
        artifact_type="markdown",
        tags=["frontend"],
        creator_agent_pk=agent.id,
        owner_human_pk=human.id,
    )
    await artifact_repo.create_artifact(
        project_pk=project.id,
        title="Doc B",
        summary="b",
        artifact_type="code",
        tags=["backend"],
        creator_agent_pk=agent.id,
        owner_human_pk=human.id,
    )

    results = await artifact_repo.list_artifacts(
        SearchParams(project_id=project.project_id)
    )
    assert len(results) == 2

    results = await artifact_repo.list_artifacts(
        SearchParams(project_id=project.project_id, type="markdown")
    )
    assert len(results) == 1
    assert results[0].title == "Doc A"

    results = await artifact_repo.list_artifacts(
        SearchParams(project_id=project.project_id, tags=["backend"])
    )
    assert len(results) == 1
    assert results[0].title == "Doc B"

    await session.commit()


@pytest.mark.asyncio
async def test_context_snapshot_and_lineage(session):
    project_repo = ProjectRepo(session)
    agent_repo = AgentRepo(session)
    artifact_repo = ArtifactRepo(session)

    human = HumanUser(name="dave", email="dave@example.com", password_hash="hash")
    session.add(human)
    await session.flush()

    project = await project_repo.create_project(name="delta-project")
    agent = await agent_repo.create_agent(
        name="fork-agent", token_hash="token4", owner_human_id=human.id
    )

    snap = await artifact_repo.create_context_snapshot(
        prompt_snapshot="generate a design doc",
        external_refs={"task_id": "T-100", "trace_id": "tr-abc"},
        execution_trace_id="exec-001",
    )
    assert snap.snapshot_id.startswith("snap_")
    assert snap.external_refs["task_id"] == "T-100"

    parent = await artifact_repo.create_artifact(
        project_pk=project.id,
        title="Parent Artifact",
        summary="parent",
        artifact_type="markdown",
        tags=["parent"],
        creator_agent_pk=agent.id,
        owner_human_pk=human.id,
    )
    await artifact_repo.insert_version(
        artifact_pk=parent.id,
        version_no=1,
        title="Parent Artifact",
        summary="parent",
        content="parent content",
        content_format="markdown",
        changelog=None,
        created_by_agent_pk=agent.id,
        context_snapshot_pk=snap.id,
    )

    child = await artifact_repo.create_artifact(
        project_pk=project.id,
        title="Child Artifact",
        summary="child fork",
        artifact_type="markdown",
        tags=["child"],
        creator_agent_pk=agent.id,
        owner_human_pk=human.id,
    )
    await artifact_repo.insert_version(
        artifact_pk=child.id,
        version_no=1,
        title="Child Artifact",
        summary="child fork",
        content="child content",
        content_format="markdown",
        changelog=None,
        created_by_agent_pk=agent.id,
    )

    lineage = await artifact_repo.insert_fork_lineage(
        child_artifact_pk=child.id,
        parent_artifact_pk=parent.id,
        parent_version_no=1,
        forked_by_agent_pk=agent.id,
        fork_note="forked for alternative approach",
    )
    assert lineage.child_artifact_id == child.id
    assert lineage.parent_artifact_id == parent.id

    fetched = await artifact_repo.get_lineage(child.id)
    assert fetched is not None
    assert fetched.parent_version_no == 1
    assert fetched.fork_note == "forked for alternative approach"

    parent_v1 = await artifact_repo.get_version(parent.id, 1)
    assert parent_v1 is not None
    assert parent_v1.context_snapshot_id == snap.id

    await session.commit()
