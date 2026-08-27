# FarmCore API Contract Questions

Audience: project lead and implementation teams.

Purpose: define the POC API surface before serializers, views, and detailed
OpenAPI schemas. The team agrees endpoint purpose, authorisation, asynchronous
behaviour, and error cases; exact field names follow during implementation.

## Locked Decisions

- Browser UI uses Django pages and HTMX fragments. JSON endpoints are under
  `/api/` for controlled programmatic operations and integrations.
- No URL version prefix in the POC. OpenAPI carries the release version.
- Django REST Framework default JSON errors and HTTP status codes are used.
- Selected-farm scope comes from authenticated server-side session, never an
  arbitrary `farm_id` supplied by the browser.
- Slow work returns a durable status reference for polling/refresh.
- JSON endpoints never expose direct SQL, MinIO, pgvector, LLM, or weather API.

## POC Endpoint Areas

### 1. Authentication and Active Farm

| Operation | Proposed purpose | Role |
|---|---|---|
| `GET /api/farms` | List authorised farms | Authenticated user |
| `POST /api/farms/{farm_id}/select` | Verify membership and set active farm session | Authorised member |
| `GET /api/farm-context` | Small dashboard snapshot | Active selected farm |

Questions: What minimum fields belong in dashboard context? What occurs with
zero/one authorised farm? Is switching a full page navigation, HTMX update, or
both?

### 2. Documents and Candidate Review

| Operation | Proposed purpose | Role |
|---|---|---|
| `POST /api/documents` | Upload and queue processing | Owner |
| `GET /api/documents/{document_id}` | Read processing status | Owner or permitted worker |
| `GET /api/extraction-candidates` | List review candidates | Owner |
| `POST /api/extraction-candidates/{candidate_id}/approve` | Approve edited candidate | Owner |
| `POST /api/extraction-candidates/{candidate_id}/reject` | Reject candidate | Owner |
| `POST /api/documents/{document_id}/archive` | Disable retrieval/new extraction | Owner |

Questions: Does approval receive an owner-edited payload? How are create/update/
conflict results rendered? Which processing details can a worker view?

Decision: approval accepts an owner-edited payload, applies a validated
create/update, and emits an audit event.

### 3. Assistant and Retrieval

| Operation | Proposed purpose | Role |
|---|---|---|
| `POST /api/assistant/messages` | Send active-session message | Selected-farm user, tool permission enforced |
| `POST /api/assistant/conversations/reset` | Clear current-session context | Current user/session |
| Current-weather tool | Controlled backend weather lookup | Authorised selected-farm user |

Questions: Which response fields are required: answer, citations, facts versus
guidance, warnings, retrieval timestamp, draft/proposal? Which tool calls are
shown to owner versus audit-only?

Decision: response includes answer, citations, facts-versus-guidance, warnings,
retrieval timestamp, and optional draft/proposal data.

### 4. Tasks and Worker Requests

| Operation | Proposed purpose | Role |
|---|---|---|
| Task draft creation/confirmation | Assistant/owner workflow, then active task | Owner |
| Worker task request | Report maintenance/work request | Worker or owner; owner approval needed |
| `POST /api/tasks/{task_id}/updates` | Progress, blockage, completion evidence | Assigned worker or owner |
| Pending-request approval/rejection | Activate/reject reported work | Owner |

Questions: Are task drafts session-scoped, database-backed, or pending task
records? What POC evidence formats are supported? How is optional source document
linked to a worker request?

Decision: task and task-update drafts are database-backed, short-lived, and not
active tasks until owner confirmation/rejection. Draft-table shape and expiry
remain open.

Decision: durable drafts use `draft` -> `confirmed`/`rejected`/`expired` lifecycle.
Worker task progress uses an authorised task-update operation with status, note,
and optional supported-document evidence reference.

### 5. FarmFlow Schedules

| Operation | Proposed purpose | Role |
|---|---|---|
| `POST /api/schedule-proposals` | Queue FarmFlow proposal | Owner |
| `GET /api/schedules/{schedule_id}` | Read proposal/status | Owner; worker sees own work only |
| Approve/reject/edit proposal | Schedule decision workflow | Owner |
| Regenerate schedule | Create new proposal version | Owner |

Questions: How are scheduled/unscheduled reasons returned? What diff data does
calendar/map require? How do manual proposed-schedule edits validate conflicts?

Decision: proposal request is asynchronous; proposal read includes jobs,
unscheduled reasons, and diff from base; owner approves/rejects. Manual edit
contract remains open.

Decision: owner may change any operational decision. Placement edits update the
proposed job and validate conflicts immediately. Task definition/lifecycle edits
update the task and trigger proposal revalidation/rebuild; system identity, audit,
and generated-reason fields are protected.

Decision: only approved/active rules affect scheduling; use in-app alerts with
read state and preferences, without SMS, email, or push integration.

### 6. Alerts, Audit, and Map

| Operation | Proposed purpose | Role |
|---|---|---|
| Alert read/mark-read | Read/update user alerts | Recipient |
| Audit search/export | Audit query/export | Owner |
| Map state | Places plus permitted task/schedule state | Owner; worker own work only |

Questions: Which alert actions are POC-essential? What audit filters/export are
needed for demo? What map state is HTML-rendered versus JSON for map code?

Decision: owner audit access supports filtered/exported concise structured events
only. Map state is GeoJSON place boundaries plus requester-permitted task/schedule
state. Browser workflows use Django pages/HTMX fragments; `/api/` is JSON-first.

## Endpoint Review Checklist

For each implemented endpoint, record:

1. Method and path.
2. Required role and selected-farm enforcement.
3. Request fields and validation rules.
4. Success status and response shape.
5. Expected DRF error statuses.
6. Sync or background-job behaviour.
7. Required audit event.

## References

- [Architecture Decision Checklist](architecture-decision-checklist.md)
- [Skeleton Readiness Checklist](skeleton-readiness-checklist.md)
- [Farm Owner Data Intake](farm-owner-data-intake.md)
- [FarmFlow Scheduling Questions](scheduling-questions.md)
