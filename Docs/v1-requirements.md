# Agentic RAG Platform — v1 Requirements

## Goal
Prove the core loop end-to-end: upload a document, get it processed, chat with cited answers grounded in it. A real, usable product — not a demo of one isolated piece.

## In scope for v1

**Content**
- One project (single project, not multi-project management yet)
- Source type: PDF only
- Single embedding model (OpenAI), fixed — no per-project model choice yet

**Ingestion**
- Upload → partition → chunk → embed → store
- Some processing state on each document (`uploaded → processing → ready → failed`) so the app knows when a doc is queryable
- Pipeline can run synchronously / simplified — full async job visibility (Celery, per-stage UI) is not required yet

**Retrieval & chat**
- Plain vector similarity retrieval (no hybrid, no multi-query, no reranking)
- "Simple RAG" only — documents-only answers, no web search, no supervisor agent
- **Answers must cite source document + page** — this is core to the product, non-negotiable for v1

**Users & auth**
- Single user for now, no login flow required
- Every row still carries `user_id` (seeded/fixed value) so auth can be turned on later without a data migration
- No RBAC, no multi-tenancy (`tenant_id` explicitly excluded — see DECISIONS.md 003)

**Chat & conversations**
- Multiple conversations per project (`Project 1─N Conversation 1─N Message`)
- Chat history persisted in Postgres, not held in memory or client-side only
- Citations attached via marker-based references (see DECISIONS.md 008); `Message.references` stored as a point-in-time JSON snapshot, not a live join (see DECISIONS.md 010)

**Data storage**
- PostgreSQL + pgvector, one shared `chunks` table (project_id filter, not per-project index — see DECISIONS.md 001)
- Embedding stored as a column directly on `chunks` (see DECISIONS.md 002)

## Explicitly out of scope for v1 (deferred, not forgotten)
- Multiple projects / project management UI
- Multiple embedding models, per-project model choice
- Hybrid / multi-query retrieval, reranking
- Agentic RAG mode (web search + supervisor agent / LangGraph)
- Auth, RBAC, multi-tenancy
- Visible multi-step ingestion pipeline UI, Celery/Redis async queue
- Eval harness (ragas), LangSmith, Sentry, ELK
- Containerized/Fargate deployment
- Other source types (docx, html, etc.)
- Multimodal ingestion: image/table extraction, AI summarization, dual-representation retrieval (see DECISIONS.md 004)

## Definition of done for v1
A user can:
1. Upload a PDF to the (single) project
2. Wait for it to finish processing
3. Ask a question in chat
4. Get an answer grounded in the document, with a citation to the specific source page

## Build sequencing
Both API and frontend are in v1 scope, built in two phases:
1. **API first** — FastAPI backend, all v1 endpoints (upload, ingestion status, chat) working and testable (e.g. via curl/Postman) before any UI exists. The API contract drives the frontend, not the reverse.
2. **Frontend after** — minimal Next.js UI consuming the API once it's stable. No frontend work starts until phase 1 is functionally complete.

## Open questions to resolve before/during build
- Data model (projects, documents, chunks, users) — ER diagram next
- Exact ingestion trigger: synchronous request/response vs. simple background task (short of full Celery)
