from fastapi import APIRouter

from app.api.deps import CurrentHuman, LineageSvc
from app.core.response import ok
from app.services.auth_service import Principal

router = APIRouter(tags=["lineage"])


@router.get("/artifacts/{artifact_id}/lineage")
async def get_lineage(
    artifact_id: str, human: CurrentHuman, service: LineageSvc
):
    principal = Principal(kind="human", human=human)
    chain = await service.get_lineage(principal, artifact_id)
    return ok(chain)
