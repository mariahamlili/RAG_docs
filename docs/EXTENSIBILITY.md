# FarmCore Extensibility — Assistant & Knowledge Track

Extension rules for the FarmCore assistant and document-retrieval POC. This
document defines the allowed extension points, the abstraction budget, and the
decision process for adding new behaviour without building a premature plug-in
framework.

## Document Metadata

| Field | Value |
|---|---|
| Title | FarmCore Extensibility — Assistant & Knowledge Track |
| Status | **Accepted** |
| Date | 2026-08-27 |
| Owning team | Assistant / Documents |
| Companion records | [`ARCHITECTURE.md`](ARCHITECTURE.md), [`API.md`](API.md), [`PLAN.md`](PLAN.md) |
| Guiding constraint | **No premature plug-in framework.** A port is an interface plus one concrete adapter. |

---

## 1. Extension Philosophy

FarmCore is a modular monolith, not a platform. Extensibility is deliberate and
bounded:

| Principle | Meaning |
|---|---|
| Contracts-first | Every cross-module surface is a declared contract before it is an implementation |
| Registries over conditionals | New behaviour is a registry entry plus a test, never an `if` branch in the orchestrator |
| One port, one adapter | Ports are swappable; call sites are not rewritten when a provider changes |
| No generic plug-in framework | No dynamic class loading, no plug-in discovery, no third-party extension SDK in the POC |
| Fail loud | A producer that cannot satisfy a schema validator fails rather than emitting partial records |

When a proposed extension does not fit an existing port or registry, use the
decision table in §8 before writing code.

---

## 2. Protocols (≤3 Methods Each)

External dependencies are reached through narrow Python protocols (structural
typing or ABC) owned by one Django app. Each protocol exposes **at most three
methods** in the POC. Additional capability requires a new protocol or an ADR
to widen an existing one.

### 2.1 EmbeddingPort

**Owner:** `assistant`

| Method | Signature | Purpose |
|---|---|---|
| `embed_documents` | `(texts: list[str]) -> list[list[float]]` | Batch embed for ingestion |
| `embed_query` | `(text: str) -> list[float]` | Single query embedding |
| `model_info` | `() -> EmbeddingModelInfo` | Dimension, model id, revision for version tuple |

**POC adapter:** Local/open-weights `bge-large-en-v1.5` (1024 dimensions, pinned
before pgvector column migration).

**Rules:**

- Provider SDK types never escape the adapter.
- Dimension is pinned before schema migration; a change requires full re-embed.
- Retries and timeouts live in the adapter only.

### 2.2 GenerationPort

**Owner:** `assistant`

| Method | Signature | Purpose |
|---|---|---|
| `generate` | `(prompt: str, *, system: str \| None, max_tokens: int) -> str` | Unstructured generation |
| `generate_structured` | `(prompt: str, schema: type[T], *, system: str \| None) -> T` | Structured output (answers, blocks) |
| `model_info` | `() -> GenerationModelInfo` | Provider, model, revision for version tuple |

**POC adapter:** Team-selected LLM behind an OpenAI-compatible or provider-native
adapter.

**Rules:**

- Credentials confined to adapter configuration.
- Prompt and payload redacted in logs and audit records.

### 2.3 RerankPort

**Owner:** `assistant`

| Method | Signature | Purpose |
|---|---|---|
| `rerank` | `(query: str, candidates: list[Candidate]) -> list[ScoredCandidate]` | Precision reordering |
| `model_info` | `() -> RerankModelInfo` | Model id for version tuple |
| `healthcheck` | `() -> bool` | Probe for graceful degradation |

**POC adapter:** `bge-reranker-v2-m3`. Degrades to identity ordering on failure.

### 2.4 EntailmentPort

**Owner:** `assistant`

| Method | Signature | Purpose |
|---|---|---|
| `entails` | `(claim: str, evidence: str) -> EntailmentResult` | Binary entailment + score |
| `entails_batch` | `(pairs: list[tuple[str, str]]) -> list[EntailmentResult]` | Batched verification |
| `model_info` | `() -> VerifierModelInfo` | Model id for version tuple |

**POC adapter:** DeBERTa-MNLI or judge prompt through `GenerationPort`.

### 2.5 ExtractionPort

**Owner:** `documents`

| Method | Signature | Purpose |
|---|---|---|
| `extract_text` | `(file_bytes: bytes, mime: str) -> ExtractionResult` | PDF/text extraction |
| `extract_tables` | `(file_bytes: bytes, mime: str) -> list[TableResult]` | Table extraction with captions |
| `tool_info` | `() -> ExtractionToolInfo` | Tool version for manifest |

