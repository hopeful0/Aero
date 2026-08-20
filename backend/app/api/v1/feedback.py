from fastapi import APIRouter, Query

from app.api.deps import CurrentHuman, CurrentPrincipal, FeedbackSvc
from app.core.response import ok
from app.schemas.feedback import FeedbackCreate
from app.services.auth_service import Principal

router = APIRouter(tags=["feedback"])


@router.post("/artifacts/{artifact_id}/feedback", status_code=201)
async def create_feedback(
    artifact_id: str,
    body: FeedbackCreate,
    human: CurrentHuman,
    service: FeedbackSvc,
):
    principal = Principal(kind="human", human=human)
    result = await service.create_feedback(
        principal=principal,
        artifact_id=artifact_id,
        kind=body.kind,
        body=body.body,
        block_id=body.block_id,
        version_no=body.version_no,
        selector=body.selector,
    )
    return ok(result)


@router.get("/artifacts/{artifact_id}/feedback")
async def list_feedback(
    artifact_id: str,
    principal: CurrentPrincipal,
    service: FeedbackSvc,
    version: int | None = Query(default=None, ge=1),
):
    results = await service.list_feedback(
        principal, artifact_id, viewing_version=version
    )
    return ok(results)
