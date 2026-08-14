from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, ConflictError, ForbiddenError
from app.core.security import (
    generate_token_secret,
    hash_password,
    hash_token,
)
from app.models.agent import Agent
from app.models.project import HumanUser, Project
from app.repos.agent import AgentRepo
from app.repos.audit import AuditRepo
from app.repos.human import HumanRepo
from app.repos.project import ProjectRepo

VALID_AGENT_ROLES = {"publisher", "consumer", "both"}


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.human_repo = HumanRepo(session)
        self.agent_repo = AgentRepo(session)
        self.project_repo = ProjectRepo(session)
        self.audit_repo = AuditRepo(session)

    async def register_human(self, name: str, email: str, password: str) -> HumanUser:
        existing = await self.human_repo.get_by_email(email)
        if existing is not None:
            raise ConflictError("email already registered", {"email": email})
        human = await self.human_repo.create_human(
            name=name,
            email=email,
            password_hash=hash_password(password),
        )
        await self.audit_repo.write_audit_log(
            event="human_register",
            actor_human_id=human.id,
            payload={"human_id": human.human_id, "email": email},
        )
        await self.session.commit()
        return human

    async def create_project(self, human: HumanUser, name: str) -> Project:
        project = await self.project_repo.create_project(name=name)
        await self.project_repo.grant_human_scope(human.id, project.id, role="both")
        await self.audit_repo.write_audit_log(
            event="project_create",
            actor_human_id=human.id,
            payload={"project_id": project.project_id, "name": name},
        )
        await self.session.commit()
        return project

    async def list_projects(self, human: HumanUser) -> list[Project]:
        return await self.project_repo.list_projects_for_human(human.id)

    async def create_agent(
        self,
        actor: HumanUser,
        name: str,
        owner_human_id: str,
        project_id: str,
        role: str,
    ) -> tuple[Agent, str]:
        if role not in VALID_AGENT_ROLES:
            raise BadRequestError("invalid role", {"role": role})

        project = await self.project_repo.get_by_project_id(project_id)
        if project is None:
            raise BadRequestError("project not found", {"project_id": project_id})

        actor_scope = await self.project_repo.get_human_scope_by_pk(
            actor.id, project.id
        )
        if actor_scope is None:
            raise ForbiddenError(
                "actor lacks access to project",
                {"project_id": project_id},
            )

        owner = await self.human_repo.get_by_human_id(owner_human_id)
        if owner is None:
            raise BadRequestError(
                "owner human not found",
                {"owner_human_id": owner_human_id},
            )

        owner_scope = await self.project_repo.get_human_scope_by_pk(
            owner.id, project.id
        )
        if owner_scope is None:
            raise BadRequestError(
                "owner lacks scope on project; agent scope must be subset of owner",
                {"owner_human_id": owner_human_id, "project_id": project_id},
            )

        secret = generate_token_secret()
        token_hash = hash_token(secret)
        agent = await self.agent_repo.create_agent(
            name=name,
            token_hash=token_hash,
            owner_human_id=owner.id,
        )
        await self.agent_repo.grant_agent_scope(agent.id, project.id, role=role)

        full_token = f"{agent.agent_id}.{secret}"
        await self.audit_repo.write_audit_log(
            event="agent_token",
            actor_human_id=actor.id,
            payload={
                "agent_id": agent.agent_id,
                "owner_human_id": owner_human_id,
                "project_id": project_id,
                "role": role,
            },
        )
        await self.session.commit()
        return agent, full_token