**POC adapter:** PyMuPDF / pdfplumber. No OCR in POC.

### 2.6 ObjectStorePort

**Owner:** `documents`

| Method | Signature | Purpose |
|---|---|---|
| `put` | `(key: str, data: bytes, *, content_type: str) -> StoredObject` | Upload original bytes |
| `get` | `(key: str) -> bytes` | Read original bytes |
| `presign` | `(key: str, *, expires_seconds: int) -> str` | Time-limited download URL |

**POC adapter:** MinIO (S3-compatible).

### 2.7 WeatherPort

**Owner:** `farms`

| Method | Signature | Purpose |
|---|---|---|
| `fetch_forecast` | `(point: GeoPoint, days: int) -> ForecastSnapshot` | Normalised forecast fetch |
| `provider_info` | `() -> WeatherProviderInfo` | Provider name for citations |
| `healthcheck` | `() -> bool` | Probe for staleness handling |

**POC adapter:** Free forecast provider (Open-Meteo or equivalent).

### 2.8 Protocol widening rule

Adding a fourth method to any protocol requires:

1. An ADR in `docs/adr/` explaining why three methods are insufficient.
2. Updates to all adapters (including test fixtures).
3. A version bump on the affected registry or schema.

Default answer to "should we add another method?" is **no** — split into a new
protocol instead.

---

## 3. Tool Registry

The tool registry is the extension point for assistant capabilities that read
structured farm data or produce inert drafts.

### 3.1 Registry entry shape

```python
@dataclass(frozen=True)
class ToolEntry:
    tool_name: str                          # stable snake_case key
    version: str                            # semver within registry version
    callable: Callable[[ToolContext, dict], ToolResult]
    input_schema: type[BaseModel]         # Pydantic or DRF serializer
    output_schema: type[BaseModel]
    tool_class: Literal["read", "draft"]
    required_role: Literal["owner", "worker"]
    audit_verbosity: Literal["summary", "full"]
    description: str                        # one paragraph for capabilities manifest
```

### 3.2 Registration rules

| Rule | Detail |
|---|---|
| Key stability | `tool_name` never renames; deprecate and add a successor |
| Version constant | `tool_registry_version` bumps when any entry changes |
| Lookup, not branch | Orchestrator selects tools by intent + role from the registry |
| Scope re-derivation | Every tool rebuilds scope from `ToolContext.principal`; never trusts model-supplied `farm_id` |
| Draft class | `draft` tools produce inert records; only human confirmation writes active data |
| Test requirement | Every entry has a unit test and appears in the registry completeness test |

### 3.3 POC tool inventory (initial)

| tool_name | class | required_role | Purpose |
|---|---|---|---|
| `get_farm_context` | read | worker | Farm name, places summary, role |
| `list_tasks` | read | worker | Assigned/open tasks |
| `get_approved_rules` | read | worker | Active rules and templates |
| `get_schedule_summary` | read | worker | Current approved schedule snapshot |
| `list_alerts` | read | worker | Unread alerts for principal |
| `get_weather_snapshot` | read | worker | Cached forecast with staleness |
| `lookup_current_weather` | read | worker | Controlled live weather fetch |
| `search_tenant_documents` | read | worker | Authorised document search (metadata) |
| `draft_task` | draft | owner | Propose a task (inert until confirmed) |
| `draft_task_update` | draft | worker | Propose task progress update |
| `request_schedule_proposal` | draft | owner | Queue FarmFlow proposal (no placement) |

Adding a tool: registry entry + input/output schemas + test + one line in
`GET /api/capabilities`. No orchestrator `if tool_name == ...` branches.

### 3.4 What is not a tool

| Excluded | Served by |
|---|---|
| Raw retrieval | Retrieval stage pipeline (§4) |
| Generation | `GenerationPort` |
| Entailment | `EntailmentPort` |
| Document upload/processing | Documents API and RQ jobs |
| FarmFlow placement | Scheduling app (deterministic) |

---

## 4. Retrieval Stage Pipeline

Retrieval is a fixed ordered pipeline, not a plug-in chain. Stages are
individually testable, timed, and audited. Extension happens by **configuration
within stages**, not by inserting arbitrary stage implementations.

### 4.1 Stage sequence

