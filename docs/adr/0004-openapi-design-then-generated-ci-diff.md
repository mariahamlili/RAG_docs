# ADR 0004: OpenAPI design-then-generated with CI diff

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-27 |
| Deciders | Assistant / UI / PL |
| Related | [`ARCHITECTURE.md`](../ARCHITECTURE.md) §2.1, [`openapi/openapi.design.yaml`](../openapi/openapi.design.yaml) |

## Context

Phase 0 requires cross-team agreement on REST shapes before serializers harden.
UI needs a stable client-generation input; backend needs freedom to implement with
DRF. Prior docs stated serializers are the runtime source of truth via
`drf-spectacular` — but negotiation cannot wait for every view to exist.

Without a design artifact, teams debate endpoints in chat and drift silently once
code lands.

## Decision

Maintain two OpenAPI artifacts:

1. **`docs/openapi/openapi.design.yaml`** — human-edited negotiation spec (Phase 0).
   Paths, operationIds, core schemas, and security schemes are authoritative for
   *intent* until implementation catches up.
2. **`docs/openapi/openapi.generated.yaml`** — emitted by `drf-spectacular` from DRF
   serializers at CI time.

**CI fails on unexpected diff** between design and generated specs (normalised:
paths, methods, operationIds, referenced response schemas). Additive implementation
detail in generated output is allowed only when the design file is updated in the
same PR. Breaking removals or renames require explicit design approval.

OpenAPI `info.version` (currently `0.4.0`) labels the contract; there is **no URL
version prefix** in the POC.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Design YAML + generated + CI diff** | Early UI client gen; visible drift; serializers stay SoT at runtime | Two files to maintain; diff tooling needed |
| Generated only | Single source | No pre-implementation contract for UI |
| Design YAML only (manual) | Full control | Guaranteed drift from running code |
| Shared TypeScript package | Strong typing | Violates contracts-first Django/DRF boundary |

## Consequences

### Positive

- UI can generate a client from `openapi.design.yaml` in Phase 0.
- Contract changes are reviewable as YAML diffs, not accidental serializer edits.
- Swagger UI serves generated schema; design file documents planned endpoints.

### Negative

- Contributors must update design YAML when adding/changing public operations.
- CI needs a normalisation step to avoid noisy false positives.

## Reversal criteria

Reopen if CI diff noise exceeds team tolerance after three phases **or** if FarmCore
adopts a monorepo shared-types package with explicit PL approval (would supersede
this ADR).

## Verification

- [ ] `openapi.design.yaml` present with Phase 0 paths and core schemas.
- [ ] CI job generates OpenAPI and diffs against design normal form.
- [ ] Phase 0 exit: UI generates client from design file without compile errors.
- [ ] `drf-spectacular` registered; generated artifact committed or CI-published.
