# FarmCore Architecture Decision Checklist

Use this as the running architecture checklist for FarmCore POC.

`[x]` means team agreed on architecture decision. It does **not** mean feature is implemented.

`[ ]` means decision still needs discussion, evidence, or explicit agreement.

## Current Position

```text
Completed: POC golden path, data ownership, document-review policy,
assistant database boundary, FarmFlow timing, rescheduling model, weather approach.

Completed: system shape, background-job boundary, frontend access boundary.

Current focus: farm-owner data intake, PostGIS/pgvector schema follow-ups, and first REST endpoint contracts.

Next after that: component designs, detailed contracts, implementation skeleton.
```

## 1. Product Boundary and POC Outcome

- [x] FarmCore has shared operational data layer, AI chat assistant, and FarmFlow scheduler.
- [x] Primary POC flow: login -> select farm -> upload documents -> review candidates -> chat -> task confirmation -> weekly schedule proposal -> approval -> audit history.
- [x] POC uses one representative farm scenario and one-week scheduling period.
- [x] Important actions require human confirmation.
- [x] Development/demo uses a ready Operational Demo Farm and a separate empty Onboarding Demo Farm.
- [x] Onboarding demo uses the real upload, extraction, candidate-review, and approval workflow.
- [x] Provide repeatable `demo-seed` and `demo-reset` commands.
- [ ] Define exact final demonstration script and success metrics.

Reference: [POC Golden Path](poc-golden-path.md).

## 2. Data Ownership and Document Ingestion

- [x] Object storage owns original uploaded files.
- [x] PostgreSQL owns approved, durable operational data.
- [x] Vector store is retrieval index, not source of truth for farm operations.
- [x] Multiple documents support farm onboarding.
- [x] POC required formats: PDF and text, including tabular PDFs.
- [x] DOCX and image OCR are deferred.
- [x] Extraction creates generic `extraction_candidates` records.
- [x] Candidate facts, rules, tasks, crops, machinery, and animal records require user approval before activation.
- [x] Index every supported uploaded document for authorised retrieval, whether or not it yields structured candidates.
- [x] Candidate review explicitly distinguishes create, update, and potential-conflict outcomes; it never silently overwrites approved data.
- [ ] Add `extraction_candidates` to logical schema, SQL DDL, and migrations.
- [ ] Team review: confirm the first extraction candidate types and validated `payload` shapes: places, animal groups, machinery, task templates, rules, and document classification.
- [x] Processing lifecycle: `uploaded` -> `processing` -> `ready` or `failed`; retry transient failures once, then offer owner manual retry.

Reference: [POC Golden Path](poc-golden-path.md).

## 3. Assistant Boundaries and Behaviour

- [x] Assistant has no direct SQL access or database credentials.
- [x] Assistant uses controlled backend tools only.
- [x] Assistant can read structured farm context and document retrieval results.
- [x] Assistant creates drafts/proposals, not active durable records.
- [x] Client scope requires current-conversation follow-up context and clear/new-chat behaviour, not durable cross-session history.
- [x] Durable chat-history persistence is optional and delegated to the assistant team.
- [x] Data-grounded assistant answers display document/record citations; general guidance is visibly labelled.
- [x] Assistant surfaces missing or conflicting required information instead of silently resolving it.
- [x] Safety/compliance guidance includes a warning and asks for human verification before action.
- [x] Initial read tools: farm context, tasks, approved rules, schedules, alerts, authorised document search, cached weather, and controlled current-weather lookup.
- [x] Initial proposal tools: draft a task, draft a task update, and request a FarmFlow schedule proposal; none writes active records.
- [x] Current-weather lookup goes through controlled backend weather client and cache/audit path, never direct model access to an external API.
- [x] Assistant natural-language task updates create reviewable task-update drafts; human confirmation writes `task_updates`.
- [ ] Finalise each tool's input/output contract.
- [ ] Decide which tools are read-only versus draft/proposal-capable.
- [x] Leave LLM/provider experimentation and POC selection to the assistant team; do not impose a central provider decision.
- [x] Define clear/new-chat behaviour; persistent conversation history is not required by client scope.
- [ ] Define citation format and missing/conflicting-data response rules.
- [ ] Define tool-call audit detail and retention needs.

Reference: [POC Golden Path](poc-golden-path.md).

