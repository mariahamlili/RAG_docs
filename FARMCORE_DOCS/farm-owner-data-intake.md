# Farm Owner Data Intake and Table Population

Sources:

- [POC PostgreSQL Schema](../client-notion/erd-poc-schema.sql.md)
- [Project Brief](../client-notion/project-brief.md)
- [User Stories](../client-notion/user-stories.md)

This record identifies which tables need owner/worker input, document-candidate
review, or system-generated data. A farm owner does not fill every table during
onboarding.

## Minimum Farm Onboarding Data

The owner enters or confirms:

1. Farm name, locality/address, timezone, and a weather lookup point. A farm
   boundary is optional in the POC.
2. Relevant paddock, barn, coop, shed, and pasture names/types.
3. Owner/worker profiles, availability, and only skills needed by POC tasks.
4. Relevant crop, animal group, and/or machinery records. Unused categories are
   not required.
5. Approved task templates/rules, entered manually or approved from documents.
6. Uploaded documents, their classification, and proposed extraction candidates.

Historical milk, egg, and treatment records improve answers but are not required
for FarmFlow's first weekly schedule.

## Table Ownership

### Identity and staff

| Tables | Source | POC treatment |
|---|---|---|
| `users` | System account setup | Create owner on registration and worker account only when worker login is needed. Never expose `password_hash`. |
| `farms` | Owner | Name, locality/address, timezone, weather location. |
| `farm_memberships` | Owner action + system | Owner grants worker farm access. |
| `roles`, `skills` | Seed | Shared controlled catalogue; owner assigns values rather than inventing app roles. |
| `staff_members`, `staff_roles`, `staff_skills` | Owner | Create/link staff profile and assign operational capability. |
| `staff_availability` | Worker or owner | Worker maintains working/unavailable windows; owner may correct them. |

### Farm context and operations

| Tables | Source | POC treatment |
|---|---|---|
| `places` | Owner or document candidate | Confirm name, type, area, and point/boundary. Covers paddocks, barns, coops, sheds, and pastures. |
| `crops` | Owner or document candidate | Confirm crop, place, stage, and dates. Create only for the scenario. |
| `animal_groups` | Owner or document candidate | Confirm group, species, purpose, head count, and place. |
| `animals` | Owner | Optional and only for individual dairy tracking; never individual chickens. |
| `machinery` | Owner or document candidate | Confirm identity, type, place, state, and optional hour meter. |
| `milk_production_records`, `egg_collection_records` | Worker/owner | Ongoing event data; seed for demo if useful, not onboarding-required. |
| `treatment_records` | Worker/owner or document candidate | Useful for safety/withholding context, not required for initial schedule. |

### Documents and retrieval

| Tables | Source | POC treatment |
|---|---|---|
| `documents` | Owner upload + confirmation | Backend creates metadata/status; owner confirms type, tags, and expiry if relevant. |
| `document_chunks` | System | Parsing job creates text plus citation page/section metadata. |
| `document_tags` | Suggested then owner-confirmed | Owner accepts, edits, or removes tags. |
| `extraction_candidates` (planned) | System then owner approval | Pending generic facts; approval creates/updates operational rows. |

Every supported upload is indexed for authorised retrieval, even when it has no
structured candidate. Manuals, policies, labels, and certificates remain useful
cited sources without becoming operational table records.

When a candidate matches existing approved data, the review must explicitly show
one of three outcomes: create a new record, update an identified record, or
potential conflict. The system never silently overwrites approved farm facts.

### Retrieval Authorisation

FarmCore uses one shared pgvector-backed document index, not a separate vector
store per user. Every assistant/retrieval request carries the authenticated user
and selected farm. The backend filters authorised documents before returning any
matching chunk to the assistant or UI:

```text
owner  -> all active documents for selected farm
worker -> farm-shared safety/procedure documents, plus documents linked to one
          of that worker's assigned tasks
```

The eventual similarity query joins chunks to their document and applies the
farm/visibility/task-link filter in the same backend query. The LLM receives only
the permitted returned chunks, never database credentials or unfiltered vector
search access.

This requires a small schema follow-up: document visibility scope, for example
`owner_only`, `farm_shared`, or `task_linked`, plus `task_documents` to link a
document to an assigned task. This is safer and simpler than running separate
vector stores.

### Tasks, schedules, and governance

| Tables | Source | POC treatment |
|---|---|---|
| `task_templates`, `rules` | Owner or document candidate | Reusable work/constraints; owner approval is required. |
| `tasks` | Owner-confirmed draft, owner input, rule, or worker request | Real work occurrence. Proposed worker requests remain pending owner approval before FarmFlow can use them. |
| `task_dependencies` | Owner | Add only for required demo prerequisites. |
| `task_updates` | Worker/owner | Progress, blockage, completion, and optional evidence. |
| `weather_forecasts` | System | Weather worker fetches normalised forecasts using farm geography. |
| `schedules`, `scheduled_jobs` | System then owner approval | FarmFlow proposes; owner approves/rejects/modifies. |
| `alerts` | System | Generated for relevant overdue/weather/maintenance/compliance events. |
| `alert_preferences` | Owner/worker | Minimal per-user alert preferences. |
| `audit_events` | System | Append-only record; never manually edited. |

## Candidate Scope

Start document extraction candidates with places, crops, animal groups,
machinery, task templates, rules, treatment records, and document classification.
If delivery requires a smaller set, reduce it but preserve review/approval.
Production history, individual animals, and staff availability should use forms
or seed data rather than generic document parsing.

## Scheduler Minimum Dataset

FarmFlow needs approved tasks with duration/priority/time window, one active
available worker, required place and machinery where relevant, a rule/template
only for recurring work, and farm timezone/weather geography. Crop, livestock,
treatment, and skill data apply only where a task or rule references them.

## Required Schema Follow-Ups

1. **PostGIS:** current DDL has numeric latitude/longitude only. Add `postgis`.
   Use required `farms.location_point GEOGRAPHY(POINT, 4326)` for weather and
   `places.boundary GEOMETRY(MULTIPOLYGON, 4326)` for map display. Every seeded
   POC place has a boundary; real-farm boundary entry may be completed later.
   The map derives an anchor inside the boundary for task/status display.
2. **pgvector:** `document_chunks` has no embedding column/index because the DDL
   assumed a separate vector store. Add the pgvector design after embedding
   dimension is known.
3. **Extraction candidates:** add the agreed generic table to logical schema,
   DDL, and migrations.
4. **Weather:** add precipitation probability and wind gust where the selected
   free provider supplies them, or retain a source payload for traceability.
5. **Worker task requests (team review):** consider `tasks.approval_status` and
   optional `tasks.source_document_id`, so workers can report maintenance work
   without activating a task or changing a schedule directly.
6. **Document access/removal:** add document visibility and `task_documents` for
   authorised retrieval. Add archive fields so owner archival removes content
   from retrieval/candidate generation while retaining metadata and audit trail.

## Related Documents

- [System Shape](system-shape.md)
- [Weather Integration](weather-integration.md)
- [POC Logical Schema](../client-notion/erd-whiteboard-tables.md)
- [POC SQL DDL](../client-notion/erd-poc-schema.sql.md)
