# FarmCore API — Assistant & Knowledge Track

Normative HTTP contract for the FarmCore POC REST surface owned by the
Assistant / Documents track. This document defines every endpoint, request and
response shape, authorisation rule, error model, and ownership boundary that
other teams may depend on.

Browser UI uses Django pages and HTMX fragments. JSON under `/api/` serves
controlled programmatic operations, assistant tools, map integrations, and
future non-browser clients.

## Document Metadata

| Field | Value |
|---|---|
| Title | FarmCore API — Assistant & Knowledge Track |
| Status | **Accepted** |
| Date | 2026-08-27 |
| Owning team | Assistant / Documents |
| Applies to | FarmCore POC — `documents` and `assistant` Django apps, plus farm-context endpoints in `farms` |
| Companion records | [`ARCHITECTURE.md`](ARCHITECTURE.md), [`EXTENSIBILITY.md`](EXTENSIBILITY.md), [`PLAN.md`](PLAN.md) |
| OpenAPI source of truth | DRF serializers in the FarmCore repo; generated schema at `docs/openapi/` |
| URL versioning | None in the POC. OpenAPI document carries a release version label. |

---

## 1. Conventions

### 1.1 Base URL and content types

| Item | Value |
|---|---|
| Base path | `/api/` (no version prefix) |
| Request body | `application/json` unless noted (multipart for uploads) |
| Response body | `application/json` |
| Charset | UTF-8 |
| Datetimes | ISO 8601 UTC with `Z` suffix, e.g. `2026-08-27T12:04:11Z` |
| UUIDs | RFC 4122 string form, lowercase hex |

### 1.2 Session authentication

The POC uses Django session authentication. There is no JWT, SSO, or API-key
surface in this track.

| Rule | Detail |
|---|---|
| Login | Browser session established through Django auth views (not documented here) |
| Session cookie | `sessionid`; `HttpOnly`, `Secure` in production, `SameSite=Lax` |
| API access | Every `/api/` request must carry a valid session cookie |
| Unauthenticated | `401 Unauthorized` with error code `authentication_failed` |
| Session expiry | Standard Django session timeout; no silent extension on API calls |

### 1.3 CSRF protection

