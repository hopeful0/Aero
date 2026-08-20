from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ApiResponse


class ShareTokenCreateResponse(BaseModel):
    share_token_id: str
    token: str
    artifact_id: str
    url: str
    created_at: datetime


class ShareTokenRevokeResponse(BaseModel):
    share_token_id: str
    revoked_at: datetime


class ShareTokenReadResponse(BaseModel):
    artifact_id: str
    version: int
    title: str
    summary: str | None = None
    artifact_type: str | None = None
    tags: list[str] = []
    creator_agent_id: str | None = None
    project_id: str | None = None
    content: str | None = None
    content_format: str | None = None
    changelog: str | None = None
    context: dict | None = None
    created_at: datetime
    updated_at: datetime | None = None
    visibility: str = "private"


ShareTokenCreateResponseApi = ApiResponse[ShareTokenCreateResponse]
ShareTokenRevokeResponseApi = ApiResponse[ShareTokenRevokeResponse]
ShareTokenReadResponseApi = ApiResponse[ShareTokenReadResponse]
