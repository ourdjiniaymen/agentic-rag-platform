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
## 011 — `User` table stripped to `id, created_at` in v1

**Why:** v1 has no login flow (see requirements doc — "single user, no login flow required"); storing credentials or identity fields that are never read or checked is dead schema, not future-proofing. Consistent with the project's "no infra for scale we don't have" principle. When auth (Clerk) is added, `User` gets real identity columns at that point — likely aligned with whatever Clerk's user model provides, which may not even match a hand-rolled `email`/`username`/`password` shape anyway, so guessing the shape now would likely be wasted effort.
---
## 012 — Drop `uploaded_by` from `Document` in v1

**Decision:** Remove `uploaded_by` from `Document`. Ownership is derived via `Document → Project → user_id`.

**Why:** In v1 (single user), `uploaded_by` is always identical to the project's `user_id` — not denormalization for a real query-path reason (unlike `project_id` on `Chunk`, which is filtered on every retrieval), just a redundant column with no code path that could ever diverge yet. It only becomes meaningful once multiple distinct users can upload to the same project — a multi-user concern, not a tenancy concern (a tenant could still have a single user). Add it back when multi-user collaboration is actually scoped, with real semantics (e.g. whether it's reassignable) defined at that point.

**Terminology note:** Document status values are `Pending → Processing → Indexed → Failed` (matches ER diagram, ingestion pipeline diagram, and decision 006) — this is the canonical vocabulary; earlier informal shorthand (`uploaded/processing/ready/failed`) used before the diagrams existed is superseded.