All state-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`) require a valid
CSRF token.

| Header | Value |
|---|---|
| `X-CSRFToken` | Token from the `csrftoken` cookie or page meta tag |

| Rule | Detail |
|---|---|
| Safe methods | `GET`, `HEAD`, `OPTIONS` do not require CSRF |
| Token mismatch | `403 Forbidden` with error code `csrf_failed` |
| Exempt endpoints | None in this track |

### 1.4 Active farm from session only

The active farm is **never** a request body field on scoped endpoints. It is
resolved exclusively from the server-side session after authentication.

| Rule | Detail |
|---|---|
| Selection | `POST /api/farms/{farm_id}/select` writes the active farm to the session |
| Scoped endpoints | Read `request.session['active_farm_id']` and verify `FarmRole` membership |
| Client-supplied `farm_id` | Rejected with `400 Bad Request`, code `farm_id_not_accepted`, if present in a body or query on a scoped endpoint |
| No farm selected | `403 Forbidden`, code `no_active_farm`, on any endpoint that requires a selected farm |
| Membership check | Every scoped request verifies the authenticated user holds a `FarmRole` on the active farm |

This rule applies to assistant messages, document upload, extraction candidates,
retrieval debug, audit export, and every other farm-scoped operation in this
document.

### 1.5 Standard request headers

| Header | Required | Purpose |
|---|---|---|
| `Accept: application/json` | Recommended | Response negotiation |
| `Content-Type: application/json` | Required on JSON bodies | Body parsing |
| `X-CSRFToken` | Required on mutations | CSRF protection |
| `X-Request-ID` | Optional (client) | Client correlation; echoed in error responses when supplied |
| `Idempotency-Key` | Optional on `POST` | See §1.8 |

The server generates a `request_id` for every request regardless of client
header. When the client supplies `X-Request-ID`, the server stores both values
in the audit record.

### 1.6 DRF error model

All error responses use Django REST Framework's default envelope, extended with
a stable machine-readable `code` and a server-generated `request_id`.

```json
{
  "detail": "Human-readable summary of the error.",
  "code": "machine_readable_snake_case",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "errors": [
    {
      "field": "message",
      "code": "blank",
      "message": "This field may not be blank."
    }
  ]
}
```

| Field | Presence | Meaning |
|---|---|---|
| `detail` | Always | Top-level human-readable message |
| `code` | Always | Stable error category for client branching |
| `request_id` | Always | Server-generated UUID for support and audit correlation |
| `errors` | Validation failures only | Per-field breakdown from DRF serializers |

Standard HTTP status codes:

| Status | When |
|---|---|
| `400 Bad Request` | Validation failure, malformed body, rejected client-supplied `farm_id` |
| `401 Unauthorized` | Missing or expired session |
| `403 Forbidden` | CSRF failure, insufficient role, no active farm, cross-farm access attempt |
| `404 Not Found` | Resource does not exist **or** exists but caller lacks visibility (no enumeration leak) |
| `409 Conflict` | Idempotency key reuse with different payload, snapshot activation race |
| `413 Payload Too Large` | Upload exceeds size limit |
| `422 Unprocessable Entity` | Semantically invalid but syntactically valid (e.g. approving an already-rejected candidate) |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Unhandled server failure |
| `503 Service Unavailable` | Dependency down (generation provider, PostgreSQL, audit write failure) |

Common stable `code` values:

| Code | HTTP | Meaning |
|---|---|---|
| `authentication_failed` | 401 | No valid session |
| `csrf_failed` | 403 | CSRF token missing or invalid |
| `permission_denied` | 403 | Authenticated but role insufficient |
| `no_active_farm` | 403 | Endpoint requires a selected farm |
| `farm_id_not_accepted` | 400 | Client supplied `farm_id` on a session-scoped endpoint |
| `not_found` | 404 | Resource not found or not visible |
| `validation_error` | 400 | Serializer validation failed |
| `rate_limit_exceeded` | 429 | Rate limit hit |
| `provider_unavailable` | 503 | External provider failure after retry |
| `audit_write_failed` | 503 | Audit persistence failed; request rejected |
| `conflict` | 409 | State conflict |

Field-level `errors[].code` values follow DRF defaults (`blank`, `max_length`,
`invalid_choice`, etc.) and are not duplicated here.

### 1.7 Async 202 Accepted pattern

Slow, retryable work is never held open on the HTTP connection. The API returns
`202 Accepted` with a durable status reference the client polls or refreshes
via HTMX.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "queued",
  "status_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440001",
  "poll_after_ms": 2000,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Field | Meaning |
|---|---|
| `job_id` | Durable identifier for the background job |
| `status` | `queued` \| `running` \| `succeeded` \| `failed` |
| `status_url` | Poll target; returns the same envelope with updated `status` and optional `result` |
| `poll_after_ms` | Suggested client backoff |

Job polling response when complete:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "succeeded",
  "result": { },
  "error": null,
  "started_at": "2026-08-27T12:04:11Z",
  "completed_at": "2026-08-27T12:04:45Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Endpoints using the async pattern in this track:

| Endpoint | Job type |
|---|---|
| `POST /api/documents` | Extraction → chunking → embedding |
| `POST /api/corpus/reindex` | Corpus snapshot import and embedding |
| `POST /api/corpus/snapshots/{snapshot_id}/activate` | Activation after embedding completeness check |
| `POST /api/schedule-explanations` | Schedule explanation generation (read-only to FarmFlow state) |

Jobs are idempotent. Retries update existing results; they never duplicate
chunks, candidates, or snapshot rows.

### 1.8 Idempotency

| Rule | Detail |
|---|---|
| Header | `Idempotency-Key: <opaque string>` on `POST` |
| Scope | Per authenticated user, per endpoint, 24-hour window |
| Same key, same payload | Returns the original response (including `202` job reference) |
| Same key, different payload | `409 Conflict`, code `idempotency_key_reused` |
| Without header | Each request creates a new resource/job |

### 1.9 Pagination

List endpoints use cursor-based pagination.

Query parameters:

| Param | Default | Max | Meaning |
|---|---|---|---|
| `cursor` | — | — | Opaque cursor from previous response |
| `limit` | 25 | 100 | Page size |

Response envelope:

```json
{
  "results": [ ],
  "next_cursor": "eyJpZCI6ICIuLi4ifQ==",
  "previous_cursor": null,
  "count": null
}
```

| Field | Meaning |
|---|---|
| `results` | Page of items |
| `next_cursor` | Present when more results exist; omit on last page |
| `previous_cursor` | Present when not on first page |
| `count` | Total count when cheap to compute; `null` otherwise |

Offset pagination is not supported. Clients must follow cursors.

### 1.10 Rate limits

Rate limits protect the generation provider and retrieval infrastructure. Limits
are enforced per authenticated user unless noted.

| Endpoint group | Limit | Window | Scope |
|---|---|---|---|
| `POST /api/assistant/messages` | 20 | 1 minute | Per user |
| `POST /api/assistant/messages` | 200 | 1 hour | Per user |
| `POST /api/retrieval/preview` | 30 | 1 minute | Per user (owner only) |
| `POST /api/documents` | 10 | 1 hour | Per farm |
| All other `/api/` | 120 | 1 minute | Per user |

Exceeded limits return `429 Too Many Requests`:

```json
{
  "detail": "Rate limit exceeded. Retry after 42 seconds.",
  "code": "rate_limit_exceeded",
  "request_id": "...",
  "retry_after_seconds": 42
}
```

Response headers on limited endpoints:

| Header | Meaning |
|---|---|
| `X-RateLimit-Limit` | Maximum requests in window |
| `X-RateLimit-Remaining` | Remaining requests |
| `X-RateLimit-Reset` | Unix timestamp when window resets |

### 1.11 Ownership matrix

| Endpoint group | Owner team | Notes |
|---|---|---|
| Health (`/healthz`, `/readyz`) | Assistant / Documents | Shared infrastructure checks |
| Farms and farm context | Assistant / Documents (auth in `accounts`/`farms`) | Session farm selection |
| Documents and extraction candidates | Assistant / Documents | Upload, processing, review |
| Assistant messages, reset, feedback | Assistant / Documents | Orchestrator and citations |
| Retrieval debug | Assistant / Documents | Feature-flagged; owner only |
| Corpus admin | Assistant / Documents | Snapshot import and activation |
| Schedule explanations, rule candidates | Assistant / Documents (read/explain boundary) | **FarmFlow write APIs owned by Scheduling team** |
| Audit events | Assistant / Documents | Owner-only read and export |
| Capabilities | Assistant / Documents | Runtime introspection |
| Tasks, schedules, FarmFlow proposals | **Scheduling team** | Not defined in this document |
| Alerts, map state | UI / Scheduling | Not defined in this document |

When this document references scheduling endpoints (`POST /api/schedule-proposals`,
`GET /api/schedules/{id}`, etc.), those contracts live with the Scheduling team.
This track owns only the **explanation** and **rule-candidate extraction**
boundary endpoints listed in §9.

---

## 2. Health

Operational probes for load balancers and CI. No authentication required.

### 2.1 GET /healthz

Liveness probe. Returns `200` when the Django process is running.

**Auth:** None

**Request:** No body. No query parameters.

**Response `200`:**

```json
{
  "status": "ok",
  "service": "farmcore",
  "timestamp": "2026-08-27T12:04:11Z"
}
```

**Errors:** None expected. Process death is detected by TCP failure, not HTTP.

**Owner:** Assistant / Documents

---

### 2.2 GET /readyz

Readiness probe. Returns `200` only when critical dependencies are reachable.

**Auth:** None

**Request:** No body.

**Checks performed:**

| Dependency | Required for ready |
|---|---|
| PostgreSQL | Yes |
| Redis (RQ transport) | Yes |
| MinIO | Yes |
| Active corpus snapshot present | Yes (warn-only in Phase 0 stub) |
| Generation provider | No (degraded mode allowed) |

**Response `200`:**

```json
{
  "status": "ready",
  "checks": {
    "postgresql": {"status": "ok", "latency_ms": 3},
    "redis": {"status": "ok", "latency_ms": 1},
    "minio": {"status": "ok", "latency_ms": 5},
    "corpus_snapshot": {
      "status": "ok",
      "active_snapshot_id": "gov-a-20260827-9f4c1ba7e2d0"
    },
    "generation_provider": {"status": "degraded", "detail": "timeout on probe"}
  },
  "timestamp": "2026-08-27T12:04:11Z"
}
```

**Response `503`:**

```json
{
  "status": "not_ready",
  "checks": {
    "postgresql": {"status": "failed", "detail": "connection refused"}
  },
  "timestamp": "2026-08-27T12:04:11Z"
}
```

**Owner:** Assistant / Documents

---

## 3. Farms

Farm listing, selection, and dashboard context. Active farm scopes all subsequent
Assistant / Documents operations.

### 3.1 GET /api/farms

List farms the authenticated user may access.

**Auth:** Authenticated session

**Request:** Optional pagination (`cursor`, `limit`).

**Response `200`:**

```json
{
  "results": [
    {
      "farm_id": "550e8400-e29b-41d4-a716-446655440010",
      "name": "Onboarding Demo Farm",
      "locality": "Tamworth, NSW",
      "timezone": "Australia/Sydney",
      "role": "owner",
      "is_active_selection": true
    },
    {
      "farm_id": "550e8400-e29b-41d4-a716-446655440011",
      "name": "Second Property",
      "locality": "Armidale, NSW",
      "timezone": "Australia/Sydney",
      "role": "worker",
      "is_active_selection": false
    }
  ],
  "next_cursor": null,
  "previous_cursor": null,
  "count": 2
}
```

| Field | Meaning |
|---|---|
| `role` | Caller's `FarmRole` on this farm: `owner` \| `worker` |
| `is_active_selection` | Whether this farm is the session's active farm |

**Errors:**

| Status | Code | When |
|---|---|---|
| 401 | `authentication_failed` | No session |

**Owner:** Assistant / Documents (implemented in `farms` app)

---

### 3.2 POST /api/farms/{farm_id}/select

Verify membership and set the active farm in the server-side session.

**Auth:** Authenticated session; user must hold any `FarmRole` on `{farm_id}`

**Request:** Empty body. Path parameter `farm_id` is the selection target only —
it does not override session scoping on other endpoints via request body.

**Response `200`:**

```json
{
  "farm_id": "550e8400-e29b-41d4-a716-446655440010",
  "name": "Onboarding Demo Farm",
  "role": "owner",
  "selected_at": "2026-08-27T12:04:11Z"
}
```

Side effect: writes `active_farm_id` and `active_farm_role` to the session.

**Errors:**

| Status | Code | When |
|---|---|---|
| 401 | `authentication_failed` | No session |
| 403 | `permission_denied` | User is not a member of `{farm_id}` |
| 404 | `not_found` | Farm does not exist |

**Owner:** Assistant / Documents (implemented in `farms` app)

---

### 3.3 GET /api/farm-context

Small dashboard snapshot for the active farm. Detailed resource endpoints follow
in later phases.

**Auth:** Authenticated session with active farm selected

**Request:** No body. No `farm_id` parameter — farm comes from session.

**Response `200`:**

```json
{
  "farm_id": "550e8400-e29b-41d4-a716-446655440010",
  "name": "Onboarding Demo Farm",
  "locality": "Tamworth, NSW",
  "timezone": "Australia/Sydney",
  "role": "owner",
  "weather": {
    "retrieved_at": "2026-08-27T06:00:00Z",
    "is_stale": false,
    "summary": "Fine, 18°C, light winds"
  },
  "document_counts": {
    "ready": 12,
    "processing": 1,
    "failed": 0
  },
  "pending_candidates": 3,
  "corpus_snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
  "capabilities_url": "/api/capabilities"
}
```

**Errors:**

| Status | Code | When |
|---|---|---|
| 401 | `authentication_failed` | No session |
| 403 | `no_active_farm` | No farm selected |
| 403 | `permission_denied` | Membership revoked since selection |

**Owner:** Assistant / Documents (implemented in `farms` app)

---

## 4. Documents and Extraction Candidates

Upload, processing status, archival, and owner review of structured extraction
candidates. Every supported upload is indexed for authorised retrieval even when
it yields no candidates.

### 4.1 POST /api/documents

Upload a document and queue extraction → chunking → embedding.

**Auth:** Owner role on active farm

**Request:** `multipart/form-data`

| Field | Required | Constraints |
|---|---|---|
| `file` | Yes | PDF or plain text; max 25 MB |
| `title` | No | Defaults to filename |
| `document_type` | No | Suggested classification: `soil_test`, `chemical_label`, `safety_procedure`, `service_record`, `contract`, `other` |
| `tags` | No | Comma-separated or repeated field |
| `visibility` | No | `owner_only` (default) \| `farm_shared` |

**Response `202`:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440020",
  "status": "queued",
  "status_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440020",
  "poll_after_ms": 2000,
  "document_id": "550e8400-e29b-41d4-a716-446655440021",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

When the job completes, `GET /api/documents/{document_id}` reflects final state.

**Errors:**

| Status | Code | When |
|---|---|---|
| 400 | `validation_error` | Missing file, unsupported type |
| 401 | `authentication_failed` | No session |
| 403 | `no_active_farm` | No farm selected |
| 403 | `permission_denied` | Worker attempting upload |
| 413 | — | File exceeds 25 MB |
| 429 | `rate_limit_exceeded` | Farm upload limit hit |

**Audit event:** `document.uploaded`

**Owner:** Assistant / Documents

---

### 4.2 GET /api/documents

List documents for the active farm.

**Auth:** Owner sees all; worker sees farm-shared and task-linked documents only

**Query parameters:** `cursor`, `limit`, optional `state` filter (`uploaded`,
`processing`, `ready`, `failed`, `archived`)

**Response `200`:**

```json
{
  "results": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440021",
      "title": "Soil Test — North Paddock",
      "document_type": "soil_test",
      "state": "ready",
      "visibility": "owner_only",
      "uploaded_at": "2026-08-27T11:00:00Z",
      "processed_at": "2026-08-27T11:02:30Z",
      "chunk_count": 8,
      "page_count": 3
    }
  ],
  "next_cursor": null,
  "previous_cursor": null,
  "count": 1
}
```

**Owner:** Assistant / Documents

---

### 4.3 GET /api/documents/{document_id}

Read processing status and metadata.

**Auth:** Owner or permitted worker (farm-shared or task-linked)

**Response `200`:**

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440021",
  "title": "Soil Test — North Paddock",
  "document_type": "soil_test",
  "state": "ready",
  "visibility": "owner_only",
  "tags": ["north-paddock", "2026"],
  "uploaded_at": "2026-08-27T11:00:00Z",
  "processed_at": "2026-08-27T11:02:30Z",
  "processing_stages": [
    {"stage": "extraction", "status": "succeeded", "completed_at": "2026-08-27T11:01:00Z"},
    {"stage": "chunking", "status": "succeeded", "completed_at": "2026-08-27T11:02:00Z"},
    {"stage": "embedding", "status": "succeeded", "completed_at": "2026-08-27T11:02:30Z"},
    {"stage": "candidate_generation", "status": "succeeded", "completed_at": "2026-08-27T11:02:45Z"}
  ],
  "chunk_count": 8,
  "page_count": 3,
  "failure_detail": null,
  "archived_at": null
}
```

