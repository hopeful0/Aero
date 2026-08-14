
from app.models.audit import AuditLog
from app.repos.base import BaseRepo


class AuditRepo(BaseRepo):
    async def write_audit_log(
        self,
        event: str,
        actor_agent_id: int | None = None,
        on_behalf_of_human_id: int | None = None,
        actor_human_id: int | None = None,
        target_artifact_id: int | None = None,
        target_version_no: int | None = None,
        payload: dict | None = None,
    ) -> AuditLog:
        log = AuditLog(
            event=event,
            actor_agent_id=actor_agent_id,
            on_behalf_of_human_id=on_behalf_of_human_id,
            actor_human_id=actor_human_id,
            target_artifact_id=target_artifact_id,
            target_version_no=target_version_no,
            payload=payload,
        )
        self.session.add(log)
        await self.session.flush()
        return log
