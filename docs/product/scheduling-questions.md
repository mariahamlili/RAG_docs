# FarmFlow Scheduling Questions

Audience: FarmFlow scheduling team and project lead.

Purpose: collect the unresolved scheduling decisions that need domain and
implementation input. The team should recommend a POC answer for each item,
with an example. The project lead records the final decision in the main
[Architecture Decision Checklist](architecture-decision-checklist.md).

## Decisions Already Locked

Do not reopen these unless new client evidence requires it.

- FarmFlow builds one-week schedule proposals using morning/afternoon blocks
  stored as real start/end timestamps.
- It consumes approved structured PostgreSQL data, never raw document text or
  vector-search results.
- Approved rules/templates create task occurrences before FarmFlow schedules
  them; FarmFlow schedules tasks, not rules.
- Scheduling is deterministic. LLM/RAG may propose rules or explain results but
  never makes final task-placement decisions.
- Hard constraints eliminate invalid slots; soft priorities rank feasible slots.
- Initial generation is owner initiated. Relevant changes create a new proposal;
  FarmFlow never overwrites an approved schedule.
- Completed tasks remain unchanged on rebuild.
- Owner can edit a proposal before approval. Changing an approved schedule
  creates a new proposed schedule version linked to the existing one.
- POC supports one assigned worker and one machinery item per scheduled job.
- Each job must explain why it was scheduled, moved, delayed, or unscheduled.

## Questions for the Scheduling Team

### 1. Task Eligibility

Which task statuses are eligible for scheduling?

Recommended POC answer:

```text
Schedule only not_started tasks in the planning week.
Exclude completed and cancelled tasks.
Keep blocked tasks unscheduled with their blocking reason.
Treat in_progress tasks as fixed/current work unless owner explicitly reschedules.
```

Questions:

- Can a task without a due date be scheduled, and if so where does it rank?
- How should overdue tasks be treated?
- Does a task require an `earliest_start_at` and/or `due_at` to be schedulable?

### 2. Time Blocks and Work Hours

What exact timestamps define `morning` and `afternoon` for the POC farm?

Questions:

- Are blocks fixed, for example 06:00-12:00 and 12:00-18:00, or derived from
  each worker's availability?
- May a task shorter than a block share that block with another task?
- May a task span blocks or days in the POC?
- How are breaks and travel time handled: ignored, fixed buffer, or simple
  same-place grouping only?

Recommended POC answer: fixed blocks, one task per worker/block when its duration
fits, no multi-day splitting, and same-place grouping rather than route planning.

### 3. Exact Hard Constraints

For each task/slot, which conditions make it impossible?

Baseline candidates:

- task status/time window/dependency invalid
- required worker unavailable or inactive
- required role/skill missing
- required machinery unavailable or double booked
- place double booked, if place exclusivity applies
- mandatory weather constraint breached

Questions:

- Is place double-booking always a conflict, or only for certain place types?
- Does a preferred worker mean mandatory assignment or only preference?
- How should staff who are available but lack an optional skill be treated?
- What is the owner-visible unscheduled reason for each failure type?

### 4. Soft Priority and Tie-Breaking

What deterministic scoring order chooses among valid slots?

Recommended order:

```text
1. Mandatory safety/compliance work
2. Higher task priority
3. Earlier due date / narrower time window
4. Weather suitability before conditions deteriorate
5. Preserve equivalent existing placement during rebuild
6. Preferred worker and same-place work grouping
7. Stable ID/time ordering as final tie-breaker
```

Questions:

- Is this order correct for the representative farm scenario?
- Which criteria need numeric weights, if any, versus simple ordered comparison?
- How should the system explain the winning score in plain language?

### 5. Weather Constraints

Which task types have weather restrictions and what thresholds apply?

Recommended representation per task template/rule:

```json
{
  "requires_dry": true,
  "max_wind_kph": 25,
  "max_rainfall_mm": 1
}
```

Questions:

- Which POC tasks are weather-sensitive: spraying, planting, harvesting,
  machinery work, egg collection, inspections, or others?
- Are forecast values hard blockers or soft penalties for each task type?
- What weather change is material enough to trigger an impact check/rebuild?
- What should occur when forecast data is stale or missing?

### 6. Resources and Assignment

How should FarmFlow choose a worker/machine when multiple valid choices exist?

Questions:

- Does required operational role always outrank preferred worker?
- Does the worker's current/previous scheduled place influence assignment?
- Does every machinery task require an explicit machinery record?
- Can owner manually lock a worker, machine, or time before regeneration?

Recommended POC answer: required role/skill is hard; preferred worker and
same-place grouping are soft; owner locks are respected as hard constraints.

### 7. Dependencies and Unscheduled Work

How should dependency failures appear in the proposal?

Questions:

- Can a task be scheduled in a later block after its prerequisite, or must the
  prerequisite be completed before proposal generation?
- When no feasible slot exists, should FarmFlow offer the first alternative,
  list all blocked reasons, or both?
- What is the minimum structured data required in `constraint_summary` for the
  UI and audit record?

### 8. Rebuild Behaviour

Which relevant changes rebuild a schedule and how are rapid changes handled?

Already agreed triggers include weather, staff availability, machinery status,
task/rule changes, user request, and task completion.

Questions:

- What is the POC debounce period for repeated events on one farm/week?
- What counts as a material weather change for each weather-sensitive task?
- When no active approved schedule exists, should an impact event generate a
  proposal automatically or wait for owner request?

### 9. Owner Authority and Manual Edits

The POC currently has owner and worker roles only.

Questions:

- Confirm owner-only generation, regeneration, approval, rejection, and manual
  schedule modification.
- Which edits are permitted on a proposal: worker, time block, place, machinery,
  task priority, or task removal?
- Does an owner edit require FarmFlow to validate conflicts immediately?

Recommended POC answer: owner-only schedule authority; validate each manual
proposal edit before it can be approved.

### 10. Demonstration Scenarios and Tests

Which three scenarios prove FarmFlow works?

Recommended minimum set:

1. Routine egg collection is generated from approved rule and scheduled.
2. Weather makes a crop/machinery task unsuitable; FarmFlow moves it or gives an
   unscheduled reason.
3. Machinery breakdown or worker unavailability creates a new schedule proposal
   that preserves completed work and explains the change.

For each scenario, define the seed records, expected proposal, and expected
explanation. These become acceptance tests.

## Required Outputs

The scheduling team should return:

1. A recommended answer and representative example for each question.
2. A final ordered scoring policy and hard-constraint list.
3. Three seedable demonstration scenarios with expected output.
4. Any schema changes needed beyond the current `tasks`, `rules`, `schedules`,
   `scheduled_jobs`, `weather_forecasts`, and availability/resource tables.

## References

- [FarmFlow Scheduler Explainer](../client-notion/farmflow-scheduler-explainer.md)
- [FarmFlow Rescheduling](farmflow-rescheduling.md)
- [POC Logical Schema](../client-notion/erd-whiteboard-tables.md)
- [POC SQL DDL](../client-notion/erd-poc-schema.sql.md)
- [Client User Stories: US19-US26](../client-notion/user-stories.md)