**Response `200` when failed:**

```json
{
  "document_id": "...",
  "state": "failed",
  "failure_detail": {
    "stage": "extraction",
    "code": "empty_extraction",
    "message": "No extractable text found. Document may be image-only."
  }
}
```

**Errors:**

| Status | Code | When |
|---|---|---|
| 404 | `not_found` | Document not found or not visible to caller |

**Owner:** Assistant / Documents

---

### 4.4 POST /api/documents/{document_id}/archive

Disable retrieval and new candidate generation. Retains metadata and audit trail.

**Auth:** Owner on active farm

**Request:**

```json
{
  "reason": "Superseded by newer soil test"
}
```

**Response `200`:**

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440021",
  "state": "archived",
  "archived_at": "2026-08-27T12:04:11Z",
  "archived_by": "user-uuid"
}
```

Side effects: sets `doc_state = 'archived'` on all chunks; excludes from every
`RetrievalScope`; no new extraction candidates generated.

**Errors:**

| Status | Code | When |
|---|---|---|
| 403 | `permission_denied` | Worker attempting archive |
| 404 | `not_found` | Document not found |
| 422 | `validation_error` | Already archived |

**Audit event:** `document.archived`

**Owner:** Assistant / Documents

---

### 4.5 GET /api/extraction-candidates

List pending and recently decided extraction candidates for owner review.

**Auth:** Owner on active farm

**Query parameters:** `cursor`, `limit`, optional `state` (`pending`, `approved`,
`rejected`)

**Response `200`:**

```json
{
  "results": [
    {
      "candidate_id": "550e8400-e29b-41d4-a716-446655440030",
      "document_id": "550e8400-e29b-41d4-a716-446655440021",
      "candidate_type": "place",
      "state": "pending",
      "confidence": 0.87,
      "proposed_payload": {
        "name": "North Paddock",
        "place_type": "paddock",
        "area_ha": 12.5
      },
      "matched_record_id": null,
      "match_outcome": "create",
      "source_excerpt": "Sample taken from North Paddock, 12.5 ha",
      "created_at": "2026-08-27T11:02:45Z"
    }
  ],
  "next_cursor": null,
  "previous_cursor": null,
  "count": 1
}
```

| Field | Meaning |
|---|---|
| `match_outcome` | `create` \| `update` \| `conflict` — never silently overwrites |
| `matched_record_id` | Existing record when outcome is `update` or `conflict` |

**Owner:** Assistant / Documents

---

### 4.6 POST /api/extraction-candidates/{candidate_id}/approve

Approve an owner-edited candidate. Applies a validated create or update and emits
an audit event.

**Auth:** Owner on active farm

**Request:**

```json
{
  "edited_payload": {
    "name": "North Paddock",
    "place_type": "paddock",
    "area_ha": 12.4
  },
  "resolution_note": "Corrected area to match farm map"
}
```

When `match_outcome` is `conflict`, the request must include
`conflict_resolution`: `keep_existing` \| `apply_proposed` \| `merge_fields`.

**Response `200`:**

```json
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440030",
  "state": "approved",
  "applied_record_type": "place",
  "applied_record_id": "550e8400-e29b-41d4-a716-446655440040",
  "approved_at": "2026-08-27T12:04:11Z"
}
```

**Errors:**

| Status | Code | When |
|---|---|---|
| 404 | `not_found` | Candidate not found |
| 422 | `validation_error` | Not pending, payload invalid, unresolved conflict |

**Audit event:** `candidate.approved`

**Owner:** Assistant / Documents

---

### 4.7 POST /api/extraction-candidates/{candidate_id}/reject

Reject a candidate without creating or updating operational records.

**Auth:** Owner on active farm

**Request:**

```json
{
  "reason": "Incorrect paddock name"
}
```

**Response `200`:**

```json
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440030",
  "state": "rejected",
  "rejected_at": "2026-08-27T12:04:11Z"
}
```

**Audit event:** `candidate.rejected`

**Owner:** Assistant / Documents

---

## 5. Assistant

Chat orchestration, structured answers, session reset, and feedback. The active
farm and `FarmRole` come from the session; they are never request fields.

### 5.1 POST /api/assistant/messages

Send a message in the current conversation. Runs the full orchestrator pipeline
(Admit → Understand → Plan → Tools → Retrieve → Rank → Assemble → Gate →
Generate → Verify → Audit).

**Auth:** Authenticated user with active farm and tool permission for their role

**Request:**

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440050",
  "message": "Is my soil pH okay for the crop I'm planning, per government guidance?"
}
```

