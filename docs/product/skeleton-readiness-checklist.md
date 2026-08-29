# FarmCore Skeleton Readiness Checklist

This checklist defines the decisions and deliverables needed before the team can
rely on one shared, runnable FarmCore skeleton. It is deliberately narrower than
the full architecture checklist: it does not block on detailed AI, document, or
FarmFlow behaviour.

`[x]` means agreed. `[ ]` means it still needs a decision or implementation plan.

## Target First Vertical Slice

```text
Login
-> select an authorised demo farm
-> store active farm in server-side session
-> load farm context from PostgreSQL
-> show owner/worker appropriate dashboard view
```

This slice proves the shared runtime, identity, farm scoping, database, and
browser interaction before specialist features are integrated.

## Already Decided

- [x] Django modular monolith with domain apps: `accounts`, `farms`,
  `documents`, `assistant`, and `scheduling`.
- [x] Django + HTMX pages; Django REST Framework JSON API under `/api/`.
- [x] Django session authentication with a custom email-based user model.
- [x] Two farm-scoped roles: farm owner and worker.
- [x] Active farm is server-side session state and must be authorised through
  `farm_roles` on every scoped request.
- [x] Docker Compose local stack: Django, PostgreSQL with pgvector and PostGIS, Redis,
  Django-RQ worker/scheduler, and MinIO.
- [x] Operational Demo Farm and Onboarding Demo Farm seed states.

## Decisions Needed Before Skeleton Work

### 1. Repository and Django Layout

- [ ] Decide the project directory layout for Django configuration, apps,
  templates, static assets, tests, Docker, and documentation.
- [ ] Decide whether the HTMX frontend lives in Django templates only for the
  POC. Recommended: yes; do not add a separate frontend build system yet.
- [ ] Define dependency management and Python version. Recommended: one
  lockfile and a documented `make setup` / `docker compose up` path.
- [ ] Define naming and import conventions for Django apps, services, API
  serializers, and background jobs.

### 2. Runtime Configuration

- [ ] Define `.env.example` variables and secret-handling rules.
- [ ] Define Docker Compose service names, ports, health checks, named volumes,
  and development-only tooling.
- [ ] Define the minimum commands: start, stop, migrate, seed, reset onboarding
  demo, run tests, and inspect worker logs.
- [ ] Define local email behaviour. Recommended: console backend; do not send
  real email in the POC.

### 3. Database and Seed Baseline

- [ ] Convert the POC SQL schema into Django migrations, including the custom
  user model and agreed `extraction_candidates` addition.
- [ ] Decide the first migration ownership/review process.
- [ ] Define the minimum records required for the first vertical slice:
  owner, worker, roles, authorised farm memberships, farm, and displayable farm
  context.
- [ ] Define deterministic `demo-seed` and `demo-reset` command behaviour.
- [ ] Define how MinIO seed files and PostgreSQL seed records remain consistent.

### 4. Authentication and Access Baseline

- [ ] Define login, logout, and unauthenticated redirect behaviour.
- [ ] Define password setup/reset behaviour for demo users. Recommended: known
  development-only seed credentials, documented outside committed secrets.
- [ ] Define the exact owner/worker permission matrix for the first slice.
- [ ] Define behaviour when a user has zero farms or only one authorised farm.
- [ ] Define active-farm switching and session-clear behaviour.

### 5. First UI and API Contract

- [ ] Define the first page routes: login, farm selection, and dashboard.
- [ ] Define the dashboard information needed for the first slice.
- [ ] Define the first REST endpoints and schemas: authorised farms and current
  farm context.
- [ ] Define standard API error response and HTML error/empty-state conventions.
- [ ] Define which updates use full-page navigation versus HTMX fragments.

### 6. Quality and Team Integration

- [ ] Define initial test layers: unit, Django integration, and minimal browser
  flow test.
- [ ] Define the vertical-slice acceptance test for both owner and worker.
- [ ] Define CI minimum: formatting/linting, migrations check, and tests.
- [ ] Define pull-request ownership for shared schema, compose, configuration,
  and API-contract changes.

## Not Skeleton Blockers

These can proceed in parallel once seed contracts exist:

- Detailed LLM/provider selection and chat behaviour.
- PDF extraction and embedding implementation.
- Full task/rule CRUD.
- FarmFlow scheduling algorithm.
- Weather provider selection and alert policy.
- Deployment hosting provider.

## Exit Criteria

The skeleton is ready for component integration when a new team member can:

1. Follow documented setup instructions.
2. Start the local stack with one command.
3. Seed both demo farms.
4. Log in as an owner or worker.
5. Select only an authorised farm.
6. See the appropriate scoped dashboard.
7. Run the automated checks successfully.

## Related Documents

- [System Shape](system-shape.md)
- [Architecture Decision Checklist](architecture-decision-checklist.md)
- [POC Golden Path](poc-golden-path.md)
- [POC Logical Schema](../client-notion/erd-whiteboard-tables.md)
- [POC SQL DDL](../client-notion/erd-poc-schema.sql.md)