```text
Query in + RetrievalScope
    │
    ▼
[1] query_rewrite        ── optional LLM rewrite, HyDE for sparse
    │
    ▼
[2] dense_recall         ── pgvector top-50 inside scope predicate
    │
    ▼
[3] lexical_recall       ── Postgres FTS top-50 inside scope predicate
    │
    ▼
[4] rrf_fusion           ── Reciprocal Rank Fusion merge
    │
    ▼
[5] metadata_filter      ── doc_state, valid_from/to, allowed_document_ids
    │
    ▼
[6] rerank               ── cross-encoder top-50 → top-8
    │
    ▼
[7] mmr                  ── diversity filter
    │
    ▼
[8] parent_expansion     ── small-to-big: child match → parent text
    │
    ▼
[9] context_pack         ── dedup by content_hash, token budget, source-class floors
    │
    ▼
Final chunk set → Gate
```

### 4.2 Scope rules (non-negotiable)

| Rule | Enforcement |
|---|---|
| Every call takes `RetrievalScope` | No bare query string entry points |
| Scope built only in Admit | Model cannot influence scope fields |
| `tenant_doc` and `gov_*` never mixed in one scope | Blended queries = two calls |
| Predicates in SQL | `farm_id`, `index_key`, `snapshot_id`, `allowed_document_ids` are `WHERE` clauses |
| Tier B is a second pass | Not a widening of the first scope |

### 4.3 Configurable parameters (hot config)

Stored in `retrieval_config_version`:

| Parameter | Default (POC) | Extension mechanism |
|---|---|---|
| `dense_top_k` | 50 | Config bump, not new stage |
| `lexical_top_k` | 50 | Config bump |
| `rrf_k` | 60 | Config bump |
| `rrf_dense_weight` | 1.0 | Config bump |
| `rrf_lexical_weight` | 1.0 | Config bump |
| `rerank_top_k` | 8 | Config bump |
| `mmr_lambda` | 0.7 | Config bump |
| `context_token_budget` | 6000 | Config bump |
| `tier_b_fallback_enabled` | true (Phase 8+) | Feature flag |
| `confidence_threshold` | provisional | Calibrated in Phase 7 |

Changing any parameter bumps `retrieval_config_version` and requires regression
suite comparison when Phase 7+ is active.

### 4.4 Adding a new retrieval stage

**Default: do not.** The nine stages above are the POC pipeline. Before adding a
tenth stage:

1. Complete the decision table (§8) with category **New retrieval stage**.
2. Demonstrate the existing pipeline cannot achieve the goal via config change.
3. Land an ADR, update audit funnel schema, update `GET /api/capabilities`
   `retrieval_stages`, and add stage-level tests.

Deferred stages (Phase 11+ triggers only):

| Stage | Trigger |
|---|---|
| `query_decomposition` | Multi-part coverage materially worse on gold set |
| `self_query_filter` | Users repeatedly express ignored metadata constraints |
| `iterative_retrieval` | Multi-hop failures fixable by bounded 2–3 iteration loop |

---

## 5. Provider Adapters

### 5.1 Adapter inventory

| Port | POC adapter | Upgrade path |
|---|---|---|
| Dense retrieval | **pgvector** (HNSW partial indexes) | Qdrant (Phase 11+, evidence-gated) |
| Lexical retrieval | **Postgres FTS** (`tsvector` + GIN) | OpenSearch/Elasticsearch BM25 (Phase 11+) |
| Embeddings | **bge-large-en-v1.5** (local/open-weights) | Same model family revision pin, or new model + re-embed |
| Reranking | **bge-reranker-v2-m3** | Cohere Rerank or larger cross-encoder |
| Entailment | **DeBERTa-MNLI** | LLM-as-judge through `GenerationPort` |
| Extraction | **PyMuPDF + pdfplumber** | OCR adapter (Phase 11+) |
| Object store | **MinIO** | S3, R2, etc. |
| Generation | **Team-selected LLM** | Any provider behind `GenerationPort` |
| Weather | **Open-Meteo or equivalent** | Any provider behind `WeatherPort` |

### 5.2 pgvector adapter

| Property | Detail |
|---|---|
| Table | `document_chunks.embedding vector(<dim>)` |
| Indexes | Partial HNSW: gov (`farm_id IS NULL`) and tenant (`farm_id IS NOT NULL`) |
| Scope predicate | Same query plan as similarity search — tenant filter is never post-hoc |
| Degradation | Query error → FTS-only recall, flagged in audit |

### 5.3 Postgres FTS adapter

