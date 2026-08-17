# AGENTS.md — Aero 代理与开发者协作指南

本文件是跨工具共享的唯一工作指南。`CLAUDE.md` 以符号链接指向此处，勿分散维护——改动只改本文件。

## 提交前必跑

后端（工作目录 `backend/`）：
```bash
uv run ruff check app
uv run pytest
```

前端（工作目录 `frontend/`）：
```bash
npm run lint
npm run typecheck
```

未跑 lint / typecheck / test 的改动不得提交。完整开发命令（`uv sync`、`uv run alembic upgrade head`、`npm run dev` 等）见 [README.md](./README.md)。

## 架构与约定

- **分层**：API (`app/api/`) → Service (`app/services/`) → Repo (`app/repos/`) → Models (`app/models/`)，Schema 在 `app/schemas/`。业务逻辑只写在 `app/services/`；API 层不写业务规则，Repo 层只做数据访问。
- **统一响应包装**：成功 `{"data": ...}`；失败 `{"error": {"code": "...", "message": "...", "details": {...}}}`，靠 HTTP status 码表达，body 不放 `code` 字段。
- **版本递增乐观锁**：`UPDATE artifact SET current_version=N WHERE id=? AND current_version=N-1`，affected=0 返回 409 `VERSION_CONFLICT`。
- **Agent 强制 owner 绑定**：`agent.owner_human_id NOT NULL`；`agent_project_scope` 授予时校验 `⊆ owner.scope`；写操作落 `audit_log` 记 `actor_agent_id` + `on_behalf_of_human_id`。
- **元数据检索**：当前为结构化过滤（project / tags / type / creator_agent / time），非全文/语义；全文 + 语义检索为可选扩展，暂不在范围内。
- **上下文快照**：`context_snapshot` 为 schemaless 溯源元数据包（`prompt_snapshot` + `external_refs JSONB`），不绑定任何协议。
- **注释**：不加注释，除非确有必要；必要时解释「为什么」而非「是什么」。
