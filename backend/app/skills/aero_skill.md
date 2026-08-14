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
  - `visibility: "private" | "public"` (default `"private"`)
- Response `data`:
  - `artifact_id: string`
  - `version: number` (= 1)
  - `visibility: "private" | "public"`
  - `web_url: string` (relative path `/artifacts/{id}`)

### GET /api/v1/artifacts — Search

Structured metadata search (M1: no full-text / semantic search).

- Auth: optional. Anonymous (no header) → only `public` artifacts (cross-project). Authenticated (agent token or human session) → scoped (project scope, incl. `private`) ∪ all `public`.
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
  - `visibility: "private" | "public"`

### GET /api/v1/artifacts/{artifact_id} — Detail

- Auth: optional. `public` → anyone (anonymous ok) reads the full body + content + context + versions. `private` → principal with read scope; anonymous → `404` (existence hidden).
- Query params:
  - `version: int` (specific version, default = current)
  - `include_context: boolean` (default false)
  - `include_feedback: boolean` (default false; ignored for anonymous — feedback is never returned without auth)
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
  - `visibility: "private" | "public"`
  - `context: ContextSnapshot | null` (only if `include_context=true`)
  - `feedback: [FeedbackItem]` (only if `include_feedback=true` and authenticated)

### PATCH /api/v1/artifacts/{artifact_id} — Change visibility

Toggle an artifact's visibility. This is a **human governance operation** (not an agent write).

- Auth: **human session cookie** (`aero_session`), not an agent bearer token. The human must have write scope (`publisher` or `both`) on the artifact's project.
- Request JSON:
  - `visibility: "private" | "public"` (required)
- Response `data`:
  - `artifact_id: string`
  - `visibility: "private" | "public"`
- Errors:
  - `401 UNAUTHORIZED` — no / invalid / expired session cookie.
  - `403 FORBIDDEN` — authenticated human lacks write scope on the project.
  - `404 NOT_FOUND` — artifact does not exist (or is archived).
  - `422 VALIDATION_ERROR` — `visibility` missing or not a valid enum value.
- Audited as `visibility_change` (`actor_human_id`, `target_artifact_id`, `payload={"visibility": ...}`).

### GET /api/v1/artifacts/{artifact_id}/versions — Version chain

- Auth: optional. `public` → anonymous ok. `private` → read scope; anonymous → `404`.
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

- Auth: required (agent token or human session); read scope on the artifact's project. Always `401` for anonymous — even on `public` artifacts (feedback exposes reviewer identity / comments).
- Response `data`: array of:
  - `id: number`
  - `artifact_id: string`
  - `version_no: number`
  - `author_human_id: string | null`
  - `kind: "thumbs_up" | "thumbs_down" | "comment"`
  - `body: string | null`
  - `inline_anchor: object | null`
  - `created_at: datetime`

## Visibility

Each artifact carries a `visibility` flag controlling read access.

- `private` (default): visible only to principals with read scope on the artifact's project (agent token or human session). Anonymous access returns `404 NOT_FOUND` — existence is not leaked.
- `public`: **fully anonymous-readable**. Anyone — with no `Authorization` header and no session cookie — may read the artifact body, content, context, and version chain. Aero does not distinguish project scope or introduce org / RBAC for public reads.

Anonymous read surface (`public` artifact):

- `GET /artifacts` (no header) → only `public` artifacts (cross-project, no `private`).
- `GET /artifacts/{id}` (no header) → full body: metadata + content + changelog + content_format + context (when `include_context=true`) + versions. `include_feedback` is ignored for anonymous (feedback is never returned without auth).
- `GET /artifacts/{id}/versions` (no header) → version chain.

Authenticated read surface: scoped (principal's project scope, including `private`) ∪ all `public` (cross-project).

Still requires auth (even for `public` artifacts):

- `GET /artifacts/{id}/lineage` — lineage may reference `private` ancestors (title / ID / version counts); anonymous exposure would leak private metadata → `401` without a header.
- `GET /artifacts/{id}/feedback` — feedback carries `author_human_id` and reviewer comments; anonymous exposure leaks reviewer privacy → `401` without a header.

Write operations (`POST /artifacts`, `POST /artifacts/{id}/versions`, `/fork`, `POST /artifacts/{id}/feedback`, `PATCH /artifacts/{id}`) still require auth + write scope — `public` only relaxes reads, never writes.

> **Security note**: a `public` artifact's `context.prompt_snapshot` (the full generation prompt) and `context.external_refs` (task IDs, trace IDs, commit SHAs) are exposed to the public internet. Before setting `visibility=public`, review the context packet for sensitive material.

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

### A8 — Share publicly (anonymous read)

Publish a `public` artifact directly, or flip an existing one to public via the human-governed PATCH:

```bash
# Option A: publish public from the start (agent)
curl -s -X POST "$BASE/api/v1/artifacts" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"project_id":"proj_...","title":"Public Spec","content":"# Public\n...",
       "tags":["spec"],"visibility":"public"}'
```

```bash
# Option B: flip an existing artifact to public (human, session cookie)
curl -s -X PATCH "$BASE/api/v1/artifacts/$ART_ID" \
  -b "aero_session=$HUMAN_SESSION" -H "Content-Type: application/json" \
  -d '{"visibility":"public"}'
```

`HUMAN_SESSION` is the `aero_session` cookie obtained from the web login flow (`POST /api/v1/auth/login` with email + password).

Expected `data`: `{"artifact_id":"art_...","visibility":"public"}`.

Verify anonymous (no header, no cookie) can read it:

```bash
curl -s "$BASE/api/v1/artifacts/$ART_ID"
```

Expected `data` includes the full body (`content`, `context` with `include_context=true`) and `visibility:"public"`.

Anonymous search returns only public artifacts:

```bash
curl -s "$BASE/api/v1/artifacts?tags=spec"
```

Anonymous access to a `private` artifact returns `404 NOT_FOUND` (existence hidden). `lineage` / `feedback` on a `public` artifact still return `401` without auth.

## Error handling

All failures return:

```json
{"error":{"code":"VERSION_CONFLICT","message":"version conflict","details":{"current_version":3,"expected_base":2}}}
```

| HTTP | code | meaning |
|---|---|---|
| 400 | `BAD_REQUEST` | malformed input / invalid role |
| 401 | `UNAUTHORIZED` | missing / invalid / revoked token or session; anonymous call to a forced-auth endpoint (`lineage`, `feedback`, `PATCH /artifacts/{id}`) |
| 403 | `FORBIDDEN` | authenticated but lacks project scope / role; human without write scope on `PATCH /artifacts/{id}` |
| 404 | `NOT_FOUND` | artifact / project / version not found; anonymous access to a `private` artifact (existence hidden) |
| 409 | `CONFLICT` | generic state conflict |
| 409 | `VERSION_CONFLICT` | optimistic-lock failure; `details.current_version` is the real current version |
| 422 | `VALIDATION_ERROR` | request schema validation failed; `details.errors` lists field errors (e.g. invalid `visibility` value) |
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
