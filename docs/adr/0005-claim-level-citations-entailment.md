# ADR 0005: Claim-level citations with LLM-as-judge entailment

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-27 |
| Deciders | Assistant |
| Related | [`ARCHITECTURE.md`](../ARCHITECTURE.md) §2.5, §8 steps 11–12 |

## Context

Users treat cited answers as evidence. A marker that points to the wrong chunk is
worse than no citation — it laundered a guess into provenance. Generation can
attach markers to claims that the cited text does not support.

The POC already defines an `EntailmentPort` and a Verify stage after Generate.
Small NLI models are brittle on agricultural phrasing; a judge prompt through
`GenerationPort` is acceptable for POC scale if scores are logged.

## Decision

Verification operates at **claim granularity**, not document granularity:

1. Generation emits **inline markers** bound to a citation map.
2. Each marked factual claim is checked via **`EntailmentPort.entails(claim, evidence)`**.
3. POC adapter may use a **small NLI model or LLM-as-judge** prompt; choice is
   pinned in `VersionTuple.verifier_model_id`.
4. On failure: **drop the claim**, re-cite from another retrieved chunk, or
   downgrade to `PARTIAL` — never ship a marker whose chunk does not entail the claim.
5. Unmarked factual sentences are removed or labelled **general guidance** explicitly.

Entailment scores are stored in the citation list and audit record.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Claim-level entailment (NLI or judge)** | Catches unsupported markers; auditable scores | Latency (~700 ms budget); judge cost |
| Marker resolution only (no entailment) | Faster | Wrong-chunk citations pass |
| Document-level citation | Simple | Cannot localise unsupported sentences |
| Human verification gate | Highest trust | Blocks automation; not POC-viable |

## Consequences

### Positive

- `Unciteable claim` mandatory test becomes enforceable.
- Audit replay shows per-claim scores and verifier actions.
- Blended answers can downgrade one source class without refusing entirely.

### Negative

- Verifier outage forces explicit downgrade (`verification.degraded = true`).
- Judge prompts need redaction and stable rubric to limit variance.

## Reversal criteria

Reopen if entailment latency breaks blended p95 budget **and** resolution-only
verification achieves equal precision on the gold answer set (unlikely — requires
evidence ADR).

## Verification

- [ ] Verify stage runs for every `ANSWER`/`PARTIAL` response with markers.
- [ ] Citations include `entailment_score`; failures reflected in audit.
- [ ] Mandatory tests: citation resolution, unciteable claim handling.
- [ ] Degraded verifier path surfaces user-visible note and audit flag.
