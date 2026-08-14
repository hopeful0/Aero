# AGENTS.md — 给 opencode 子 agent 与开发者的工作指南

需求与设计文档是唯一事实来源，由 `project-lead` 子代理维护为本地工作文件（不纳入 VCS），不在此仓库内；实现前向其索取相关章节。

## 必跑命令（提交前）

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

未跑 lint/typecheck 的改动不得提交。若命令缺失，先问用户或写入此处。

## 架构约束

- 分层：API (`app/api/`) → Service (`app/services/`) → Repo (`app/repos/`) → Models (`app/models/`)。
- 统一响应包装：成功 `{"data": ...}`；失败 `{"error": {"code": "...", "message": "...", "details": {...}}}`，靠 HTTP status 码表达，body 不放 `code` 字段。
- 版本递增乐观锁：`UPDATE artifact SET current_version=N WHERE id=? AND current_version=N-1`，affected=0 返回 409 `VERSION_CONFLICT`。
- Agent 强制 owner 绑定：`agent.owner_human_id NOT NULL`；`agent_project_scope` 授予时校验 `⊆ owner.scope`；写操作落 `audit_log` 记 `actor_agent_id`+`on_behalf_of_human_id`。
- 元数据检索（MVP）：结构化过滤（project/tags/type/creator_agent/time），非全文/语义。全文+语义检索为可选扩展，不在 M1-M3 路线内。
- 上下文 `context_snapshot` 为 schemaless 溯源元数据包（`prompt_snapshot` + `external_refs JSONB`），不绑定任何协议。

## 实现节奏

M1（P0）目标：Story A 闭环跑通 + 埋点就绪。验收 = 闭环可观测。