| Field | Required | Constraints |
|---|---|---|
| `conversation_id` | No | UUID; omit or null to start a new conversation |
| `message` | Yes | 1–4000 characters |

**Response `200` — full structured answer schema:**

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440050",
  "message_id": "550e8400-e29b-41d4-a716-446655440051",
  "audit_id": "550e8400-e29b-41d4-a716-446655440052",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "decision": "ANSWER",
  "refusal_code": null,
  "refusal_detail": null,
  "answer_text": "Your most recent soil test records pH 5.4 in North Paddock [1]. DAFF guidance recommends liming when pH falls below 5.5 for the planned crop [2].",
  "blocks": [
    {
      "type": "fact",
      "text": "Your most recent soil test records pH 5.4 in North Paddock [1].",
      "markers": [1]
    },
    {
      "type": "guidance",
      "text": "DAFF guidance recommends liming when pH falls below 5.5 for the planned crop [2].",
      "markers": [2]
    },
    {
      "type": "warning",
      "text": "Verify lime rate and timing with an agronomist before application.",
      "markers": []
    }
  ],
  "citations": [
    {
      "marker": 1,
      "source_class": "tenant_document",
      "chunk_id": "550e8400-e29b-41d4-a716-446655440060",
      "document_id": "550e8400-e29b-41d4-a716-446655440021",
      "title": "Soil Test — North Paddock",
      "dated": "2026-07-12",
      "excerpt": "pH (CaCl2): 5.4",
      "source_url": null,
      "entailment_score": 0.94,
      "verified": true
    },
    {
      "marker": 2,
      "source_class": "gov_tier_a",
      "chunk_id": "550e8400-e29b-41d4-a716-446655440061",
      "document_id": null,
      "title": "Soil acidity management",
      "dated": null,
      "excerpt": "Target pH above 5.5 for most winter cereals...",
      "source_url": "https://www.agriculture.gov.au/...",
      "snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
      "entailment_score": 0.91,
      "verified": true
    }
  ],
  "general_guidance": [],
  "warnings": [
    {
      "code": "SAFETY_VERIFY",
      "message": "Verify lime rate and timing with an agronomist before application."
    }
  ],
  "refusals": [],
  "drafts": [],
  "tools_used": [
    {
      "tool_name": "get_farm_context",
      "status": "succeeded",
      "latency_ms": 45
    },
    {
      "tool_name": "search_tenant_documents",
      "status": "succeeded",
      "latency_ms": 120
    }
  ],
  "retrieval": {
    "scopes_executed": [
      {
        "scope_type": "tenant_doc",
        "index_keys": ["tenant_doc"],
        "snapshot_id": null,
        "stages": [
          {
            "stage": "hybrid_recall",
            "candidate_count": 50,
            "top_score": 0.82
          },
          {
            "stage": "rerank",
            "candidate_count": 8,
            "top_score": 0.91
          },
          {
            "stage": "mmr",
            "candidate_count": 4
          }
        ],
        "final_chunk_ids": ["550e8400-e29b-41d4-a716-446655440060"]
      },
      {
        "scope_type": "gov_tier_a",
        "index_keys": ["gov_tier_a"],
        "snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
        "stages": [
          {
            "stage": "hybrid_recall",
            "candidate_count": 50,
            "top_score": 0.78
          },
          {
            "stage": "rerank",
            "candidate_count": 8,
            "top_score": 0.88
          },
          {
            "stage": "mmr",
            "candidate_count": 3
          }
        ],
        "final_chunk_ids": ["550e8400-e29b-41d4-a716-446655440061"]
      }
    ],
    "fallback_invoked": false,
    "degraded": []
  },
  "versions": {
    "corpus_snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
    "chunker_version": "chunk-v3",
    "embedding_model_id": "bge-large-en-v1.5:revision:1024",
    "retrieval_config_version": "retr-v2",
    "reranker_model_id": "bge-reranker-v2-m3",
    "prompt_template_id": "answer-blended-v4",
    "tool_registry_version": "tools-v5",
    "generation_model_id": "provider:model:revision",
    "verifier_model_id": "deberta-mnli-v1",
    "schema_version": "chunks-v1"
  },
  "config_fingerprint": "9f4c1ba7e2d0-retr-v2-tools-v5",
  "retrieved_at": "2026-08-27T12:04:11Z",
  "latency_ms": {
    "total": 4820,
    "admit": 45,
    "understand": 180,
    "plan": 95,
    "tools": 165,
    "retrieve": 420,
    "rank": 380,
    "assemble": 55,
    "gate": 30,
    "generate": 3100,
    "verify": 280,
    "audit": 70
  }
}
```

#### Block types

| Type | Meaning | Citation requirement |
|---|---|---|
| `fact` | Claim grounded in retrieved evidence or structured tool output | Must carry markers resolving to citations |
| `guidance` | General advisory text grounded in corpus or registered guidance | Must carry markers when corpus-sourced |
| `warning` | Safety, compliance, staleness, or verification prompts | Markers optional |

#### Refusal response shape

When `decision` is `REFUSE` or `PARTIAL`:

```json
{
  "decision": "REFUSE",
  "refusal_code": "TENANT_SCOPE_EMPTY",
  "refusal_detail": "I don't have soil test records for your farm. Upload a recent soil test PDF to get paddock-specific advice.",
  "answer_text": null,
  "blocks": [],
  "citations": [],
  "refusals": [
    {
      "code": "TENANT_SCOPE_EMPTY",
      "message": "I don't have soil test records for your farm.",
      "action_hint": "Upload a recent soil test PDF."
    }
  ]
}
```

Refusal codes (from refusal registry):

| Code | Meaning |
|---|---|
| `NO_RELEVANT_CONTEXT` | Nothing retrieved above threshold |
| `INSUFFICIENT_COVERAGE` | Partial query coverage only |
| `CONFLICTING_SOURCES` | Material contradiction unresolved |
| `OUT_OF_SCOPE` | Outside agriculture/farm domain |
| `ACCESS_DENIED` | Relevant content exists but role excludes it |
| `TENANT_SCOPE_EMPTY` | Farm data needed but not uploaded |
| `PROVIDER_UNAVAILABLE` | Generation provider failed |

#### Drafts in response

Draft payloads appear when the orchestrator proposes inert records:

```json
{
  "drafts": [
    {
      "draft_id": "550e8400-e29b-41d4-a716-446655440070",
      "draft_type": "task",
      "state": "draft",
      "expires_at": "2026-08-28T12:04:11Z",
      "payload": {
        "title": "Apply lime to North Paddock",
        "due_at": "2026-09-15T00:00:00Z"
      },
      "confirm_url": "/api/task-drafts/550e8400-e29b-41d4-a716-446655440070/confirm"
    }
  ]
}
```

Draft confirmation endpoints are owned by the Scheduling team. This track returns
draft payloads only.

**Errors:**

| Status | Code | When |
|---|---|---|
| 400 | `validation_error` | Empty message, message too long |
| 401 | `authentication_failed` | No session |
| 403 | `no_active_farm` | No farm selected |
| 403 | `permission_denied` | Role lacks tool permission |
| 429 | `rate_limit_exceeded` | Assistant rate limit |
| 503 | `provider_unavailable` | Generation failed after retry |
| 503 | `audit_write_failed` | Audit persistence failed |

**Audit event:** `assistant.message.completed` (always, including refusals)

**Owner:** Assistant / Documents

---

### 5.2 POST /api/assistant/conversations/reset

Clear current-session conversation context. Does not delete audit records.

**Auth:** Authenticated user

**Request:** Empty body or:

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440050"
}
```

