from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreateRequest(BaseModel):
    name: str


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: str
    name: str
    created_at: datetime
