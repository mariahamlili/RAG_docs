# State-of-the-Art RAG System Design Plan
### Multi-Stage Retrieval · Audit Trails · Citations · Refusals
### (with decision rationale: the easy way, why it falls short, and example cases)

| Field | Value |
|---|---|
| Status | **Aligned with FarmCore POC** — feasible within the 4-week CAI sprint |
| Companion docs | [`CAI_SPRINT_PLAN.md`](../CAI_SPRINT_PLAN.md) · [`ARCHITECTURE.md`](../ARCHITECTURE.md) · [`PLAN.md`](../PLAN.md) · [`MAPPING.md`](../MAPPING.md) |
| Last updated | 2026-08-28 |

## Feasibility (short answer: yes)

This design is **doable** for the FarmCore gov-corpus POC. The repo already has:

- **Week 1 done** — corpus ingest, Tier A filters, boilerplate strip, quality manifests (CAI-014–021).
- **Week 1 foundations** — Django apps, ports/registries, `chunks-v1` schema, stub API, audit models (CAI-001–011).
- **Accepted stack** — pgvector + Postgres FTS in one database (ADR-0001, ADR-0002); custom pipeline, not LlamaIndex.

What is **not** in the 4-week POC (deferred to Phase 11+ per `MAPPING.md` §6): OpenSearch/Qdrant, agentic retrieval loops, query decomposition, OCR, HyDE by default. The build order below matches the CAI sprint critical path; agentic features are explicitly last.

**Main risks (manageable):** reranker latency (CAI-044, CAI-047), over-refusal until gate calibration (CAI-065), chunker quality (CAI-029). None block the architecture — they are tuning and test tickets.

---

## 1. High-Level Architecture

```
User Query
   │
   ▼
[Query Understanding] → rewrite, decompose, classify intent
   │
   ▼
[Multi-Stage Retrieval]
   ├─ Stage 1: Hybrid Retrieval (dense + sparse)
   ├─ Stage 2: Metadata / Filter Pre-narrowing
   ├─ Stage 3: Cross-Encoder Reranking
   └─ Stage 4: Diversity / Redundancy Filtering (MMR)
   │
   ▼
[Context Assembly] → chunk stitching, dedup, token budget packing
   │
   ▼
[Groundedness Gate] → decide: answer / partial / refuse
   │
   ▼
[Generation with Citations]
   │
   ▼
[Post-hoc Verification] → citation check, hallucination check
   │
   ▼
[Audit Log] ← every stage above writes structured events here
   │
   ▼
Response + Citations + Confidence + Audit ID
```

> **Why this shape at all?** The easy version of a RAG system is: embed chunks → cosine-similarity top-k → stuff into prompt → generate. That's ~20 lines of code and it demos well. It breaks in production because each of the five things this pipeline adds — recall, precision, groundedness, provenance, and auditability — fails independently, and the naive version has no mechanism to catch any of them. The rest of this doc justifies each addition on its own terms so nothing here is cargo-culted.

---

## 2. Ingestion & Indexing

### Chunking

- Structure-aware chunking (headers, sections, tables kept intact) instead of fixed-size sliding windows.
- **300–500 tokens** per chunk, ~10–15% overlap within section (CAI-022; aligns with `chunks-v1` validator max 500).
- Parent-child hierarchy: small chunks for retrieval precision, larger parent context for generation ("small-to-big retrieval").
- Tables/figures: extract separately, summarize with a caption chunk, keep raw table linked by ID.

**Why not the easy way (fixed-size sliding window)?**
Fixed-size chunking (e.g., "every 500 characters") is a single `for` loop over the raw text — trivial to implement. The problem is it chunks blind to document structure, so it routinely slices a table in half, separates a heading from the paragraph it introduces, or splits a clause across two chunks so neither one is individually retrievable.

- *Example:* A policy doc has a section "Refund Eligibility" followed by a table of conditions. A fixed 500-char window cuts the table after row 3. A user asks "am I eligible for a refund after 60 days?" — the retrieved chunk contains rows 1–3 but the 60-day row is in the next chunk, which scores lower and gets dropped. The naive pipeline confidently answers using incomplete rows. Structure-aware chunking keeps the whole table (or a summarized reference to it) as one retrievable unit, so this failure mode doesn't happen.