When `conversation_id` is omitted, resets the active conversation for the
current user and farm session.

**Response `200`:**

```json
{
  "reset_at": "2026-08-27T12:04:11Z",
  "conversation_id": null
}
```

**Owner:** Assistant / Documents

---

### 5.3 POST /api/assistant/messages/{message_id}/feedback

Submit user feedback on an assistant response.

**Auth:** Authenticated user who received the message

**Request:**

```json
{
  "rating": "helpful",
  "comment": "Citation to soil test was exactly what I needed.",
  "tags": ["accurate_citation", "actionable"]
}
```

| Field | Values |
|---|---|
| `rating` | `helpful` \| `not_helpful` \| `harmful` |
| `comment` | Optional, max 1000 characters |
| `tags` | Optional list from controlled vocabulary |

**Response `201`:**

```json
{
  "feedback_id": "550e8400-e29b-41d4-a716-446655440080",
  "message_id": "550e8400-e29b-41d4-a716-446655440051",
  "recorded_at": "2026-08-27T12:04:11Z"
}
```

Feedback is stored separately from the audit record and linked by `message_id`
and `audit_id`.

**Owner:** Assistant / Documents

---

## 6. Retrieval Debug

Owner-only diagnostic endpoints behind the `FEATURE_RETRIEVAL_DEBUG` feature
flag. Disabled by default in production-like environments.

### 6.1 Feature flag

| Flag | Default | Effect |
|---|---|---|
| `FEATURE_RETRIEVAL_DEBUG` | `false` | When false, all §6 endpoints return `404 not_found` |

When enabled, responses include a `"debug": true` marker.

### 6.2 POST /api/retrieval/preview

Run retrieval stages without generation. Returns candidates at each funnel step.

**Auth:** Owner on active farm

**Request:**

```json
{
  "query": "soil pH liming winter cereals",
  "scope": "blended",
  "top_k": 8,
  "include_tier_b_fallback": true
}
```

| Field | Values |
|---|---|
| `scope` | `gov_tier_a` \| `tenant_doc` \| `blended` |
| `include_tier_b_fallback` | Whether to simulate Tier B fallback pass |

**Response `200`:**

```json
{
  "debug": true,
  "query": "soil pH liming winter cereals",
  "scopes": [
    {
      "scope_type": "tenant_doc",
      "retrieval_scope": {
        "farm_id": "550e8400-e29b-41d4-a716-446655440010",
        "farm_role": "owner",
        "logical_indexes": ["tenant_doc"],
        "snapshot_id": null
      },
      "stages": {
        "dense_recall": {"count": 50, "top": [{"chunk_id": "...", "score": 0.82}]},
        "lexical_recall": {"count": 50, "top": [{"chunk_id": "...", "score": 12.4}]},
        "rrf_fusion": {"count": 50, "top": [{"chunk_id": "...", "score": 0.031}]},
        "rerank": {"count": 8, "top": [{"chunk_id": "...", "score": 0.91}]},
        "mmr": {"count": 4, "chunk_ids": ["..."]}
      }
    }
  ],
  "fallback": null,
  "latency_ms": 380,
  "versions": { }
}
```

