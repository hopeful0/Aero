import pytest

from app.models.project import HumanUser
from app.repos.agent import AgentRepo
from app.repos.artifact import ArtifactRepo
from app.repos.project import ProjectRepo
from app.services.artifact_service import ArtifactService
from app.services.block_parser import parse_blocks

DUPLICATE_PARAGRAPH_CONTENT = "\n\n".join(
    [
        "# Title",
        "Solve it",
        "Solve it",
        "---",
        "---",
    ]
)


@pytest.mark.asyncio
async def test_publish_with_duplicate_block_ids_and_hr_blocks(session):
    project_repo = ProjectRepo(session)
    agent_repo = AgentRepo(session)

    human = HumanUser(name="dup@example.com", email="dup@example.com", password_hash="hash")
    session.add(human)
    await session.flush()

    project = await project_repo.create_project(name="duplicate-blocks-project")
    agent = await agent_repo.create_agent(
        name="dup-agent",
        token_hash="token-dup",
        owner_human_id=human.id,
    )
    await agent_repo.grant_agent_scope(agent.id, project.id, "both")

    service = ArtifactService(session)
    result = await service.publish(
        agent=agent,
        project_id=project.project_id,
        title="Dup Blocks",
        summary=None,
        artifact_type="markdown",
        content=DUPLICATE_PARAGRAPH_CONTENT,
        tags=[],
        context=None,
        visibility="private",
    )

    assert result["artifact_id"].startswith("art_")

    artifact_repo = ArtifactRepo(session)
    artifact = await artifact_repo.get_artifact_by_artifact_id(result["artifact_id"])
    assert artifact is not None
    version = await artifact_repo.get_version(artifact.id, 1)
    assert version is not None

    blocks = await artifact_repo.list_version_blocks(version.id)
    assert len(blocks) == len(parse_blocks(DUPLICATE_PARAGRAPH_CONTENT))
    assert len({b.block_index for b in blocks}) == len(blocks)

    # 两个相同段落 + 两个 hr 各自共享同一 block_id，不得抛异常。
    block_ids = [b.block_id for b in blocks]
    assert block_ids.count(block_ids[1]) == 2
    assert block_ids.count(block_ids[3]) == 2

    # get_version_block 取第一条，不得 MultipleResultsFound。
    for b in blocks:
        fetched = await artifact_repo.get_version_block(version.id, b.block_id)
        assert fetched is not None
        assert fetched.block_id == b.block_id