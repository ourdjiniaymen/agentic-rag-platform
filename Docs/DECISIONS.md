# Decisions Log

Lightweight ADR-style log. Each entry: decision, alternatives considered, why.

---

## 001 — Shared vector index with `project_id` filter, not per-project index

**Decision:** Store all chunks/embeddings in one shared `chunks` table (Postgres + pgvector), scoped per query with a `WHERE project_id = X` filter. One HNSW index serves all projects.

**Alternatives considered:**
- Per-project vector index/table: physical isolation per project.

**Why:** At current scale, metadata filtering on a shared table is fine and avoids managing N indexes/tables. Per-project physical isolation adds real ops overhead (migrations, monitoring, backups multiplied) with no benefit until there's a scale or compliance reason to isolate. Revisit if/when multi-tenancy or data-isolation requirements demand it.

---

## 002 — Single embedding column in v1; split into per-model embedding tables when model #2 is added

**Decision:** v1 stores the embedding as a column directly on `chunks` (`embedding vector(1536)`), since only one embedding model (OpenAI) is used. When a second embedding model is introduced, refactor to: `chunks(id, project_id, document_id, page, text)` + one `embeddings_<model>(chunk_id FK, embedding vector(dim))` table per model.

**Alternatives considered:**
- One column + model/dim metadata: rejected — pgvector columns have a fixed dimension; can't mix dims in one column or one HNSW index.
- Multiple embedding columns (one per model) on `chunks`: rejected — requires a schema migration per new model and leaves null columns on every row for models not used.
- Per-model tables from v1: rejected for now — premature, v1 only has one model. Correct design once model #2 exists.

**Why:** Avoid designing for a problem (multiple embedding models) that v1 doesn't have yet, per the project's "no infra for scale we don't have" principle. The migration path is well understood and cheap to do later (create new table, backfill, drop inline column), so deferring it costs nothing.

---

## 003 — No `tenant_id` column in v1; multi-tenancy shape deferred

**Decision:** Do not add a `tenant_id` column to the schema in v1. `user_id` is added now (per-row) since its shape is certain and cheap, but tenancy is left undecided until it's actually scoped.

**Alternatives considered:**
- Add `tenant_id` now as future-proofing, mirroring the `user_id` decision.

**Why:** Unlike `user_id`, the shape of "tenant" isn't known yet — whether it's an org, a team, whether a user belongs to one tenant or many, and how it nests with projects (tenant → users → projects vs. other hierarchies) is all undecided and not implied by the current feature list. Adding a column for an undefined concept risks guessing the wrong shape and migrating it anyway later — the same premature-scaling trap the project avoids elsewhere, just less obvious. Decide the real shape when multi-tenancy is scoped, likely alongside RBAC (roles only make sense within a tenant boundary).

---

## 004 — Multimodal ingestion (images, HTML tables per chunk) deferred to v2

**Decision:** v1 ingestion is pure text extraction only. No image or table columns on `Chunk` in v1, even though Unstructured.io (the reference architecture's partitioner) supports extracting them.

**Alternatives considered:**
- Build multimodal from v1: extract images/HTML tables per chunk, generate AI summaries at ingestion time, embed/match on the summary but return original content at query time.

**Why:** Not implied by the v1 requirements doc (Simple RAG, PDF only, plain vector retrieval, "upload → ask → cited answer"), all of which are satisfiable with text-only chunking. Multimodal adds three non-trivial, independently-failing subsystems (extraction, AI summarization, dual-representation retrieval) before the core loop has even been proven once — direct risk to the "genuinely usable end-to-end" principle. A real, well-scoped v2/v3 feature, not a v1 necessity; nothing about deferring it blocks adding it later, and it's arguably easier to add once the base retrieve/cite loop already works.

---

## 005 — pgvector: shared HNSW index filtering risk, not tuned in v1

**Decision:** Use pgvector's iterative scan (available ≥0.8) as a lightweight default mitigation for filtered search over the shared `chunks` index, but do not otherwise tune HNSW parameters (`ef_search`, etc.) in v1.

**Context / risk:** With one shared HNSW index across all projects filtered by `project_id`, HNSW applies the filter during graph traversal (not a separate post-filter pass), but an unbalanced project size distribution (e.g. one project with 50 chunks, another with 500,000) can still cause a query on the small project to under-return or return lower-quality matches if the graph traversal finds mostly the large project's chunks before satisfying `LIMIT k`. Iterative scan mitigates this by expanding the search until enough post-filter matches are found, at the cost of more traversal time when the filter is highly selective.

**Why not solved further now:** v1 doesn't yet have multiple projects with meaningfully different chunk-count scales to observe or diagnose this against real data. Tuning further now would be guessing; revisit once real usage shows imbalance.

---

## 008 — Marker-based citations; LLM sees only `chunk_id` + `content`

**Decision:** At query time, retrieval fetches full chunk metadata (`chunk_id, content, file_path, filename, file_type, start_page, end_page`) via the `Chunk`/`Document` join and keeps it in app memory. The LLM prompt includes only `chunk_id` and `content` per chunk — no filename, path, or page numbers. The LLM is instructed to tag claims in its answer with reference markers (e.g. `[chunk_1]`). The app then maps each marker back to the full metadata already held in memory to render clickable citations — no second DB call.

**Alternatives considered:**
- Give the LLM full metadata (filename, path, page) and let it state citations in prose directly.
- Give the LLM only `chunk_id`, have it return markers, then re-fetch full metadata from the DB per marker after the fact.

**Why:** The LLM doesn't need filename/path/page to reason about the answer — that's presentation metadata, not reasoning input. Sending it adds prompt tokens and gives the model room to mis-transcribe a filename or page number in prose, where citation accuracy can't be verified against ground truth. Withholding it and having the app attach citations from data it already fetched during retrieval avoids a redundant second DB round-trip and keeps doc/page values authoritative (from the DB, not the LLM's own output).