**Owner:** Assistant / Documents

---

### 6.3 GET /api/retrieval/traces

List retrieval trace summaries linked to audit records.

**Auth:** Owner on active farm

**Query parameters:** `cursor`, `limit`, optional `audit_id`, optional date range

**Response `200`:**

```json
{
  "results": [
    {
      "trace_id": "550e8400-e29b-41d4-a716-446655440090",
      "audit_id": "550e8400-e29b-41d4-a716-446655440052",
      "query": "soil pH liming",
      "decision": "ANSWER",
      "scope_count": 2,
      "final_chunk_count": 7,
      "created_at": "2026-08-27T12:04:11Z"
    }
  ],
  "next_cursor": null,
  "previous_cursor": null,
  "count": null
}
```

**Owner:** Assistant / Documents

---

### 6.4 POST /api/retrieval/replay

Re-execute retrieval for a past audit record against its pinned snapshot and
version tuple.

**Auth:** Owner on active farm

**Request:**

```json
{
  "audit_id": "550e8400-e29b-41d4-a716-446655440052",
  "override": {
    "retrieval_config_version": null,
    "top_k": 8
  }
}
```

Only `top_k` and non-version-breaking config overrides are permitted. Changing
`corpus_snapshot_id` or `embedding_model_id` requires a full reindex, not replay.

**Response `200`:**

```json
{
  "debug": true,
  "audit_id": "550e8400-e29b-41d4-a716-446655440052",
  "original_fingerprint": "9f4c1ba7e2d0-retr-v2-tools-v5",
  "replay_fingerprint": "9f4c1ba7e2d0-retr-v2-tools-v5",
  "match": true,
  "scopes": [ ],
  "diff": null
}
```

When overrides produce different results, `match` is `false` and `diff` lists
changed chunk IDs per stage.

**Owner:** Assistant / Documents

---

### 6.5 GET /api/retrieval/chunks/{chunk_id}

Fetch chunk text and metadata for citation debugging.

**Auth:** Owner on active farm; chunk must be visible under caller's scope

**Response `200`:**

```json
{
  "debug": true,
  "chunk_id": "550e8400-e29b-41d4-a716-446655440060",
  "parent_id": "550e8400-e29b-41d4-a716-446655440065",
  "document_id": "550e8400-e29b-41d4-a716-446655440021",
  "index_key": "tenant_doc",
  "farm_id": "550e8400-e29b-41d4-a716-446655440010",
  "tier": null,
  "doc_title": "Soil Test — North Paddock",
  "source_url": null,
  "heading_path": ["Results", "Chemical Analysis"],
  "token_count": 412,
  "content_hash": "sha256:abc123...",
  "text": "pH (CaCl2): 5.4\nOrganic carbon: 2.1%...",
  "snapshot_id": null,
  "created_at": "2026-08-27T11:02:00Z"
}
```

**Errors:**

| Status | Code | When |
|---|---|---|
| 404 | `not_found` | Chunk not found or cross-farm |

**Owner:** Assistant / Documents

---

## 7. Corpus Admin

Government corpus snapshot import, index management, and activation. Tenant
documents are not part of corpus snapshots.

Current corpus baseline (2026-08-27):

| Metric | Count |
|---|---|
| Tier A documents | 2,250 |
| Tier B documents | 1,054 |
| Tier C documents | 1,268 (excluded) |
| Tier A PDFs fetched | 639 |
| Tier A PDFs text extracted | 605 |

### 7.1 GET /api/corpus/indexes

List logical indexes and their status.

**Auth:** Owner on active farm (read-only introspection)

**Response `200`:**

```json
{
  "indexes": [
    {
      "index_key": "gov_tier_a",
      "description": "Curated government agriculture corpus — Tier A",
      "document_count": 2250,
      "chunk_count": 48200,
      "active_snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
      "embedding_complete": true,
      "tier": "A"
    },
    {
      "index_key": "gov_tier_b",
      "description": "Fallback government corpus — Tier B",
      "document_count": 1054,
      "chunk_count": 0,
      "active_snapshot_id": null,
      "embedding_complete": false,
      "tier": "B"
    },
    {
      "index_key": "tenant_doc",
      "description": "Farm-uploaded documents",
      "document_count": 12,
      "chunk_count": 96,
      "active_snapshot_id": null,
      "embedding_complete": true,
      "tier": null
    }
  ]
}
```

**Owner:** Assistant / Documents

---

### 7.2 GET /api/corpus/snapshots

List published gov corpus snapshots.

**Auth:** Owner

**Response `200`:**

```json
{
  "results": [
    {
      "snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
      "tier_set": "a",
      "build_date": "2026-08-27",
      "chunk_count": 48200,
      "document_count": 605,
      "chunker_version": "chunk-v3",
      "source_pipeline_commit": "abc1234",
      "is_active": true,
      "imported_at": "2026-08-27T08:00:00Z",
      "embedding_status": "complete"
    }
  ],
  "next_cursor": null,
  "previous_cursor": null,
  "count": 1
}
```

**Owner:** Assistant / Documents

---

### 7.3 POST /api/corpus/reindex

Import a snapshot artifact and enqueue embedding. Does not activate until
embedding completes and an explicit activation call succeeds.

**Auth:** Owner (typically operator/admin principal in POC)

**Request:**

```json
{
  "snapshot_path": "/data/snapshots/gov-a-20260827-9f4c1ba7e2d0",
  "replace_existing": false
}
```

**Response `202`:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440100",
  "status": "queued",
  "status_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440100",
  "poll_after_ms": 5000,
  "snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
  "request_id": "..."
}
```

Import validates `checksums.txt`, chunk schema, and aborts without touching the
active snapshot on any failure.

**Owner:** Assistant / Documents

---

### 7.4 POST /api/corpus/snapshots/{snapshot_id}/activate

Atomically flip the active corpus snapshot pointer after embedding completeness
check.

**Auth:** Owner (operator)

**Request:** Empty body

**Response `202`:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440101",
  "status": "queued",
  "status_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440101",
  "poll_after_ms": 2000,
  "snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
  "previous_snapshot_id": "gov-a-20260820-1a2b3c4d5e6f",
  "request_id": "..."
}
```

On success the job result includes:

```json
{
  "snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
  "activated_at": "2026-08-27T12:04:11Z",
  "rollback_available": true
}
```

**Errors:**

| Status | Code | When |
|---|---|---|
| 409 | `conflict` | Embedding incomplete |
| 404 | `not_found` | Snapshot not imported |

**Audit event:** `corpus.snapshot.activated`

**Owner:** Assistant / Documents

---