## 4. FarmFlow Scheduling

- [x] FarmFlow uses approved structured data, not raw document text or vector-search output.
- [x] Rules and templates generate tasks; tasks become scheduled jobs.
- [x] POC creates one-week schedules.
- [x] POC uses morning/afternoon blocks stored as real start/end timestamps.
- [x] Initial schedule generation is user initiated.
- [x] Relevant changes create new schedule proposals, never overwrite approved schedules.
- [x] Completed tasks remain unchanged during rebuilds.
- [x] Scheduler explains scheduled, moved, delayed, and unscheduled work.
- [x] FarmFlow is deterministic: the same approved inputs produce the same schedule proposal.
- [x] LLM/RAG may extract candidate rules or explain results, but does not make final task-placement decisions.
- [x] Hard constraints eliminate invalid slots; soft priorities rank feasible slots.
- [x] Owners may edit a proposal before approval; changing an approved schedule creates a new proposed version linked to its base schedule.
- [ ] Define exact scheduler input contract.
- [ ] Define deterministic scoring order and tie-breakers.
- [ ] Define exact hard-constraint evaluation for staff, machinery, places, dependencies, and weather.
- [ ] Define weather constraints for each POC task type.
- [ ] Define authorised roles for schedule generation and approval.

Reference: [FarmFlow Rescheduling](farmflow-rescheduling.md).

Open scheduling questions: [FarmFlow Scheduling Questions](scheduling-questions.md).

## 5. Weather Integration

- [x] POC uses live weather API data.
- [x] Backend weather worker fetches and normalises forecasts.
- [x] PostgreSQL stores forecast snapshots.
- [x] Assistant reads cached forecast through controlled backend tool.
- [x] FarmFlow uses latest forecast snapshot when generating proposal.
- [x] Use a free forecast provider that supplies the normalised POC data contract; exact provider is an implementation choice.
- [x] Refresh active-farm seven-day forecasts every six hours; controlled current-weather requests may refresh the cache when practical.
- [x] Treat forecast data older than twelve hours as stale and show a warning while using the latest available snapshot.
- [ ] Define API key handling, rate-limit behaviour, and cost limit.
- [ ] Define meaningful forecast-change threshold for rescheduling.
- [x] Define stale-weather UI state; define no-usable-weather state during detailed weather-constraint design.

Reference: [FarmCore Weather Integration](weather-integration.md).

## 6. System Shape and Component Boundaries