**Why parent-child (small-to-big) instead of one chunk size for everything?**
Small chunks retrieve precisely (a 200-token chunk matches a specific query closely) but generate poorly (not enough surrounding context for the model to reason correctly). Large chunks generate well but dilute the embedding, so precise queries retrieve worse. Using one size is an either/or trade-off; small-to-big just uses each size for what it's good at.

- *Example:* Query: "What's the max file size for uploads?" A small child chunk containing just that sentence retrieves at rank 1. But the model needs the surrounding paragraph (which explains an exception for enterprise plans) to answer correctly — that's pulled in via the parent, not re-embedded and re-searched.

### Metadata & the immutable content store

- Attach `doc_id, source_uri, version_hash, chunk_id, section_path, page_number, created_at, access_level, doc_type` to every chunk.
- Keep an immutable content-addressed store (hash → original chunk text).

**Why bother, when you could just store text + a doc name?**
The easy version stores `{text, doc_name}`. It works until someone asks "why did the bot say X" six weeks later, or a document gets edited and the old citation now points to different content. `version_hash` and the immutable store exist specifically so a citation always resolves to the exact bytes that were actually retrieved, even after the source doc has since changed.

- *Example:* A company updates its expense policy on March 1. On Feb 20 the bot answered a question citing the old $50 meal limit. Without a version hash, that citation link now shows the *current* $75 limit when someone audits it — looking like the bot fabricated the answer. With content-addressing, the citation resolves to the Feb-20 snapshot, and the audit shows the bot was correct *at the time*.

---

## 3. Multi-Stage Retrieval

| Stage | Purpose | Technique |
|---|---|---|
| 1. Query rewriting | Handle ambiguity, coreference, multi-intent | LLM query rewrite + HyDE for sparse queries |
| 2. Recall (hybrid) | Cast a wide, high-recall net | Dense top-50 + BM25 top-50, merged via RRF |
| 3. Metadata filtering | Enforce scope/permissions before ranking | Pre-/post-filter on access_level, date, doc type |
| 4. Reranking | High-precision reordering | Cross-encoder on top-50 → top-8 |
| 5. Diversity control | Avoid redundant near-duplicate chunks | MMR |
| 6. Context packing | Fit token budget, preserve provenance | Greedy pack by relevance, keep chunk-doc mapping |

**Why not just dense retrieval alone?**
Dense embedding search *is* the easy path — one model, one cosine similarity, done. It's genuinely good at semantic/paraphrase matches but weak on exact tokens: IDs, product codes, error codes, acronyms, names — anything where the literal string matters more than the meaning.

- *Example:* Query: "what does error E-4471 mean?" A dense embedding model may treat "E-4471" as noise and instead retrieve chunks about generic error handling. BM25 (sparse/keyword) matches the literal token "E-4471" and finds the exact chunk. Hybrid retrieval (dense + sparse, merged with Reciprocal Rank Fusion) gets both: paraphrase queries *and* exact-match queries, without you having to guess in advance which kind a user will ask.

**Why add a reranker instead of just trusting the retriever's top-k?**
Embedding similarity and BM25 scores are both *cheap approximations* — fast enough to search millions of chunks, but they don't jointly read the query and the chunk together, so they miss subtler relevance signals. A cross-encoder reranker is expensive (can't run it over the whole corpus) but accurate, so the fix is: use the cheap method to get a wide net (top-50), then the expensive method to sort just those 50 well.

- *Example:* Query: "How do I cancel my subscription without losing my data?" Top dense-retrieval hits might include three chunks that are all "about cancellation" in a generic sense, but only one specifically addresses data retention on cancellation. A cross-encoder, reading query and chunk together, ranks that specific chunk to #1 even though its raw embedding similarity wasn't the highest. This is the step the document already calls "highest-leverage" — skipping it is the single most common reason a working RAG demo underperforms in production.

**Why MMR (diversity filtering) on top of reranking?**
Without it, the top-k can be five near-duplicate paraphrases of the same paragraph (common when a doc set has multiple versions of similar policies), which wastes context budget and gives the illusion of "5 sources" that are really 1 fact repeated.