---

## 009 — v1 dependency scope: Unstructured.io yes; LangChain, LangGraph, boto3 deferred

**Decision:** v1 uses Unstructured.io directly for PDF partitioning, and calls the OpenAI SDK directly for embeddings and chat completion, with a hand-written prompt builder (f-string/Jinja) for message + retrieved-chunk assembly. No LangChain, no LangGraph, no boto3 in v1.

**Alternatives considered:** Adopt LangChain now for prompt templating and message handling, ahead of needing LangGraph.

**Why:** v1's LLM flow is a single static shape — embed query → vector search → one LLM call, no chains, no agent, no tool routing. LangChain/LangGraph's abstractions exist to manage variation and composition across multiple chains/tools/models, a problem v1 doesn't have; adopting them now means learning and debugging through framework indirection for something the OpenAI SDK does directly in fewer lines. Message persistence is unrelated to LangChain regardless — it's just the app's own `Message` table. boto3 has no v1 use since S3 is deferred (see 007). Revisit LangChain/LangGraph together once the v2 supervisor-agent (RAG + web search) is actually being built — natural fit at that point, isolated adoption now is not.

---

## 010 — Conversation persistence in Postgres; multiple conversations per project; no Redis in v1

**Decision:** Add `Conversation` (project-scoped) and `Message` (conversation-scoped) tables to the v1 data model: `Project 1─N Conversation 1─N Message`. A project can have multiple conversations. Chat history is persisted in Postgres, not held in memory or a client-side session. No Redis in v1.

`Message.references` is a JSON snapshot of citation metadata (`chunk_id, filename, file_type, file_path, start_page, end_page`) captured at generation time, not a normalized FK/join to live chunks.

**Alternatives considered:**
- No persistence (chat lives only in the request/response, client resends full history each turn).
- Normalized `references` join table pointing at live `chunk_id`s.
- Redis for chat/session state.

**Why:** Persistent, resumable, multi-conversation chat is part of "genuinely usable end-to-end" — a chat that forgets itself isn't usable, and users may want more than one conversation thread per project. Postgres already holds all other v1 state; no separate store is needed. Redis in the target architecture is specifically Celery's broker (already deferred, see 006) — there's no other v1 need for it (no caching, no session-store requirement yet). `references` as a point-in-time JSON snapshot is intentional, not a shortcut: normalizing it would mean a deleted or re-chunked document could silently corrupt or orphan historical citations; a conversation should show what was true when the message was sent.

---

## 006 — Synchronous ingestion pipeline in v1; Celery/Redis deferred

**Decision:** `POST /projects/{id}/documents` runs the full ingestion pipeline (partition → chunk → embed → store) synchronously within the request and returns once the document's status is `indexed` or `failed`. No background task queue, no polling endpoint behavior required for v1.

**Alternatives considered:**
- Return immediately with `status: pending`/`processing` and require the client to poll `GET /documents/{id}` for completion, backed by Celery + Redis per the target architecture.

**Why:** A single PDF processes in seconds-to-low-minutes at v1 scale (single user, one document at a time). Async infra (Celery, Redis, worker processes, task monitoring) is real operational complexity with no payoff until concurrent/multi-user ingestion load exists — same "no infra for scale we don't have" principle applied elsewhere. The `status` field on `Document` (pending/processing/indexed/failed) is kept regardless, so moving to async later is a pipeline-trigger change, not a data model change.

---

## 007 — PDF storage: local disk in v1, not S3

**Decision:** Uploaded PDFs are stored on local disk (e.g. `storage/{project_id}/{document_id}/{filename}`), with the path recorded in `Document.path`. No AWS S3 integration in v1.

**Why:** S3 requires AWS credentials/IAM and bucket setup for a single-user, local-only v1 that doesn't need durability or remote access yet. Storage is abstracted behind `Document.path` already, so switching to S3 later is a contained storage-layer change, not a schema or API change.

---

## 011 — `User` table stripped to `id, created_at` in v1

**Decision:** The `User` table carries no auth-related columns in v1 — no `email`, `username`, or `password`. Just `id` and `created_at`, referenced by `Project.user_id` (seeded/fixed single user) and `Document.uploaded_by`.

**Why:** v1 has no login flow (see requirements doc — "single user, no login flow required"); storing credentials or identity fields that are never read or checked is dead schema, not future-proofing. Consistent with the project's "no infra for scale we don't have" principle. When auth (Clerk) is added, `User` gets real identity columns at that point — likely aligned with whatever Clerk's user model provides, which may not even match a hand-rolled `email`/`username`/`password` shape anyway, so guessing the shape now would likely be wasted effort.

---