| Property | Detail |
|---|---|
| Column | `text_search tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED` |
| Indexes | Partial GIN matching dense partial indexes |
| Tuning | `english` config; custom dictionary deferred |
| Degradation | N/A — if Postgres is down, entire request fails |

### 5.4 BGE embedding adapter

| Property | Detail |
|---|---|
| Model | `BAAI/bge-large-en-v1.5` |
| Dimension | 1024 (pinned before migration) |
| Query prefix | `Represent this sentence for searching relevant passages: ` |
| Document prefix | None (passage embedding) |
| Batch size | Configurable in adapter; default 32 |

### 5.5 Swapping an adapter

1. Implement new adapter satisfying the existing protocol (≤3 methods).
2. Register in Django settings / dependency injection — one line change at the
   composition root.
3. Run mandatory tests plus provider-specific integration test.
4. Bump the relevant version in `VersionTuple` (`embedding_model_id`,
   `reranker_model_id`, etc.).
5. If dimension or index structure changes, follow reindex procedure in
   [`API.md`](API.md) §7.

No call-site rewrites. No orchestrator changes.

---

## 6. Named Indexes

Logical indexes live on one physical `document_chunks` table. Separation is by
`index_key` and mandatory query predicates.

### 6.1 Index registry entry shape

```python
@dataclass(frozen=True)
class IndexEntry:
    index_key: str
    description: str
    tier: Literal["A", "B"] | None       # gov only
    default_scope_eligible: bool          # False for gov_tier_b
    farm_id_null: bool                    # True for gov, False for tenant
    freshness_policy: Literal["snapshot", "continuous"]
    registry_version: str
```

### 6.2 Registered indexes (POC)

| index_key | tier | default_scope | farm_id | freshness | document count |
|---|---|---|---|---|---|
| `gov_tier_a` | A | Yes | NULL | snapshot | 2,250 |
| `gov_tier_b` | B | No (fallback only) | NULL | snapshot | 1,054 |
| `tenant_doc` | — | Yes (when farm has docs) | NOT NULL | continuous | per farm |

Tier C (1,268 documents) is **not registered**. It is excluded entirely.

### 6.3 Adding a named index

Requires:

1. Index registry entry with test.
2. Partial HNSW and GIN indexes matching the `index_key` predicate.
3. `RetrievalScope` validation update if eligibility rules are novel.
4. Snapshot or ingestion path if gov-class.
5. ADR if the index introduces a new access pattern.
6. Update `GET /api/capabilities` and corpus admin endpoints.

Cold Tier C index (Phase 11+): separate `index_key = 'gov_tier_c'`, explicit
human opt-in in UI, never in default scope.

---

## 7. Audit Schema Versioning

Audit events are append-only with an explicit schema version on every record.

### 7.1 Current schema: `audit-v1`

Top-level envelope:

```json
{
  "event_id": "uuid",
  "audit_id": "uuid",
  "event_type": "string",
  "schema_version": "audit-v1",
  "timestamp": "ISO8601",
  "actor_user_id": "uuid",
  "farm_id": "uuid | null",
  "request_id": "uuid",
  "payload": { }
}
```

`assistant.message.completed` payload fields (minimum):

| Field | Purpose |
|---|---|
| `raw_query` | User message |
| `rewritten_query` | Post-Understand query |
| `retrieval_stages` | Funnel with candidate IDs and scores per stage |
| `groundedness_decision` | `ANSWER` \| `PARTIAL` \| `REFUSE` |
| `refusal_reason` | Code from refusal registry |
| `tools_invoked` | Tool name, args summary, status, latency |
| `citations` | Claim, chunk_id, entailment_score |
| `version_tuple` | Full `VersionTuple` (§ARCHITECTURE.md §11) |
| `latency_ms` | Per-stage timing |

### 7.2 Versioning rules

| Rule | Detail |
|---|---|
| Additive changes | New optional payload fields within `audit-v1` — no version bump |
| Breaking changes | New `schema_version` (`audit-v2`); both versions readable indefinitely |
| Migration | Export tools must emit requested version or latest with conversion |
| Immutability | No updates or deletes for POC lifetime |
| Redaction | No raw document bytes, no secrets, no full model prompts |
| Failure | Audit write failure fails the request — no degradation |

### 7.3 Event types (extensible list)