- [x] POC uses a modular monolith, not separately deployed microservices.
- [x] Frontend accesses external systems only through backend API.
- [x] Slow/external work runs as background jobs from backend codebase.
- [x] Django owns server-rendered pages and HTMX fragment endpoints for browser UI.
- [x] REST JSON endpoints under `/api/` support controlled assistant tools and integrations.
- [x] REST endpoints will be documented with an OpenAPI specification.
- [x] Use Django REST Framework for REST endpoints and `drf-spectacular` for OpenAPI generation.
- [x] Do not add FastAPI alongside Django for the POC.
- [x] Use domain-focused Django apps in one modular monolith, not one catch-all app.
- [x] Django app boundaries: `accounts`, `farms`, `documents`, `assistant`, and `scheduling`.
- [x] Apps share one deployment/database but own their business logic and public service interfaces.
- [x] Build and protect a first runnable vertical slice: login -> authorised farm selection -> scoped dashboard.
- [x] Teams may prototype providers independently; merged code uses only small, owned client modules.
- [x] Do not build a generic provider framework or plug-in system for the POC.
- [x] Shared schema, migrations, seed data, and documented contracts are the team integration points.
- [x] FarmFlow consumes approved structured data and normalised weather data, not direct LLM calls.
- [x] Use Django-RQ with Redis for background jobs; do not introduce Celery for the POC.
- [x] Use the RQ scheduler for recurring POC jobs such as weather refresh and alert evaluation.
- [x] Treat PostgreSQL as durable business/job-result state and make background jobs idempotent.
- [x] Use Django session authentication and a custom email-based user model; defer JWT/external identity providers.
- [x] Start with PostgreSQL `pgvector` for embeddings; evaluate Qdrant only if evidence supports a later change.
- [x] Use PostGIS geography for farm/place spatial data; detailed geometry fields still need schema design.
- [x] Standardise local development through Docker Compose: Django, PostgreSQL with pgvector, Redis, RQ worker/scheduler, and S3-compatible object storage.
- [x] Use MinIO as the initial S3-compatible object store for local POC development.
- [x] Store original document bytes in MinIO and document metadata/status in PostgreSQL.
- [x] Keep the selected farm in the authenticated server-side session and verify `FarmRole` on every scoped operation.
- [x] Limit POC roles to farm owner and worker.
- [x] Use Django templates and HTMX for the full browser layer; do not add a separate frontend framework/application.
- [x] UI team owns templates, static assets, HTMX interactions, and map rendering; Django owns rendering, authorisation, and data access.
- [x] Django apps use in-process, deliberate service functions for internal integration; do not make internal HTTP calls or cross-app direct writes.
- [ ] Define detailed internal service interfaces between Django apps.
- [x] Choose Django-RQ/Redis for queue transport and PostgreSQL for durable job-result state.
- [x] Choose pgvector as the initial vector-search implementation.
- [x] Choose MinIO as initial local object storage; defer hosted S3 choice.
- [x] Retain archived documents, chunks, embeddings, candidates, schedules, and audit events for full POC lifetime; no automatic deletion job or permanent-purge UI.
- [ ] Perform focused pgvector-versus-Qdrant comparison before changing retrieval architecture.
- [x] Use `farms.location_point` as a required PostGIS point for weather lookup.
- [x] Use `places.boundary` as PostGIS `GEOMETRY(MULTIPOLYGON, 4326)` for map context; seed boundaries for every POC place.
- [x] Map visualisation represents scheduled/current task state at a place, not live GPS tracking.
- [x] Seed Operational Demo Farm boundaries; real-farm boundaries remain optional and polygon editing is deferred.
- [ ] Add the agreed PostGIS fields to the logical schema, DDL, and migrations.
- [ ] Add pgvector embeddings/index to the retrieval schema after embedding dimension is known.
- [x] Keep external-provider access in small domain-owned client modules, not scattered SDK calls.
- [ ] Select concrete LLM, embedding, weather, and document-extraction providers.
- [x] Use local Docker Compose per developer and one shared hosted demo environment; defer separate staging environment.
- [x] Use generated Swagger UI, `GET /healthz` dependency checks, and structured request/RQ logs; do not add external monitoring platform.

Reference: [FarmCore System Shape](system-shape.md).

## 7. Access Control, Approvals, and Audit

- [x] Selected farm scopes all records, retrieval, tasks, and scheduling.
- [x] Approved rules/tasks/schedules are durable PostgreSQL data.
- [x] Important AI-assisted actions are audit logged.
- [x] Active selected farm is stored server-side and checked against `FarmRole` on every scoped operation.
- [x] POC roles: farm owner and worker only.
- [ ] Team review: confirm worker permissions. Proposed scope: view own assigned work/map/task-linked documents, update availability/progress, upload supported incident documents, and submit maintenance/task requests; no direct record activation, schedule authority, or farm/user administration.
- [ ] Team review: confirm worker task-request design using `tasks.approval_status` (`pending`, `approved`, `rejected`) and optional `tasks.source_document_id`; only approved tasks are eligible for FarmFlow.
- [x] Use consistent review UX: proposed change, source/reason, affected records, edit/confirm/reject, then audit outcome.
- [x] Audit significant document, assistant/tool, candidate, task, worker-progress, and schedule events using concise structured metadata.
- [x] Owner retrieves all active selected-farm documents; worker retrieves only farm-shared safety/procedure documents and task-linked documents.
- [x] Enforce document/citation authorisation in the backend retrieval query before chunks reach the assistant or UI.
- [x] Archive documents rather than offering permanent user deletion; archival disables retrieval and new candidate generation but retains metadata/audit trail.
- [x] Keep audit events append-only for POC lifetime; only owner may search/export them and no audit-deletion UI exists.

## 8. Data Model and Database Delivery

- [x] POC logical schema exists.
- [x] PostgreSQL DDL draft exists.
- [ ] Review logical schema against confirmed `extraction_candidates` decision.
- [ ] Convert SQL DDL into versioned database migrations.
- [ ] Choose ORM/query layer and migration tool.
- [x] Define two demo farm datasets: ready operational and empty onboarding.
- [x] Build repeatable seed/reset workflow for those demo datasets.
- [ ] Define which tables are Sprint 1 core versus later additions.
- [ ] Add document visibility/archive fields and `task_documents` link to logical schema, DDL, and migrations.

