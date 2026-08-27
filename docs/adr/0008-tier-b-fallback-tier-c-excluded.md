# ADR 0008: Tier B fallback; Tier C excluded

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-27 |
| Deciders | Assistant / Documents |
| Related | [`ARCHITECTURE.md`](../ARCHITECTURE.md) §5.1, §6.1, §10 |

## Context

The gov corpus has three tiers: **A** (2,250 docs, default index), **B** (1,054,
lower curation confidence), **C** (1,268, archive-grade noise). Default retrieval
must prioritise precision; diluting Tier A with B increases false-confidence citations.

Some user questions are valid but narrowly missed by Tier A alone. A controlled
second pass can reduce false refusals without making Tier B ambient noise.

Tier C would dominate recall with peripheral pages and harm citation precision with
no demonstrated POC coverage gap.

## Decision

- **Default scope:** `gov_tier_a` only (`index_key = 'gov_tier_a'`).
- **Tier B:** enters only via a **single bounded fallback** after Tier A gate would
  refuse — re-query Tier A + B, re-rank once, label results lower confidence.
- **Tier C:** **not indexed** in POC. No snapshot import, no `index_key`, no silent
  inclusion path. Recovery requires explicit human opt-in and new ADR.

Tier B never appears in default-scope results or first-pass retrieval SQL.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A default; B one-pass fallback; C excluded** | Precision-first; measurable fallback | Latency on fallback; calibration needed |
| A+B in default index | Fewer refusals | Precision dilution; harder to audit |
| Index all tiers | Maximum recall | Tier C noise; trust failure |
| A only, no fallback | Simplest | Higher false refusal rate |

## Consequences

### Positive

- Fallback invocation audited (`retrieval.fallback`); SLO tracks false refusal vs precision.
- Snapshot IDs encode tier set: `gov-a-*` vs `gov-ab-*`.
- Tier C exclusion is explicit in `rejected.jsonl` / not-in-manifest.

### Negative

- Fallback doubles retrieve+rank latency on affected queries (single retry bound).
- Mis-calibrated gate may over-trigger fallback — monitor rate.

## Reversal criteria

Reopen Tier C only with reviewed coverage analysis showing a specific unanswered
question class **and** owner-approved cold-index design. Reopen default Tier B
inclusion only if fallback fails SLO and precision metrics on gold set.

## Verification

- [ ] Default `RetrievalScope.logical_indexes == {'gov_tier_a'}` for gov queries.
- [ ] Test: Tier B chunk never returned when fallback conditions not met.
- [ ] Tier B results carry lower-confidence indicator in response and audit.
- [ ] No Tier C rows in `document_chunks`; import rejects Tier C manifest entries.
