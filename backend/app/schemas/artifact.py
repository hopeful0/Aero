from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ApiResponse


class ContextSnapshot(BaseModel):
    prompt_snapshot: str | None = None
    external_refs: dict | None = None
    execution_trace_id: str | None = None


class PublishRequest(BaseModel):
    project_id: str
    title: str
    summary: str | None = None
    artifact_type: str = "markdown"
    content: str
    tags: list[str] = Field(default_factory=list)
    parent_artifact_id: str | None = None
    context: ContextSnapshot | None = None
    visibility: Literal["private", "public"] = "private"


class NewVersionRequest(BaseModel):
    base_version: int
    title: str | None = None
    summary: str | None = None
    content: str
    changelog: str | None = None
    context: ContextSnapshot | None = None


class ForkRequest(BaseModel):
    new_title: str | None = None
    content: str | None = None
    context: ContextSnapshot | None = None
    from_version: int | None = None


class VisibilityUpdateRequest(BaseModel):
    visibility: Literal["private", "public"]


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: int
    title: str
    summary: str | None = None
    artifact_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    creator_agent_id: str | None = None
    project_id: str
    content: str | None = None
    content_format: str | None = None
    changelog: str | None = None
    context: ContextSnapshot | None = None
    created_at: datetime
    updated_at: datetime | None = None
    visibility: str = "private"


class ArtifactListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    artifact_id: str
    title: str
    summary: str | None = None
    current_version: int
    artifact_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    updated_at: datetime
    visibility: str = "private"


class SearchParams(BaseModel):
    project_id: str | None = None
    tags: list[str] | None = None
    type: str | None = None
    creator_agent_id: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    limit: int = 50
    offset: int = 0


class VersionBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    block_id: str
    block_path: str
    block_index: int
    block_text: str
    content_preview: str


PublishResponse = ApiResponse[ArtifactResponse]
ArtifactListResponse = ApiResponse[list[ArtifactListItem]]
VersionBlockListResponse = ApiResponse[list[VersionBlockResponse]]
