# ADR 0010: Registries, not frameworks

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-27 |
| Deciders | Assistant / PL |
| Related | [`ARCHITECTURE.md`](../ARCHITECTURE.md) §2.2, §2.3 |

## Context

The orchestrator varies by intent: different tools, indexes, refusal codes, and
prompt templates. A naive approach scatters `if intent == …` branches across stages,
making behaviour untestable and audit opaque.

Ports already abstract external providers. Internal variability still needs a
lookup mechanism. A generic plug-in framework (dynamic loading, plugin discovery,
lifecycle hooks) exceeds POC needs and hides control flow from review.

## Decision

Use **four explicit registries** — each a versioned map from stable key to typed
entry plus documentation:

| Registry | Key | Consumed by |
|---|---|---|
| Tool | `tool_name` | Plan, Tools stages |
| Index | `index_key` | Admit → `RetrievalScope` |
| Refusal | `refusal_code` | Gate, error surfaces |
| Prompt | `prompt_id` | Generate |

Adding behaviour = **registry entry + test + doc string** — not a new framework
hook. Registries export a `REGISTRY_VERSION` constant included in `VersionTuple`
where applicable (`tool_registry_version`, prompt ids).

**Do not build:** generic plugin loaders, decorator-based auto-discovery, or
reflective tool registration. One port, one adapter applies to external deps; registries
apply to internal variation.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Static registries + completeness tests** | Explicit; grep-friendly; auditable versions | Manual registration |
| Giant if/elif chains | No indirection | Unmaintainable; untested branches |
| Plugin framework | Extensible | Opaque; over-engineered for POC |
| Config-only YAML without code | Non-dev editable | Loses type checks; drift from implementation |

## Consequences

### Positive

- `Registry completeness` mandatory test gates merge.
- Plan stage tool list is finite and known before generation (§5.2).
- Refusal taxonomy is data-driven with consistent user-facing templates.

### Negative

- New tool requires code change in registry module (acceptable for POC velocity).
- Registry version bumps must be deliberate for A/B evaluation.

## Reversal criteria

Reopen if registry count exceeds maintainability (e.g. >40 tools) **and** a typed
plugin boundary is designed with explicit security review — not before.

## Verification

- [ ] Four registry modules scaffolded with version constants.
- [ ] Completeness test enumerates every entry; CI fails on orphan keys.
- [ ] Orchestrator Plan stage selects only from tool registry filtered by role.
- [ ] No `importlib`/`__subclasses__` plugin discovery in assistant app.
