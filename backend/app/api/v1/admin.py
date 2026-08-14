from fastapi import APIRouter

from app.api.deps import AdminSvc, CurrentAgent, CurrentHuman
from app.core.response import ok
from app.schemas.auth import AgentCreateRequest, HumanRegisterRequest
from app.schemas.project import ProjectCreateRequest

router = APIRouter(tags=["admin"])


@router.post("/humans", status_code=201)
async def register_human(body: HumanRegisterRequest, admin_service: AdminSvc):
    human = await admin_service.register_human(body.name, body.email, body.password)
    return ok({"human_id": human.human_id, "name": human.name, "email": human.email})


@router.get("/projects")
async def list_projects(human: CurrentHuman, admin_service: AdminSvc):
    projects = await admin_service.list_projects(human)
    return ok(
        [
            {
                "project_id": p.project_id,
                "name": p.name,
                "created_at": p.created_at,
            }
            for p in projects
        ]
    )


@router.post("/projects", status_code=201)
async def create_project(
    body: ProjectCreateRequest, human: CurrentHuman, admin_service: AdminSvc
):
    project = await admin_service.create_project(human, body.name)
    return ok(
        {"project_id": project.project_id, "name": project.name, "created_at": project.created_at}
    )


@router.post("/agents", status_code=201)
async def create_agent(
    body: AgentCreateRequest, human: CurrentHuman, admin_service: AdminSvc
):
    agent, token = await admin_service.create_agent(
        actor=human,
        name=body.name,
        owner_human_id=body.owner_human_id,
        project_id=body.project_id,
        role=body.role,
    )
    return ok(
        {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "owner_human_id": body.owner_human_id,
            "token": token,
        }
    )


@router.get("/agents/me")
async def get_agent_self(agent: CurrentAgent, admin_service: AdminSvc):
    return ok(await admin_service.get_agent_self(agent))