- *Example:* A company has a global HR handbook and three regional addenda that all restate the base vacation policy with minor wording differences. A query about vacation days could retrieve all four restatements as top-4, leaving no room in the context window for the one addendum that actually differs (e.g., a regional public-holiday rule). MMR penalizes redundancy so the fourth slot goes to that different, useful chunk instead of a fourth copy of the same fact.

---

## 4. Groundedness Gate & Refusals

Decision policy:
- High confidence + full coverage → answer normally with citations.
- Partial coverage → answer only the covered part, state what's missing.
- Low confidence / no relevant chunks / permission-filtered → refuse, with reason code (`NO_RELEVANT_CONTEXT`, `INSUFFICIENT_COVERAGE`, `CONFLICTING_SOURCES`, `OUT_OF_SCOPE`, `ACCESS_DENIED`).

**Why not just always answer with whatever was retrieved?**
The easy path — always generate an answer from whatever top-k came back — is exactly what makes RAG systems produce confident, well-cited-*looking* wrong answers. If nothing relevant was retrieved, the LLM will still write a fluent paragraph, because generation and "knowing you don't know" are separate capabilities that the naive pipeline never checks. The groundedness gate exists to make refusal a first-class output, not a failure mode.

- *Example:* A user asks a medical-imaging RAG system, "what's the recommended DVF regularization weight for lung tumors near the diaphragm?" If the corpus only has general 4DCT motion papers and nothing diaphragm-specific, the naive system will still synthesize a plausible-sounding number by blending nearby chunks — which is dangerous in a domain where a fabricated parameter could feed into a real workflow. The groundedness gate catches "coverage is partial" and returns "general DVF regularization guidance is covered; diaphragm-adjacent tumor motion isn't specifically addressed in the indexed literature" instead of guessing.

**Why distinguish refusal *reasons* instead of one generic "I don't know"?**
A single refusal message is easy to write but useless for the person asking (they don't know whether to rephrase, request access, or give up) and useless for you (you can't tell from logs whether your corpus has a coverage gap or your access control is too aggressive).

- *Example:* `ACCESS_DENIED` vs `NO_RELEVANT_CONTEXT` look identical from the outside ("no answer") but require completely different fixes — one means "the answer exists, request access," the other means "go index this topic." Tracking these separately in the audit log turns refusals from dead ends into a prioritized backlog of what to index or fix next.

---

## 5. Citations

- Cite at claim granularity (inline markers), not one source list at the end.
- Post-hoc entailment check: does the cited chunk actually support the claim?

**Why not just list "sources used" at the bottom of the answer?**
End-of-response source dumps are the easy default (most chat UIs do this) but they don't tell the reader *which* sentence came from *which* source, so the reader can't actually verify any individual claim — they'd have to re-read every source in full to check. Claim-level citation makes each sentence independently checkable.

- *Example:* An answer has three sentences: one from Source A, one from Source B, and one that's actually the model paraphrasing/inferring without support. A bottom-of-page "Sources: A, B" hides the third sentence's lack of grounding entirely — it looks equally supported. Inline citation ([1], [2]) immediately exposes that the third sentence has no marker, which is precisely the failure the entailment check is designed to catch before the answer even ships.

**Why run an entailment check instead of trusting that "a citation was attached" means it's correct?**
LLMs can attach a citation marker to a claim it actually got from parametric memory, not from the cited chunk — the marker is a generation artifact, not proof. Entailment verification (does chunk X actually logically support claim Y?) closes that gap.

- *Example:* The model writes "the device has an IP67 rating [3]" and chunk 3 is real and about that device, but chunk 3 only discusses battery life, not water resistance. The citation *looks* legitimate (real chunk, right document) but doesn't entail the claim. An NLI/LLM-judge entailment pass flags this and either drops the claim, re-cites, or downgrades that sentence to a refusal — catching what the doc calls the most common RAG failure mode: correct-sounding answer, wrong or unsupported citation.

---

## 6. Audit System

Log per request: raw query, rewritten query, retrieval candidates per stage, groundedness decision, citations with entailment scores, model/config versions, latency.

