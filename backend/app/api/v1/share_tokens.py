from fastapi import APIRouter

from app.api.deps import CurrentPrincipal, ShareTokenSvc
from app.core.response import ok

router = APIRouter(tags=["share-tokens"])


@router.post("/artifacts/{artifact_id}/share-tokens")
async def create_share_token(artifact_id: str, principal: CurrentPrincipal, service: ShareTokenSvc):
    data = await service.create_share_token(principal, artifact_id)
    return ok(data)


@router.delete("/artifacts/{artifact_id}/share-tokens/{share_token_id}")
async def revoke_share_token(
    artifact_id: str,
    share_token_id: str,
    principal: CurrentPrincipal,
    service: ShareTokenSvc,
):
    data = await service.revoke_share_token(principal, artifact_id, share_token_id)
    return ok(data)


@router.get("/artifacts/{artifact_id}/share/{token}")
async def read_share_token(artifact_id: str, token: str, service: ShareTokenSvc):
    data = await service.read_share_token(token, artifact_id)
    return ok(data)
