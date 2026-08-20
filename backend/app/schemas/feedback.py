from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ApiResponse


class FeedbackCreate(BaseModel):
    kind: Literal["thumbs_up", "thumbs_down", "comment"]
    body: str | None = None
    # 行内评论锚点：block_id 命中 version_no 对应版本 block map；selector 为前端 DOM 选择器。
    block_id: str | None = None
    version_no: int | None = None
    selector: str | None = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artifact_id: str
    version_no: int
    author_human_id: str
    kind: str
    body: str | None = None
    inline_anchor: dict | None = None
    # 仅带 block_id 的行内评论有 migration_status（exact/fuzzy/stale）；版本级评论为 null。
    migration_status: str | None = None
    created_at: datetime


FeedbackListResponse = ApiResponse[list[FeedbackResponse]]