**Why not just log the final prompt and response, like a normal app log?**
Logging input/output is the easy version and is enough to know *that* something went wrong, but not *why*. If retrieval config, embedding model, or reranker changes over time, a prompt+response log can't tell you whether a bad answer was caused by bad retrieval, a bad rerank, or bad generation — you'd be debugging blind.

- *Example:* Three weeks after switching embedding models, someone in Legal asks why the system gave a wrong answer to a compliance question last Tuesday. A prompt+response log only shows "here's what it said." A structured, stage-by-stage audit log with `retrieval_config_version` and `embedding_model` pinned lets you replay the exact retrieval that happened, see that the *old* embedding model (still in use that day) missed the right chunk entirely, and prove the fix (the new embedding model) already resolves it — turning a vague complaint into a closed, evidenced ticket.

---

## 7. Evaluation

Retrieval metrics (Recall@k, MRR, nDCG) on a labeled gold set; generation metrics (faithfulness, answer relevance); refusal calibration (false refusal rate vs. false answer rate) as a deliberate precision/recall trade-off.

**Why not just eyeball a few test questions before shipping?**
Spot-checking 5–10 queries is the easy way and it's how most regressions slip through — a chunking change can silently break retrieval for an entire document type while the 5 questions you happened to test still work fine. A gold set + regression suite exists specifically to catch changes that only affect the *other* 95% of queries you didn't manually check.

- *Example:* You improve chunking to keep tables intact (Section 2). This incidentally shifts token boundaries for every prose-only document too, and average chunk length rises 15%. Manually you'd never notice — but running the fixed 200-query gold set shows Recall@5 dropped 8 points specifically on the prose-only doc type, because chunks are now sometimes too long to embed distinctly. Without the regression suite, this ships silently and users just start getting slightly worse answers with no clear cause.

---

## 8. Implementation Stack (FarmCore POC)

Libraries below are what we would use to implement each layer. **POC column** = locked or in progress via ADRs and `docker-compose.yml`. **Phase 11+** = only if gold-set evidence triggers migration (see `MAPPING.md` §6).

### 8.1 Corpus pipeline (`ingest/` — offline)

| Layer | POC library / tool | Role | CAI tickets |
|---|---|---|---|
| PDF text extraction | **PyMuPDF** (`pymupdf>=1.24`) | Tier A text → `data/text/source/` | CAI-012–013 |
| Corpus filters | **stdlib** + custom `corpus_filter.py` | Tier A-only, empty/untitled/near-dup, boilerplate strip | CAI-014–017 |
| HTML/PDF fetch | **httpx**, **Playwright**, **crawl4ai**, **WeasyPrint** | Discover, fetch, render | pre-sprint |
| HTML text | **trafilatura**, **BeautifulSoup4** | Main-content extraction | pre-sprint |
| Structure-aware chunker | **Custom Python** + **tiktoken** (`cl100k_base` or model-matched encoding) | Heading/section splits, token budget, overlap | CAI-022–025 |
| Table extraction | **pdfplumber** (alongside PyMuPDF) | Table rows + caption chunks | CAI-024 |
| Snapshot artifacts | **stdlib** `json`, **jsonschema** | `chunks.jsonl`, manifests, checksums | CAI-026–028 |
| Manifest validation | **jsonschema** + `shared/schemas/chunks-v1.schema.json` | Hard-fail invalid chunks | CAI-007, CAI-027 |
| Tests | **pytest** | Baseline 605/34 guard, filter unit tests | CAI-021 |

### 8.2 Runtime platform (`farmcore/` — online)

| Layer | POC library / tool | Role | CAI tickets |
|---|---|---|---|
| Web framework | **Django 5.1**, **Django REST Framework** | API, apps, ORM | CAI-001–002 |
| Database | **PostgreSQL 16** + **pgvector** extension (`pgvector/pgvector:pg16`) | Embeddings, FTS, audit, app data | CAI-031, CAI-034 |
| Python DB driver | **psycopg 3** (`psycopg[binary]`) | Parameterised scope predicates | CAI-031 |
| Vector ORM | **pgvector** Python package | `vector(dim)` column, distance ops | CAI-031 |
| Sparse retrieval | **Postgres FTS** (`to_tsvector`, GIN partial indexes) — no extra service | Lexical recall for codes/names | CAI-041–042 |
| Job queue | **django-rq** + **Redis 7** | Async embed on snapshot import | CAI-032 |
| Object storage | **MinIO** (S3-compatible) | PDFs, snapshot blobs, tenant uploads | CAI-069 |
| Config | **django-environ** | Secrets, provider endpoints | CAI-001 |
| OpenAPI | **drf-spectacular** | Generated schema from DRF serializers | CAI-009 |
| Schema validation | **jsonschema** | Chunk + audit envelope validation | CAI-007–008 |

