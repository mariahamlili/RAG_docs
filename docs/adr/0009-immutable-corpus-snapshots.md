# ADR 0009: Immutable corpus snapshots

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-27 |
| Deciders | Assistant / Documents |
| Related | [`ARCHITECTURE.md`](../ARCHITECTURE.md) §6 |

## Context

`RAG_docs` is a build-time pipeline; FarmCore is runtime. They must not share a
live database or ad-hoc file copies. Citations must resolve to the exact chunk text
the model saw months later — requiring content-addressed, immutable artifacts.

Corrections, re-chunking, or tier changes produce new content; mutating rows in
place would invalidate audit replay and `content_hash` provenance.

## Decision

Join pipeline and runtime through **immutable, versioned snapshot artifacts** only:

```text
snapshot_id = gov-<tier_set>-<YYYYMMDD>-<content_hash_12>
```

Published snapshot directory: `manifest.json`, `chunks.jsonl`, `parents.jsonl`,
`rejected.jsonl`, `checksums.txt`. Once activated, **rows are never updated in
place** — new build → new `snapshot_id` → atomic pointer flip in `corpus_snapshots`.

FarmCore never scrapes or re-derives gov content at runtime. `RAG_docs` never
connects to FarmCore DB. Import is idempotent, checksum-verified, transactional;
failed import leaves active snapshot untouched.

Every audit record pins the `snapshot_id` that served the request.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Immutable snapshot handoff** | Replayable; clear provenance; rollback = pointer flip | Re-import latency on corpus refresh |
| Live shared DB sync | Always fresh | Coupling; breaks citation immutability |
| Manual rsync without manifest | Fast to hack | No checksum/schema gate; audit useless |
| Embed in RAG_docs only | Simple pipeline | Runtime cannot query; wrong separation |

## Consequences

### Positive

- Citation `content_hash` matches stored chunk text for any historical `audit_id`.
- Two snapshots may coexist; rollback is pointer flip without re-embed rush.
- Rejected docs (`EMPTY_EXTRACTION`, etc.) are reviewed artifacts, not silent drops.

### Negative

- Corpus updates require full import + embed completion before activation.
- Schema changes (`chunks-v1` → v2) need bilateral agreement.

## Reversal criteria

Reopen if operational cadence requires sub-daily gov corpus updates **and** immutable
snapshots cannot meet freshness SLO — would require streaming ingest design and new ADR.

## Verification

- [ ] Snapshot builder produces content-addressed ID and checksum file.
- [ ] Import aborts on checksum/schema failure; active snapshot unchanged.
- [ ] Mandatory snapshot import test in CI.
- [ ] Gov rows carry non-null `snapshot_id`; audit records match active at request time.
