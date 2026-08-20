from pydantic import BaseModel, EmailStr


class HumanRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class HumanResponse(BaseModel):
    human_id: str
    name: str | None = None
    email: str | None = None


class LoginResponse(BaseModel):
    human_id: str
    name: str | None = None


class AgentCreateRequest(BaseModel):
    name: str
    owner_human_id: str
    project_id: str
    role: str = "both"


class AgentResponse(BaseModel):
    agent_id: str
    name: str | None = None
    owner_human_id: str
    token: str


class AgentScopeRequest(BaseModel):
    project_id: str
    role: str
