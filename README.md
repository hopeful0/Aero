# Aero — Agent 协作产物路由中枢

AI-Native 团队产物沉淀与知识协同系统：Agent 通过 API 发布/检索/派生产物，人类通过 Web UI 评审与反馈，产物可溯源演进。

> 需求与设计文档由 `project-lead` 子代理维护为本地工作文件（不纳入 VCS），不在此仓库内。

## 技术栈

- 后端：Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) / PostgreSQL 16 / Alembic
- 前端：Vite + React 18 + TypeScript
- 部署：单机 Docker Compose（nginx + backend + postgres + redis）

## 开发命令

### 后端（`backend/`）

```bash
uv sync                          # 安装依赖
uv run ruff check app            # lint
uv run ruff format app           # 格式化
uv run pytest                    # 测试
uv run uvicorn app.main:app --reload  # 本地运行
uv run alembic upgrade head      # 迁移
```

### 前端（`frontend/`）

```bash
npm install
npm run lint                     # eslint
npm run typecheck                # tsc --noEmit
npm run build
npm run dev
```

### 集成

```bash
docker compose -f deploy/docker-compose.yml up --build
```

## 约定

- 提交前必须跑 `ruff check`（后端）与 `npm run typecheck`（前端）。
- 业务逻辑只写在 `app/services/`，API 层不写业务规则，Repo 层只做数据访问。
- 统一响应：`{"data": ...}`；错误：`{"error": {"code","message","details"}}`，依赖 HTTP 状态码。
- 写操作落 `audit_log`，agent 写操作记 `actor_agent_id` + `on_behalf_of_human_id`。
- 不加注释，除非必要。

## License

Apache License 2.0。详见 [LICENSE](./LICENSE)。