| event_type | Emitted by |
|---|---|
| `assistant.message.completed` | Orchestrator audit stage |
| `document.uploaded` | Documents upload handler |
| `document.archived` | Archive endpoint |
| `document.processing.failed` | RQ extraction job |
| `candidate.approved` | Candidate approval |
| `candidate.rejected` | Candidate rejection |
| `rule_candidate.approved` | Rule candidate approval |
| `corpus.snapshot.imported` | Snapshot import job |
| `corpus.snapshot.activated` | Snapshot activation |
| `audit.export.requested` | Audit export |
| `retrieval.replay.executed` | Debug replay (when `FEATURE_RETRIEVAL_DEBUG`) |

Adding an event type: define payload schema, add to export filters, document in
[`API.md`](API.md), add validator test. No change to `schema_version` if payload
fits existing envelope.

---

## 8. Extension Decision Table

Use this table before every proposed extension. The default column is the POC
answer.

| You want to… | First check | POC answer | If yes, do this | If no, stop and… |
|---|---|---|---|---|
| Add a new tool | Tool registry | Register entry | Schema + test + capabilities update | Use an existing tool or retrieval |
| Change embedding model | `EmbeddingPort` adapter | Swap adapter | Re-embed all chunks; bump `embedding_model_id` | Tune retrieval config first |
| Add a retrieval stage | Stage pipeline | **Reject** unless ADR | ADR + audit schema + tests | Change config within existing stages |
| Add a fourth protocol method | Protocol budget | **Reject** unless ADR | ADR + adapter updates | Split into a new protocol |
| Add a new logical index | Index registry | ADR if non-obvious | Registry + partial indexes + scope rules | Use existing index with better chunking |
| Add a new refusal reason | Refusal registry | Register entry | Template + test + API `refusal_codes` | Map to existing code |
| Add a new prompt template | Prompt registry | Register entry | Version bump + eval regression | Edit existing template version |
| Support a new document format | `ExtractionPort` adapter | **Defer** OCR/DOCX to Phase 11+ | ADR when trigger fires | Reject upload with clear error |
| Expose a dynamic plug-in API | Framework budget | **Reject** | — | Use ports and registries |
| Let the model choose tools | Orchestrator design | **Defer** Phase 11+ | ADR + audit loop design | Keep tools-before-generation |
| Store chat history in vector index | §10 ARCHITECTURE | **Reject** | — | Pass conversation context to Understand only |
| Mix tenant and gov in one retrieval call | Scope rules | **Reject** | Dual call + assembly merge | Build two scopes |
| Filter retrieval results in Python | §2.4 ARCHITECTURE | **Reject** | Move predicate to SQL | Fix scope construction |
| Skip audit on degraded path | Audit rules | **Reject** | Fail request or record degradation | Never silent skip |
| Add URL API version prefix | API conventions | **Reject** for POC | — | Use OpenAPI release version label |
| Build a generic rules engine | Framework budget | **Reject** | — | Register specific tools and stages |

### 8.1 Reconciliation with "no premature plug-in framework"

| What people often call "plug-ins" | What FarmCore does instead |
|---|---|
| Dynamic tool discovery | Static tool registry with version constant |
| Pipeline plug-in chain | Fixed stage sequence with hot config |
| Provider plug-in SDK | Port interface + one adapter per provider |
| Index plug-in loader | Named index registry + partial DB indexes |
| Prompt plug-in marketplace | Prompt registry with versioned templates |
| Third-party extensions | Not supported in POC |

The abstraction budget for the POC is: **seven ports, four registries, nine
retrieval stages, three logical indexes.** Anything beyond that is a Phase 11+
item with a written trigger in [`PLAN.md`](PLAN.md), or it requires an ADR that
explicitly expands the budget.

---

## 9. Testing Extensions

Every extension ships with:

| Requirement | Test type |
|---|---|
| Registry entry reachable | `test_registry_completeness` |
| Schema valid | Validator unit test |
| Scope integrity preserved | Cross-farm leak test |
| Audit event emitted | Audit completeness test |
| Version tuple updated | Version pinning test |
| No post-hoc filtering | Static SQL predicate check |
| Idempotent jobs | Rerun test for background work |

Extensions that fail any mandatory test from `ARCHITECTURE.md` §13 do not merge.

---

## 10. Related Records

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — principles §2, retrieval §7, version tuple §11
- [`API.md`](API.md) — HTTP contracts and capabilities manifest
- [`PLAN.md`](PLAN.md) — phase gates and deferred triggers
- [`MAPPING.md`](MAPPING.md) — DesignDoc traceability
- `DesignDoc.md` — general multi-stage RAG pattern this track specialises