References: [POC Logical Schema](../client-notion/erd-whiteboard-tables.md), [POC SQL DDL](../client-notion/erd-poc-schema.sql.md).

## 9. API and Shared Contracts

- [x] Use REST JSON endpoints for the programmatic API contract.
- [x] Use an OpenAPI specification to describe that REST API.
- [x] Use `/api/` without a URL version prefix for the POC; label the OpenAPI document with its release version instead.
- [x] Slow actions return accepted/status references immediately; Django-RQ updates durable PostgreSQL status for UI/API polling.
- [ ] Define Django page and HTMX-fragment endpoint conventions.
- [x] Select farm through authorised `POST /api/farms/{farm_id}/select`; scope subsequent requests from server-side session.
- [x] Use small `GET /api/farm-context` dashboard snapshot; detailed resource endpoints follow later.
- [x] Upload documents asynchronously; expose document status and owner-only extraction candidate review.
- [x] Candidate review uses list/approve/reject operations; approval accepts owner-edited payload, validates/applies create-update, and writes audit event.
- [x] Assistant responses return structured answer, citations, facts-versus-guidance, warnings, retrieval timestamp, and optional draft/proposal data.
- [x] Task/task-update drafts persist in PostgreSQL with short-lived draft state until owner confirmation or rejection.
- [x] Durable drafts use `draft` -> `confirmed`/`rejected`/`expired` lifecycle; only confirmation writes active task/task-update data.
- [x] Worker task progress uses authorised task-update operation with status, note, and optional supported-document evidence reference.
- [x] Schedule proposal request returns accepted/job reference; proposal read includes jobs, unscheduled reasons, and base-schedule diff; approval/rejection are owner operations.
- [x] Owner has full operational control: proposed placement edits validate immediately; task-definition/lifecycle edits trigger proposal revalidation or rebuild; system identity/audit/explanation fields remain protected.
- [x] Rules use draft/pending-review/approved-active/rejected lifecycle; only approved active rules affect FarmFlow and approved-rule edits require review.
- [x] Use in-app alerts only, with alert read state and user alert preferences; no SMS, email, or push integration in POC.
- [x] Owner audit API supports filtered read/export of concise structured events only, not raw chat/document content.
- [x] Map state API returns GeoJSON place boundaries plus requester-permitted task/schedule state; server applies owner/worker filtering.
- [x] Browser uses full Django page routes and named HTMX fragment routes; `/api/` remains JSON-first for tools, map data, and integrations.
- [x] DRF serializers and generated OpenAPI/Swagger UI are the JSON contract source of truth; do not create a separate shared-types package.
- [ ] Define draft-table model, expiry policy, and exact task-confirmation contracts.
- [ ] Define task/rule CRUD and confirmation APIs.
- [ ] Define FarmFlow schedule-proposal, approval, rejection, and modification APIs.
- [ ] Define shared types for frontend, backend, assistant, and scheduler.
- [x] Use Django REST Framework default JSON errors and HTTP status codes; use normal Django/HTMX validation fragments for browser pages.

Open API contract questions: [FarmCore API Contract Questions](api-contract-questions.md).

## 10. Implementation and Team Delivery

- [ ] Choose repository structure and coding conventions.
- [ ] Create frontend, backend, shared-types, database, and docs skeleton.
- [ ] Set up local development environment and environment-variable policy.
- [ ] Set up automated tests and continuous integration.
- [ ] Assign component ownership and integration owner.
- [ ] Define pull-request review and merge process.
- [ ] Define sprint vertical slices and demo criteria.
- [ ] Define deployment and demonstration plan.

Reference: [Skeleton Readiness Checklist](skeleton-readiness-checklist.md).

## Related Records

- [System Design Index](README.md)
- [Farm Owner Data Intake](farm-owner-data-intake.md)
- [POC Golden Path](poc-golden-path.md)
- [FarmFlow Rescheduling](farmflow-rescheduling.md)
- [FarmCore Weather Integration](weather-integration.md)
- [Client Project Brief](../client-notion/project-brief.md)
- [Client User Stories](../client-notion/user-stories.md)
