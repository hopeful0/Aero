from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ApiResponse


class FeedbackCreate(BaseModel):
    kind: Literal["thumbs_up", "thumbs_down", "comment"]
    body: str | None = None
    inline_anchor: dict | None = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artifact_id: str
    version_no: int
    author_human_id: str
    kind: str
    body: str | None = None
    inline_anchor: dict | None = None
    created_at: datetime


FeedbackListResponse = ApiResponse[list[FeedbackResponse]]