### 8.3 ML / retrieval adapters (behind ports)

| Component | POC choice | Python package | Port | Phase 11+ alternative |
|---|---|---|---|---|
| **Dense embeddings** | `BAAI/bge-large-en-v1.5` (1024-dim) | **sentence-transformers** | `EmbeddingPort` | New model + full re-embed |
| **Reranker** | `BAAI/bge-reranker-v2-m3` | **sentence-transformers** (CrossEncoder) or **FlagEmbedding** | `RerankPort` | Cohere Rerank API |
| **Generation** | Team-selected LLM | Provider SDK behind port (e.g. **openai**, **anthropic**, or **ollama** for local) | `GenerationPort` | Any provider swap |
| **Entailment** | LLM-as-judge (preferred POC) or small NLI | Judge via `GenerationPort`; optional **transformers** + `microsoft/deberta-v3-base-mnli` | `EntailmentPort` | ADR-0005 |
| **RRF fusion** | Custom Python | stdlib / small helper in `assistant/services/retrieval/` | — | — |
| **MMR diversity** | Custom Python | **NumPy** optional for vectorised cosine | — | — |
| **Query rewrite / HyDE** | Deferred default | Same `GenerationPort` when enabled | — | Phase 11+ (CAI-063 stretch) |

> **Not adopted for POC:** LlamaIndex, LangChain, Qdrant, OpenSearch/Elasticsearch — custom Django services + registries instead (`MAPPING.md` §6, ADR-0001, ADR-0002).

### 8.4 Audit, eval, CI

| Layer | POC library / tool | Role | CAI tickets |
|---|---|---|---|
| Audit store | **PostgreSQL** (`assistant.AuditEvent`, append-only rows) | Per-stage funnel, version tuple | CAI-008, CAI-059 |
| Eval metrics | **Custom scripts** + **pandas** optional | Recall@k, MRR, nDCG, faithfulness | CAI-062–064 |
| Regression CI | **pytest** + **pytest-django** | Baseline guards, scope-leak tests | CAI-021, CAI-038, CAI-064 |
| Token counting | **tiktoken** | Chunk budget, context packing | CAI-022, CAI-046 |

### 8.5 `requirements.txt` touchpoints

| File | Already pinned | To add (Week 2–3) |
|---|---|---|
| `ingest/requirements.txt` | pymupdf, pytest, httpx, trafilatura, … | `tiktoken`, `pdfplumber` |
| `farmcore/requirements.txt` | Django, DRF, pgvector, django-rq, jsonschema | `sentence-transformers`, `tiktoken`, `drf-spectacular`, provider SDK |

---

## 9. Build Order — and why this order specifically

This order matches [`PLAN.md`](../PLAN.md) phases and the CAI sprint critical path (`CAI-036 → CAI-043 → CAI-050 → CAI-055 → CAI-064`).

| Step | What | CAI / phase | Status |
|---|---|---|---|
| 1 | Ingestion + filters + boilerplate strip | CAI-012–021 / Phase 1 | ✅ Done |
| 2 | Structure-aware chunking + parent-child + snapshot | CAI-022–028 / Phase 2 | Next |
| 3 | Single dense retriever + generation (no rerank) | CAI-030–036 / Phase 3 | Week 2 |
| 4 | Postgres FTS + RRF hybrid fusion | CAI-041–043 / Phase 4 | Week 3 |
| 5 | Cross-encoder reranker + MMR + context pack | CAI-044–046 / Phase 4 | Week 3 |
| 6 | Citation mapping + entailment verification | CAI-049–052 / Phase 5 | Week 3 |
| 7 | Groundedness gate + refusal categories | CAI-054–058 / Phase 6 | Week 3 |
| 8 | Structured audit across all stages | CAI-059, CAI-040 / Phase 0+4 | Partial (model exists) |
| 9 | Gold eval set + regression CI | CAI-060–064 / Phase 7 | Week 3–4 |
| 10 | Agentic retrieval, decomposition, self-query | Phase 11+ | **Out of POC scope** |