### 7.5 GET /api/jobs/{job_id}

Poll any async job referenced by `status_url` in this document.

**Auth:** Same principal that created the job

**Response:** See §1.7 async envelope.

**Owner:** Assistant / Documents

---

## 8. Scheduling Boundary

The Assistant track may **explain** schedules and **propose rule candidates**
from documents. It never writes schedules, tasks, or placements. All FarmFlow
write APIs (`POST /api/schedule-proposals`, schedule approval, task CRUD) are
owned by the **Scheduling team** and are not specified here.

### 8.1 POST /api/schedule-explanations

Generate a plain-language explanation of why a schedule proposal assigned,
moved, delayed, or left unscheduled each job. Read-only against approved
FarmFlow state.

**Auth:** Owner on active farm

**Request:**

```json
{
  "schedule_id": "550e8400-e29b-41d4-a716-446655440110",
  "job_ids": ["550e8400-e29b-41d4-a716-446655440111"],
  "focus": "unscheduled"
}
```

| Field | Meaning |
|---|---|
| `schedule_id` | Target schedule proposal |
| `job_ids` | Optional subset; omit for all jobs |
| `focus` | `all` \| `unscheduled` \| `changed` |

**Response `202`:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440112",
  "status": "queued",
  "status_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440112",
  "poll_after_ms": 3000,
  "request_id": "..."
}
```

Completed job result:

```json
{
  "schedule_id": "550e8400-e29b-41d4-a716-446655440110",
  "explanations": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440111",
      "task_title": "Spray North Paddock",
      "outcome": "unscheduled",
      "reason_code": "WEATHER_CONSTRAINT",
      "reason_text": "Forecast wind exceeds 25 km/h maximum for spraying on Tuesday afternoon.",
      "structured_inputs": {
        "max_wind_kph": 25,
        "forecast_wind_kph": 32,
        "forecast_retrieved_at": "2026-08-27T06:00:00Z"
      },
      "citations": []
    }
  ],
  "generated_at": "2026-08-27T12:04:11Z"
}
```

Explanations cite structured FarmFlow reason codes and weather snapshots — not
retrieved document chunks — unless a linked rule document is referenced.

**Owner:** Assistant / Documents (explanation generation); Scheduling team
(FarmFlow state and write APIs)

---

### 8.2 GET /api/rule-candidates

List rule candidates extracted from documents, pending owner approval.

**Auth:** Owner on active farm

**Query parameters:** `cursor`, `limit`, optional `state` (`pending`, `approved`,
`rejected`)

**Response `200`:**

```json
{
  "results": [
    {
      "candidate_id": "550e8400-e29b-41d4-a716-446655440120",
      "document_id": "550e8400-e29b-41d4-a716-446655440021",
      "state": "pending",
      "proposed_rule": {
        "name": "Monthly coop inspection",
        "cadence": "monthly",
        "task_template_id": null,
        "proposed_template": {
          "title": "Coop safety inspection",
          "duration_minutes": 60,
          "required_role": "owner"
        }
      },
      "source_excerpt": "Inspect coops monthly for structural damage...",
      "confidence": 0.79,
      "created_at": "2026-08-27T11:02:45Z"
    }
  ],
  "next_cursor": null,
  "previous_cursor": null,
  "count": 1
}
```

Approved rules become structured data consumed by FarmFlow. The Scheduling team
owns the `rules` table write path after approval.

**Owner:** Assistant / Documents

---

### 8.3 POST /api/rule-candidates

Manually create a rule candidate (owner-initiated, not document-derived).

**Auth:** Owner on active farm

**Request:**

```json
{
  "proposed_rule": {
    "name": "Weekly egg collection",
    "cadence": "weekly",
    "proposed_template": {
      "title": "Collect eggs",
      "duration_minutes": 30,
      "required_role": "worker"
    }
  },
  "source_note": "Owner-entered recurring task"
}
```

**Response `201`:**

```json
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440121",
  "state": "pending",
  "created_at": "2026-08-27T12:04:11Z"
}
```

**Owner:** Assistant / Documents

---

### 8.4 POST /api/rule-candidates/{candidate_id}/approve

Approve a rule candidate. Creates an approved rule and task template via the
Scheduling team's service boundary.

**Auth:** Owner on active farm

**Request:**

```json
{
  "edited_payload": {
    "name": "Monthly coop inspection",
    "cadence": "monthly"
  }
}
```

**Response `200`:**

```json
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440120",
  "state": "approved",
  "rule_id": "550e8400-e29b-41d4-a716-446655440130",
  "approved_at": "2026-08-27T12:04:11Z"
}
```

**Audit event:** `rule_candidate.approved`

**Owner:** Assistant / Documents (candidate workflow); Scheduling team (`rules`
persistence)

---

### 8.5 POST /api/rule-candidates/{candidate_id}/reject

**Auth:** Owner

**Request:**

```json
{
  "reason": "Already covered by existing rule"
}
```

**Response `200`:**

```json
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440120",
  "state": "rejected",
  "rejected_at": "2026-08-27T12:04:11Z"
}
```

**Owner:** Assistant / Documents

---

## 9. Audit

Append-only audit event read and export. Owner only. No deletion surface exists
for the POC lifetime.

### 9.1 GET /api/audit/events

List audit events with filters.

**Auth:** Owner on active farm

**Query parameters:**

| Param | Meaning |
|---|---|
| `cursor`, `limit` | Pagination |
| `event_type` | Filter: `assistant.message.completed`, `document.uploaded`, `candidate.approved`, etc. |
| `since`, `until` | ISO datetime range |
| `audit_id` | Exact match |
| `user_id` | Filter by actor |

**Response `200`:**

```json
{
  "results": [
    {
      "event_id": "550e8400-e29b-41d4-a716-446655440140",
      "audit_id": "550e8400-e29b-41d4-a716-446655440052",
      "event_type": "assistant.message.completed",
      "timestamp": "2026-08-27T12:04:11Z",
      "actor_user_id": "550e8400-e29b-41d4-a716-446655440015",
      "farm_id": "550e8400-e29b-41d4-a716-446655440010",
      "summary": "ANSWER — blended query, 2 citations",
      "schema_version": "audit-v1"
    }
  ],
  "next_cursor": "eyJ...",
  "previous_cursor": null,
  "count": null
}
```

**Owner:** Assistant / Documents

---

### 9.2 GET /api/audit/events/{event_id}

Full audit event detail.

**Auth:** Owner on active farm; event must belong to active farm

**Response `200`:**

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440140",
  "audit_id": "550e8400-e29b-41d4-a716-446655440052",
  "event_type": "assistant.message.completed",
  "schema_version": "audit-v1",
  "timestamp": "2026-08-27T12:04:11Z",
  "actor_user_id": "550e8400-e29b-41d4-a716-446655440015",
  "farm_id": "550e8400-e29b-41d4-a716-446655440010",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "payload": {
    "raw_query": "Is my soil pH okay...",
    "rewritten_query": "soil pH suitability winter cereal DAFF guidance",
    "retrieval_stages": [
      {"stage": "hybrid_recall", "scope": "tenant_doc", "candidates": [{"chunk_id": "...", "score": 0.82}]},
      {"stage": "rerank", "scope": "tenant_doc", "candidates": [{"chunk_id": "...", "score": 0.91}]},
      {"stage": "final_context", "chunk_ids": ["..."]}
    ],
    "groundedness_decision": "ANSWER",
    "refusal_reason": null,
    "tools_invoked": [{"tool_name": "get_farm_context", "status": "succeeded"}],
    "citations": [{"claim": "pH 5.4", "chunk_id": "...", "entailment_score": 0.94}],
    "version_tuple": {
      "corpus_snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
      "retrieval_config_version": "retr-v2",
      "prompt_template_id": "answer-blended-v4"
    },
    "latency_ms": {"total": 4820}
  }
}
```

