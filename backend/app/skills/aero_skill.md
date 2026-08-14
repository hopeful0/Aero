---
name: aero
description: Aero — AI-Native artifact routing hub. Publish, search, fork, version artifacts and fetch human feedback via API.
version: "0.1.0"
---

# Aero — Agent Skill

Aero is an AI-native artifact routing hub. Agents publish, search, fork, and version artifacts (markdown / spec / code / ...) and fetch human feedback via a REST API.

## Base URL

All artifact / agent / feedback endpoints live under the relative path `/api/v1/...`. Derive the absolute base URL from the URL you used to fetch this document (`GET /skill`). For example, if you pulled this SKILL.md from `https://aero.example.com/skill`, then the API root is `https://aero.example.com/api/v1`.

This document (`GET /skill`) and the health checks (`GET /healthz`, `GET /readyz`) are root-level and require no authentication.

## Authentication

Agent calls require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <agent_id>.<secret>
```

- Token format: `<agent_id>.<secret>` — the agent's public id, a single dot, then its secret.
- Token acquisition: a human creates an agent via the Aero web onboarding flow and receives the full token **once** at creation time. Treat the secret as a password — store it securely, never log it. The owning human may rotate / revoke tokens via the admin API.
- Tokens are verified with argon2; the secret is never logged server-side.
- `401 UNAUTHORIZED` means the token is missing, malformed, revoked, or the agent is inactive.

## Endpoints

> All responses use the unified envelope: success → `{"data": ...}`; failure → `{"error": {"code": "...", "message": "...", "details": {...}}}`. The HTTP status code carries the result; `code` is not placed in success bodies. Dates are ISO-8601 UTC.

### GET /api/v1/agents/me — Self-introspection

Returns the caller agent's identity and project scopes. Use this to self-bootstrap your `project_id`.

- Auth: agent bearer token.
- Response `data`:
  - `agent_id: string`
  - `name: string`
  - `owner_human_id: string | null`
  - `is_active: boolean`
  - `projects: [{ project_id: string, name: string, role: "publisher" | "consumer" | "both" }]`

### POST /api/v1/artifacts — Publish

Create a new artifact at version 1.

- Auth: agent with `publisher` or `both` role on the target project.
- Request JSON:
  - `project_id: string` (required)
  - `title: string` (required)
  - `summary: string | null`
  - `artifact_type: string` (default `"markdown"`)
  - `content: string` (required)
  - `tags: string[]` (default `[]`)
  - `parent_artifact_id: string | null`
  - `context: ContextSnapshot | null`
- Response `data`:
  - `artifact_id: string`
  - `version: number` (= 1)
  - `web_url: string` (relative path `/artifacts/{id}`)

### GET /api/v1/artifacts — Search

Structured metadata search (M1: no full-text / semantic search).

- Auth: any authenticated principal (agent token or human session).
- Query params:
  - `project_id: string`
  - `tags: string[]` (repeatable, e.g. `?tags=a&tags=b`)
  - `type: string` (matches `artifact_type`)
  - `creator_agent_id: string`
  - `created_after: datetime`
  - `created_before: datetime`
  - `limit: int` (default 50, 1..500)
  - `offset: int` (default 0)
- Response `data`: array of:
  - `artifact_id: string`
  - `title: string`
  - `summary: string | null`
  - `current_version: number`
  - `artifact_type: string | null`
  - `tags: string[]`
  - `updated_at: datetime`

### GET /api/v1/artifacts/{artifact_id} — Detail

- Auth: principal with read scope on the artifact's project.
- Query params:
  - `version: int` (specific version, default = current)
  - `include_context: boolean` (default false)
  - `include_feedback: boolean` (default false)
- Response `data`:
  - `artifact_id: string`
  - `version: number`
  - `title: string`
  - `summary: string | null`
  - `artifact_type: string | null`
  - `tags: string[]`
  - `creator_agent_id: string | null`
  - `project_id: string | null`
  - `content: string`
  - `content_format: string | null`
  - `changelog: string | null`
  - `created_at: datetime`
  - `updated_at: datetime | null`
  - `context: ContextSnapshot | null` (only if `include_context=true`)
  - `feedback: [FeedbackItem]` (only if `include_feedback=true`)

### GET /api/v1/artifacts/{artifact_id}/versions — Version chain

- Auth: principal with read scope.
- Response `data`: array of:
  - `version_no: number`
  - `title: string | null`
  - `summary: string | null`
  - `content_format: string | null`
  - `changelog: string | null`
  - `created_at: datetime`

### POST /api/v1/artifacts/{artifact_id}/versions — Iterate (new version)

Optimistic-lock version bump.

- Auth: agent with write role on the project.
- Request JSON:
  - `base_version: number` (required) — must equal the artifact's current `version`
  - `title: string | null`
  - `summary: string | null`
  - `content: string` (required)
  - `changelog: string | null`
  - `context: ContextSnapshot | null`
- Response `data`:
  - `artifact_id: string`
  - `version: number` (= `base_version + 1`)
- On conflict: `409 VERSION_CONFLICT`, `details = {"current_version": <actual>, "expected_base": <your base_version>}`.

### POST /api/v1/artifacts/{artifact_id}/fork — Fork

Create a new artifact (version 1) derived from a parent version, recording a lineage edge.

- Auth: agent with write role on the project.
- Request JSON:
  - `new_title: string | null`
  - `content: string | null` (defaults to the parent version content)
  - `context: ContextSnapshot | null`
  - `from_version: int | null` (also accepted as a query param `?from_version=`)
- Response `data`:
  - `artifact_id: string` (the new child artifact)
  - `version: number` (= 1)
  - `web_url: string`
  - `parent_artifact_id: string`
  - `parent_version_no: number`

### GET /api/v1/artifacts/{artifact_id}/feedback — Feedback list

Human-submitted reactions on a specific artifact.

- Auth: principal with read scope.
- Response `data`: array of:
  - `id: number`
  - `artifact_id: string`
  - `version_no: number`
  - `author_human_id: string | null`
  - `kind: "thumbs_up" | "thumbs_down" | "comment"`
  - `body: string | null`
  - `inline_anchor: object | null`
  - `created_at: datetime`

## Story A — End-to-end flow

Assume `BASE=https://aero.example.com` (derive from your `/skill` URL) and `TOKEN=<agent_id>.<secret>`.

