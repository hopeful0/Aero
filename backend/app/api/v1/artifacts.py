from datetime import datetime

from fastapi import APIRouter, Query

from app.api.deps import ArtifactSvc, CurrentAgent, CurrentPrincipal
from app.core.response import ok
from app.schemas.artifact import ForkRequest, NewVersionRequest, PublishRequest, SearchParams

router = APIRouter(tags=["artifacts"])


def _parse_context(body):
    if body.context is None:
        return None
    return body.context.model_dump()


@router.post("/artifacts", status_code=201)
async def publish(body: PublishRequest, agent: CurrentAgent, service: ArtifactSvc):
    result = await service.publish(
        agent=agent,
        project_id=body.project_id,
        title=body.title,
        summary=body.summary,
        artifact_type=body.artifact_type,
        content=body.content,
        tags=body.tags,
        context=_parse_context(body),
    )
    return ok(result)


@router.get("/artifacts")
async def search(
    principal: CurrentPrincipal,
    service: ArtifactSvc,
    project_id: str | None = Query(default=None),
    tags: list[str] = Query(default=[]),
    artifact_type: str | None = Query(default=None, alias="type"),
    creator_agent_id: str | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    params = SearchParams(
        project_id=project_id,
        tags=tags or None,
        type=artifact_type,
        creator_agent_id=creator_agent_id,
        created_after=created_after,
        created_before=created_before,
        limit=limit,
        offset=offset,
    )
    results = await service.search(principal, params)
    return ok(results)


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    principal: CurrentPrincipal,
    service: ArtifactSvc,
    version: int | None = Query(default=None, ge=1),
    include_context: bool = Query(default=False),
    include_feedback: bool = Query(default=False),
):
    data = await service.get_artifact(
        principal=principal,
        artifact_id=artifact_id,
        version=version,
        include_context=include_context,
        include_feedback=include_feedback,
    )
    return ok(data)


@router.get("/artifacts/{artifact_id}/versions")
async def list_versions(artifact_id: str, principal: CurrentPrincipal, service: ArtifactSvc):
    versions = await service.list_versions(principal, artifact_id)
    return ok(versions)


@router.post("/artifacts/{artifact_id}/versions")
async def add_version(
    artifact_id: str,
    body: NewVersionRequest,
    agent: CurrentAgent,
    service: ArtifactSvc,
):
    result = await service.add_version(
        agent=agent,
        artifact_id=artifact_id,
        base_version=body.base_version,
        title=body.title,
        summary=body.summary,
        content=body.content,
        changelog=body.changelog,
        context=_parse_context(body),
    )
    return ok(result)


@router.post("/artifacts/{artifact_id}/fork", status_code=201)
async def fork(
    artifact_id: str,
    body: ForkRequest,
    agent: CurrentAgent,
    service: ArtifactSvc,
    from_version: int | None = Query(default=None, ge=1),
):
    effective_from = from_version if from_version is not None else body.from_version
    result = await service.fork(
        agent=agent,
        artifact_id=artifact_id,
        from_version=effective_from,
        new_title=body.new_title,
        content=body.content,
        context=_parse_context(body),
    )
    return ok(result)