Audit payloads store concise structured metadata. They do not store raw document
bytes or full model prompts. Secrets are redacted.

**Owner:** Assistant / Documents

---

### 9.3 POST /api/audit/exports

Request an audit export for compliance or debugging.

**Auth:** Owner on active farm

**Request:**

```json
{
  "since": "2026-08-01T00:00:00Z",
  "until": "2026-08-27T23:59:59Z",
  "event_types": ["assistant.message.completed", "candidate.approved"],
  "format": "jsonl"
}
```

| Field | Values |
|---|---|
| `format` | `jsonl` \| `csv` |

**Response `202`:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440150",
  "status": "queued",
  "status_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440150",
  "poll_after_ms": 5000,
  "request_id": "..."
}
```

Completed job result includes a time-limited presigned download URL:

```json
{
  "export_id": "550e8400-e29b-41d4-a716-446655440151",
  "download_url": "https://minio.example/presigned/...",
  "expires_at": "2026-08-27T13:04:11Z",
  "record_count": 142,
  "format": "jsonl"
}
```

**Audit event:** `audit.export.requested`

**Owner:** Assistant / Documents

---

## 10. Capabilities

Runtime introspection for clients, UI, and integration tests.

### 10.1 GET /api/capabilities

Return the current runtime capability manifest.

**Auth:** Authenticated session (any role)

**Response `200`:**

```json
{
  "release_version": "poc-2026-08-27",
  "openapi_version": "1.0.0",
  "tools": [
    {
      "tool_name": "get_farm_context",
      "class": "read",
      "required_role": "worker",
      "input_schema_ref": "#/components/schemas/GetFarmContextInput",
      "output_schema_ref": "#/components/schemas/GetFarmContextOutput",
      "registry_version": "tools-v5"
    },
    {
      "tool_name": "search_tenant_documents",
      "class": "read",
      "required_role": "worker",
      "input_schema_ref": "#/components/schemas/SearchTenantDocumentsInput",
      "output_schema_ref": "#/components/schemas/SearchTenantDocumentsOutput",
      "registry_version": "tools-v5"
    },
    {
      "tool_name": "draft_task",
      "class": "draft",
      "required_role": "owner",
      "input_schema_ref": "#/components/schemas/DraftTaskInput",
      "output_schema_ref": "#/components/schemas/DraftTaskOutput",
      "registry_version": "tools-v5"
    }
  ],
  "retrieval_stages": [
    "query_rewrite",
    "dense_recall",
    "lexical_recall",
    "rrf_fusion",
    "metadata_filter",
    "rerank",
    "mmr",
    "parent_expansion",
    "context_pack"
  ],
  "indexes": [
    {"index_key": "gov_tier_a", "tier": "A", "document_count": 2250},
    {"index_key": "gov_tier_b", "tier": "B", "document_count": 1054},
    {"index_key": "tenant_doc", "tier": null, "document_count": null}
  ],
  "providers": {
    "embedding": {"adapter": "bge-local", "model_id": "bge-large-en-v1.5", "dimension": 1024},
    "generation": {"adapter": "openai-compatible", "model_id": "configured-at-runtime"},
    "reranker": {"adapter": "bge-reranker", "model_id": "bge-reranker-v2-m3"},
    "entailment": {"adapter": "deberta-nli", "model_id": "deberta-mnli-v1"},
    "extraction": {"adapter": "pymupdf", "model_id": "pinned-in-manifest"},
    "object_store": {"adapter": "minio", "model_id": null},
    "weather": {"adapter": "open-meteo", "model_id": null}
  },
  "answer_contract": {
    "schema_version": "answer-v1",
    "required_fields": [
      "conversation_id",
      "audit_id",
      "decision",
      "blocks",
      "citations",
      "warnings",
      "retrieved_at",
      "versions"
    ],
    "block_types": ["fact", "guidance", "warning"],
    "decisions": ["ANSWER", "PARTIAL", "REFUSE"],
    "refusal_codes": [
      "NO_RELEVANT_CONTEXT",
      "INSUFFICIENT_COVERAGE",
      "CONFLICTING_SOURCES",
      "OUT_OF_SCOPE",
      "ACCESS_DENIED",
      "TENANT_SCOPE_EMPTY",
      "PROVIDER_UNAVAILABLE"
    ],
    "source_classes": ["tenant_document", "gov_tier_a", "gov_tier_b", "farm_record"]
  },
  "feature_flags": {
    "FEATURE_RETRIEVAL_DEBUG": false,
    "FEATURE_TIER_B_FALLBACK": true,
    "FEATURE_ENTAILMENT_VERIFY": true,
    "FEATURE_DRAFT_TASKS": true
  },
  "corpus": {
    "active_snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
    "tier_a_documents": 2250,
    "tier_b_documents": 1054,
    "tier_c_documents": 1268,
    "tier_a_pdfs_fetched": 639,
    "tier_a_pdfs_extracted": 605
  },
  "version_tuple": {
    "corpus_snapshot_id": "gov-a-20260827-9f4c1ba7e2d0",
    "chunker_version": "chunk-v3",
    "embedding_model_id": "bge-large-en-v1.5:revision:1024",
    "retrieval_config_version": "retr-v2",
    "reranker_model_id": "bge-reranker-v2-m3",
    "prompt_template_id": "answer-blended-v4",
    "tool_registry_version": "tools-v5",
    "generation_model_id": "provider:model:revision",
    "verifier_model_id": "deberta-mnli-v1",
    "schema_version": "chunks-v1"
  }
}
```

**Owner:** Assistant / Documents

---

## 11. Related Records

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — normative runtime architecture
- [`EXTENSIBILITY.md`](EXTENSIBILITY.md) — ports, registries, extension rules
- [`PLAN.md`](PLAN.md) — phased delivery and gates
- [`MAPPING.md`](MAPPING.md) — DesignDoc traceability
- `FARMCORE_DOCS/api-contract-questions.md` — upstream contract decisions
- `docs/openapi/` — generated OpenAPI schema (DRF serializers are source of truth)