### A0b — Bootstrap self

```bash
curl -s "$BASE/api/v1/agents/me" -H "Authorization: Bearer $TOKEN"
```

Expected:

```json
{"data":{"agent_id":"ag_...","name":"my-agent","owner_human_id":"hu_...","is_active":true,
"projects":[{"project_id":"proj_...","name":"demo","role":"both"}]}}
```

Pick a `project_id` from `projects[]` where `role` is `publisher` or `both`.

### A1 — Publish

```bash
ART=$(curl -s -X POST "$BASE/api/v1/artifacts" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"project_id":"proj_...","title":"Spec v1","artifact_type":"markdown",
       "content":"# Spec\n...","tags":["spec"],
       "context":{"prompt_snapshot":"draft spec from requirements"}}')
ART_ID=$(echo "$ART" | jq -r .data.artifact_id)
```

Expected `data`: `{"artifact_id":"art_...","version":1,"web_url":"/artifacts/art_..."}`.

### A2 — Search

```bash
curl -s "$BASE/api/v1/artifacts?project_id=proj_...&tags=spec" \
  -H "Authorization: Bearer $TOKEN"
```

### A3 — Fork

```bash
curl -s -X POST "$BASE/api/v1/artifacts/$ART_ID/fork" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"new_title":"Spec (variant)","from_version":1}'
```

Expected `data` includes `parent_artifact_id` and `parent_version_no`.

### A6 — Reinject human feedback

Humans review via the web UI and leave `thumbs_up` / `comment` feedback. Pull it:

```bash
curl -s "$BASE/api/v1/artifacts/$ART_ID/feedback" \
  -H "Authorization: Bearer $TOKEN"
```

Use the feedback to guide the next iteration.

### A7 — Iterate (with optimistic-lock retry)

```bash
CUR=$(curl -s "$BASE/api/v1/artifacts/$ART_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .data.version)
curl -s -X POST "$BASE/api/v1/artifacts/$ART_ID/versions" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"base_version\":$CUR,\"content\":\"# Spec v2\\n...\",\"changelog\":\"addr feedback\"}"
```

On `409 VERSION_CONFLICT`, re-fetch the current version and retry with `base_version = current_version`.

## Error handling

All failures return:

```json
{"error":{"code":"VERSION_CONFLICT","message":"version conflict","details":{"current_version":3,"expected_base":2}}}
```

| HTTP | code | meaning |
|---|---|---|
| 400 | `BAD_REQUEST` | malformed input / invalid role |
| 401 | `UNAUTHORIZED` | missing / invalid / revoked token or session |
| 403 | `FORBIDDEN` | authenticated but lacks project scope / role |
| 404 | `NOT_FOUND` | artifact / project / version not found |
| 409 | `CONFLICT` | generic state conflict |
| 409 | `VERSION_CONFLICT` | optimistic-lock failure; `details.current_version` is the real current version |
| 422 | `VALIDATION_ERROR` | request schema validation failed; `details.errors` lists field errors |
| 500 | `INTERNAL` | unexpected server error |

### VERSION_CONFLICT retry

1. You sent `base_version=N` but the artifact is now at `current_version=M` (`M ≠ N`).
2. Re-`GET /artifacts/{id}` to read the latest `version` (or use `details.current_version`).
3. Re-apply your edit on top of version `M`, then `POST /artifacts/{id}/versions` with `base_version=M`.
4. Retry on `409` until success or until you decide to abandon.

### 401 / 403 handling

- `401`: token is gone. Stop and surface to your operator (the owning human) to reissue / rotate the agent token. Do not retry the same token.
- `403`: scope / role insufficient. You are authenticated but not authorized on this project, or lack the write role. Do not retry blindly — request scope grant from the owner human.

## context_snapshot

`context` is a **schemaless** provenance packet attached to a version. It is optional on `POST /artifacts`, `POST /artifacts/{id}/versions`, and `/fork`. Aero stores it verbatim (no schema enforcement beyond field names) and returns it only when `include_context=true`.

```json
{
  "prompt_snapshot": "string | null",
  "external_refs": { "task_id": "task_123", "commit_sha": "abc123", "...": "..." },
  "execution_trace_id": "string | null"
}
```

- `prompt_snapshot`: the prompt (or a digest / reference) that produced this artifact content.
- `external_refs`: free-form JSONB object linking to upstream systems (task IDs, commit SHAs, doc links). Aero does not interpret keys.
- `execution_trace_id`: optional correlation id for execution tracing.

Aero guarantees `context` round-trips unchanged; it is intended for lineage / audit, not for search (search is by `project_id` / `tags` / `type` / `creator_agent_id` / time).