1. Ingestion + chunking + single dense retriever, no rerank.
2. Add BM25 + RRF hybrid fusion.
3. Add cross-encoder reranker.
4. Add citation mapping + entailment verification.
5. Add groundedness gate + refusal categories.
6. Add structured audit logging across all stages.
7. Build the gold evaluation set and wire in regression testing.
8. Agentic/iterative retrieval, query decomposition, self-querying filters.

**Why this order and not, say, building the fanciest agentic loop first?**
It's tempting to build the "impressive" features (agentic re-querying, decomposition) first because they demo well. The order here is deliberately ROI-sorted: hybrid retrieval and reranking fix the largest share of wrong-answer cases for the least engineering effort, while agentic loops add real latency/cost and only pay off once the underlying retrieval is already solid — an agent that re-queries against a bad retriever just calls the bad retriever twice.

- *Example:* Teams that build query decomposition/agentic loops before hybrid+rerank often find that multi-hop questions still fail — not because decomposition is broken, but because each sub-query still hits the same weak single-stage retriever. Fixing the retriever first means every later feature (citations, refusals, agentic loops) is being built on top of results that are actually good enough to cite and act on.

---

## 10. Alignment with existing FarmCore plan

| Design section | FarmCore record | Notes |
|---|---|---|
| §2 Ingestion & chunking | `PLAN` Phase 1–2, CAI-022–025 | Chunk params match CAI (300–500 tok). Immutable store = `content_hash` + snapshot checksums (ADR-0009). |
| §3 Multi-stage retrieval | `ARCHITECTURE` §3.3, `PLAN` Phase 4, CAI-041–047 | Dense = pgvector; sparse = Postgres FTS, **not** OpenSearch (ADR-0002). RRF top-50 + rerank top-8 + MMR. |
| §4 Groundedness gate | `PLAN` Phase 6, CAI-054–058 | Refusal codes match refusal registry (`NO_RELEVANT_CONTEXT`, `INSUFFICIENT_COVERAGE`, etc.). |
| §5 Citations | ADR-0005, CAI-049–052 | Claim-level markers + `EntailmentPort`; LLM-as-judge acceptable for POC. |
| §6 Audit | ADR-0007, CAI-008, CAI-059 | Postgres append-only `AuditEvent`; version tuple on every response. |
| §7 Evaluation | `PLAN` Phase 7, CAI-060–064 | Gold set + offline metrics; CI regression gate Week 4. |
| §8 Stack | ADRs 0001–0002, `EXTENSIBILITY` §5 | pgvector + Postgres FTS locked; Qdrant/OpenSearch/LlamaIndex explicitly deferred. |
| §9 Build order | `CAI_SPRINT_PLAN` critical path | Step 1 complete; steps 2–9 map to Weeks 2–4 tickets. |
| Query rewrite / HyDE | `CAI_SPRINT_PLAN` Week 3 stretch | Optional flag only — not default POC path. |
| Scheduling / tools | ADR-0006, CAI-075–083 | Out of RAG scope until Week 4 optional stubs. |

### Gaps to watch (design vs sprint)

| Topic | Design doc says | FarmCore POC decision |
|---|---|---|
| Vector DB | "Qdrant or pgvector" | **pgvector only** until Phase 11+ evidence (ADR-0001) |
| Sparse | "OpenSearch BM25" | **Postgres FTS** (ADR-0002) |
| Orchestration | "LlamaIndex or custom" | **Custom** Django services + ports |
| Entailment default | "DeBERTa-MNLI or LLM-as-judge" | **LLM-as-judge** first; NLI optional (ADR-0005) |
| Chunk size | Was 256–512 | **300–500** per CAI-022 and `chunks-v1` max 500 |

No architectural conflicts — the generic design doc is now specialised to the accepted FarmCore stack above.
