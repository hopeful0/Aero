from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, ConflictError, ForbiddenError
from app.core.security import generate_token_secret, hash_password, hash_token
from app.models.agent import Agent
from app.models.project import HumanUser, Project
from app.repos.agent import AgentRepo
from app.repos.audit import AuditRepo
from app.repos.human import HumanRepo
from app.repos.project import ProjectRepo
from app.services.auth_service import WRITE_ROLES

VALID_AGENT_ROLES = {"publisher", "consumer", "both"}


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.human_repo = HumanRepo(session)
        self.agent_repo = AgentRepo(session)
        self.project_repo = ProjectRepo(session)
        self.audit_repo = AuditRepo(session)

    async def list_agents_for_human(self, human: HumanUser) -> list[dict]:
        """Return all agents visible to a human (owned or sharing a project
        scope) with their project scopes and the human's own role per project."""
        agents = await self.agent_repo.list_agents_for_human(human.id)
        return [await self._with_scopes(human, agent) for agent in agents]

    async def _serialize_agent(self, agent: Agent) -> dict:
        owner = await self.human_repo.get_by_id(agent.owner_human_id)
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "owner_human_id": owner.human_id if owner is not None else agent.owner_human_id,
            "is_active": agent.is_active,
        }

    async def add_agent_scope(
        self, human: HumanUser, agent_id: str, project_id: str, role: str
    ) -> dict:
        if role not in VALID_AGENT_ROLES:
            raise BadRequestError("invalid role", {"role": role})

        agent = await self.agent_repo.get_by_agent_id(agent_id)
        if agent is None:
            raise BadRequestError("agent not found", {"agent_id": agent_id})

        project = await self.project_repo.get_by_project_id(project_id)
        if project is None:
            raise BadRequestError("project not found", {"project_id": project_id})

        actor_scope = await self.project_repo.get_human_scope_by_pk(
            human.id, project.id
        )
        if actor_scope is None or actor_scope.role not in WRITE_ROLES:
            raise ForbiddenError(
                "actor lacks write access to project",
                {"project_id": project_id},
            )

        owner = await self.human_repo.get_by_id(agent.owner_human_id)
        if owner is None:
            raise BadRequestError(
                "agent owner not found",
                {"owner_human_id": agent.owner_human_id},
            )
        owner_scope = await self.project_repo.get_human_scope_by_pk(
            owner.id, project.id
        )
        if owner_scope is None:
            raise BadRequestError(
                "owner lacks scope on project; agent scope must be subset of owner",
                {"owner_human_id": owner.human_id, "project_id": project_id},
            )

        scope = await self.agent_repo.get_project_scope_by_pk(agent.id, project.id)
        if scope is None:
            await self.agent_repo.grant_agent_scope(agent.id, project.id, role=role)
        else:
            scope.role = role

        await self.audit_repo.write_audit_log(
            event="agent_scope_grant",
            actor_human_id=human.id,
            payload={
                "agent_id": agent_id,
                "project_id": project_id,
                "role": role,
            },
        )
        await self.session.commit()
        return await self._with_scopes(human, agent)

    async def revoke_agent_scope(
        self, human: HumanUser, agent_id: str, project_id: str
    ) -> dict:
        agent = await self.agent_repo.get_by_agent_id(agent_id)
        if agent is None:
            raise BadRequestError("agent not found", {"agent_id": agent_id})
        project = await self.project_repo.get_by_project_id(project_id)
        if project is None:
            raise BadRequestError("project not found", {"project_id": project_id})

        actor_scope = await self.project_repo.get_human_scope_by_pk(
            human.id, project.id
        )
        if actor_scope is None or actor_scope.role not in WRITE_ROLES:
            raise ForbiddenError(
                "actor lacks write access to project",
                {"project_id": project_id},
            )

        deleted = await self.agent_repo.delete_agent_scope(agent.id, project.id)
        if deleted:
            await self.audit_repo.write_audit_log(
                event="agent_scope_revoke",
                actor_human_id=human.id,
                payload={"agent_id": agent_id, "project_id": project_id},
            )
            await self.session.commit()
        return await self._with_scopes(human, agent)

    async def _with_scopes(self, human: HumanUser, agent: Agent) -> dict:
        """Serialize one agent plus its project scopes with the actor's role
        annotated per project (null when the actor has no scope there)."""
        scopes = await self.agent_repo.list_agent_scopes(agent.id)
        for scope in scopes:
            project = await self.project_repo.get_by_project_id(scope["project_id"])
            if project is None:
                scope["current_human_role"] = None
                continue
            human_scope = await self.project_repo.get_human_scope_by_pk(
                human.id, project.id
            )
            scope["current_human_role"] = (
                human_scope.role if human_scope is not None else None
            )
        data = await self._serialize_agent(agent)
        data["projects"] = scopes
        return data

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

    async def get_agent_self(self, agent: Agent) -> dict:
        owner = await self.human_repo.get_by_id(agent.owner_human_id)
        scopes = await self.agent_repo.list_agent_scopes(agent.id)
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "owner_human_id": owner.human_id if owner is not None else None,
            "is_active": agent.is_active,
            "projects": scopes,
        }

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