**Chunk timestamps:** `Chunk` gets `created_at` but not `updated_at` — chunks are immutable in v1 (created once at ingestion, never edited in place; reprocessing would delete/recreate, and isn't a v1 feature anyway), so an `updated_at` column would imply a mutability path that doesn't exist.

---

## Note — chunking quality observed on first real ingestion test

Not a decision, just logged so it isn't lost before v2 review:

- OCR noise: `hi_res` returns OCR'd text from raster/scanned regions as
  regular text elements (not filtered by `extract_image_block_to_payload`,
  which only controls image *bytes*, not OCR'd text) — can pollute
  embeddings with low-quality content. Worth a text-confidence or
  region-type filter; needs checking what Unstructured actually exposes
  before committing to a fix.
- Chunk boundaries follow `chunk_by_title`'s section logic, not sentences —
  expected behavior, not a bug. True overlap would need a different
  chunking strategy or a post-processing step; `chunk_by_title` doesn't
  support it natively.
- Chunk size variance is tunable via existing config
  (`chunk_max_characters`/`new_after_n_chars`/`combine_text_under_n_chars`)
  but not iterated on yet.

Deferred to v2 chunking review — not blocking v1 DoD (grounded cited
answer), and the test document (scanned draft image + heavy license
boilerplate) is not representative of typical user uploads.

---

## 013 — Log full exception on ingestion failure; API response stays untyped (status: failed only)

**Decision:** `ingest_document` logs the full exception (`logger.exception`, with `document_id`/`project_id` context) before re-raising. The router still catches broadly and returns `201` with `status: "failed"` for any failure — the API response doesn't distinguish a genuine code bug from an expected pipeline failure (bad PDF, embedding API error).

**Alternatives considered:**
- Typed exceptions (`PartitioningError`, `EmbeddingAPIError`, vs. unexpected) so the router could return different responses/status codes per failure category.

**Why:** The broad `except Exception` in the router (see decision on 201-with-status-field response) means a real bug and a content-related failure currently look identical to the API client. Logging closes the *operator's* visibility gap cheaply — a full traceback plus document/project context is enough to tell "every document is failing with the same stack trace" (code bug) from "this one PDF failed" (content issue) by reading logs. Typed exceptions would let the *client* make that distinction too, but that's real design work (defining the exception taxonomy, deciding what each maps to in the response) with no v1 requirement forcing it yet. Revisit once real failure patterns are observed - premature to guess the right taxonomy now.

---

## 014 — Full conversation history resent every message; no summarization/windowing in v1

**Decision:** Each chat turn sends the LLM the full persisted message history for that conversation (all prior `Message` rows, in order), not a summarized or windowed subset. No caching layer either.

**Alternatives considered:**
- Sliding window (last N messages only).
- Running summarization of older turns, kept alongside recent raw messages.
- Prompt caching (provider-level) to reduce repeated-prefix cost.

**Why:** v1's conversations are expected to be short (single user, one project, testing the core loop) - token cost from resending full history is negligible at this scale. Summarization/windowing are real techniques with real trade-offs of their own (what gets lost in a summary, when a window boundary cuts off relevant earlier context) that shouldn't be guessed at without seeing real long-conversation usage. Same "no infra for scale we don't have" principle as elsewhere - revisit once conversation length or token cost actually becomes a problem, not before.

---

## 015 — Custom per-project system prompt deferred; v1 uses one hardcoded prompt

**Decision:** v1's chat uses a single hardcoded `SYSTEM_PROMPT` (services/retrieval.py). No per-project custom prompt/instructions field in v1. When added (later version), the design is concatenation, not replacement: the hardcoded grounding/citation rules stay in force, and any user-supplied instructions get appended after them - never substituted in place of the citation contract.

**Alternatives considered:**
- Let a per-project custom prompt fully replace the system prompt.

**Why:** Not implied by v1 requirements (no project settings concept exists yet - see decision 003's "settings later" note on the ER diagram). Full replacement would let a custom prompt silently drop the citation-marker instruction (decision 008) or the "don't answer from outside knowledge" grounding rule, breaking the core "cited answer" guarantee the whole product depends on. Concatenation preserves the non-negotiable contract while still allowing customization - append-only, not override.

---

## 016 — No duplicate-upload detection in v1, despite storing `checksum`

**Decision:** `Document.checksum` (sha256, computed at upload) is stored but not checked against existing documents. Uploading the same PDF twice creates two separate `Document` rows and duplicate `Chunk` sets, both retrievable and citable independently.

**Context:** Observed in testing - the same PDF uploaded twice caused answers to cite two chunks covering the same content from different documents (e.g. `chunk_46` + `chunk_8`, different storage paths), consuming two of the `top_k` retrieval slots for redundant content.

**Why not fixed now:** Not a retrieval bug - retrieval and citation both worked correctly against what was actually indexed. It's a data-hygiene gap: nothing stops a duplicate upload from happening. `checksum` already exists specifically to make this fixable later (reject or warn on a repeat checksum within a project) without a schema change - just an endpoint-level check that hasn't been added yet. Deferred rather than fixed immediately since it's not blocking v1 DoD and the right UX (reject vs. warn vs. silently reuse the existing document) hasn't been decided.

**Resolved:** `POST /projects/{id}/documents` now checks `checksum` against existing documents in the same project and rejects with `409 Conflict` (pointing at the existing document's id/filename/status) rather than silently reusing or duplicating. Reject was chosen over silent reuse because a duplicate upload attempt is meaningful signal to surface to the client, not something to paper over.

---

## 017 — Load/concurrency and ragas comparison tests deferred to v2

**Decision:** v1's test suite (pytest, `backend/tests/`) covers correctness only: API integration tests (with mocked OpenAI + mocked partitioning) and unit tests for pure logic (embedding order-safety, citation marker parsing, page-range derivation). No load/concurrency tests and no ragas-based quality eval in v1.

**Why:** Load/concurrency tests would be testing against v1's known-synchronous ingestion (DECISIONS.md 006) and single-user assumption - there's no concurrent-load scenario v1 is designed to handle yet, so a load test today would only confirm what's already known by design, not surface new information. ragas (RAG-quality eval) is explicitly a later-version feature per PROJECT_OVERVIEW.md's target architecture, not scoped for v1.

**Intent, not forgotten:** the plan is to establish load/concurrency and ragas baselines once async ingestion (Celery) and/or retrieval tuning are actually built, specifically so v2 changes can be measured against a real v1 baseline rather than guessed at. Revisit at that point, not before.

---

## 018 — v1 hardening gaps not yet addressed (not oversights, not prod-ready as-is)

**Decision:** Log the following as known, deliberate v1 gaps rather than leave them undocumented. Not fixed now; each needs its own scoping before being built, not a quick patch.

- **No auth, no rate limiting, no request size limits** on any endpoint (upload especially) - acceptable for a single-user local v1 (DECISIONS.md 011), not acceptable exposed beyond that. Real fix arrives with auth (Clerk), not before.
- **No retry/backoff on OpenAI calls** (embeddings or chat) - a transient network/rate-limit error fails the whole ingestion or chat turn outright. Production systems wrap these in retry logic (exponential backoff, at minimum for rate-limit responses); v1 doesn't.
- **No CI** - tests exist and pass locally (see 017) but nothing runs them automatically on push/PR. Unlike the other items here, this is a plain gap, not a scoped-out feature - cheap to add whenever.
- **No enforced linting/type-checking** (e.g. `ruff`, `mypy`) in CI or pre-commit - code quality currently depends on manual review catching issues (a missing `logger` import and a bulk-`update()` bug both slipped through undetected until tests were actually run).

**Why not fixed now:** None of these block the v1 DoD (upload -> indexed -> ask -> cited answer, single local user). Auth/rate-limiting is real design work tied to the Clerk integration, not a quick add. Retry/backoff needs a real policy decision (which errors retry, how many attempts, backoff shape) rather than a guessed default. CI and lint/type-check enforcement are the cheapest to add of this group and could reasonably be picked up before v2 rather than deferred alongside the others - logged together here since none were addressed yet, not because they're equally hard.

---

## 019 — Chat turn failures return raw 500, unlike ingestion's 201-with-status

**Decision:** `POST /conversations/{id}/messages` lets an unhandled exception from `answer_question` propagate as a plain `500`, rather than following the pattern used for document ingestion (decision on 201-with-status-field for pipeline failures).

**Why not made symmetric with ingestion:** `Document` has a `status` field precisely to represent "this failed, here's the row anyway" as a first-class domain state. `Message`/`Conversation` don't - inventing one just to make the failure response shape symmetric would mean designing new schema (a status field with no other use) purely for error presentation, not because chat has an equivalent "partially succeeded" state to represent (the user's question is either answered or it isn't; there's no useful partial state to persist). Retrieval already rolls back the user's question on failure (DECISIONS.md, chat-turn rollback), so no orphaned data - the only gap is the response shape a client sees.

**Accepted for v1:** matches decision 013's stance - log instead of building typed-exception/response-taxonomy infrastructure prematurely. Revisit if/when a real product need appears (e.g. showing the user "that failed, try again" distinctly from a generic error).

---
## 020 — `Conversation.updated_at` doesn't bump on new messages

**Decision:** Left as-is for v1, deferred to v2 rather than fixed now.

**Context:** Discovered during frontend work - the conversation sidebar sorts by `created_at` instead of true "recent activity," since nothing touches the parent `Conversation` row when a `Message` is added to it. `onupdate=func.now()` on `Conversation.updated_at` never fires as a result.

**Why not fixed now:** A real bug, not a design trade-off - but v1 is being closed at DoD rather than gold-plated further. The fix is small and contained (touch `conversation.updated_at` inside `answer_question` when persisting the assistant message) and doesn't require a schema change, so it's cheap to pick up at the start of v2 rather than reopening v1 for it.

---

## 021 — `Message.references` limited to filename + page range; no chunk text or file-serving in v1

**Decision:** The citation payload returned to the frontend (`API.md`) exposes only `chunk_id, filename, file_type, file_path, start_page, end_page` - no chunk text/snippet, no highlighted span, and no endpoint to actually fetch/view the source file. The v1 frontend's citation UI (clickable popover) is built against this limited payload by necessity.

**Alternatives considered:**
- Include chunk `content` in `references` so the frontend could show a text preview without a second request.
- A file-serving endpoint so citations could deep-link into the actual PDF page.

**Why not decided now:** This is a real design question - how much to expose (snippet vs. full chunk vs. highlighted span vs. rendered PDF page) - not a bug, and not implied by v1's DoD ("cited answer" was satisfied by filename+page). Deciding it now, driven by a frontend nice-to-have rather than a real product requirement, risks guessing the wrong shape. Revisit in v2 alongside whatever the actual citation-UX bar turns out to be once real usage exists.

---

## v1 — Closed

Both v1 definitions of done are met and verified against the running
system:
- **Backend** (`v1-requirements.md`): upload -> indexed -> ask -> cited
  answer, via API.
- **Frontend** (`v1-frontend-requirements.md`): upload/list documents,
  create/list conversations, chat with clickable citations back to
  source document + page - all from the UI alone.

Known gaps (016-021 above, plus the hardening items in 018) are logged,
not forgotten, and carry into v2 planning rather than blocking v1's
close.