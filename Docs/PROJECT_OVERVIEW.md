# Agentic RAG Platform — Project Overview

## Purpose
A vehicle for learning production software engineering, system design, and applied AI (RAG + agents) by shipping something real — not a toy project, and not a race to clone every feature of the reference course.

Inspired publicly by Harish Neel's "Six-Figure RAG" course curriculum (used only as an architecture/requirements reference — not code or paid content). Functionally comparable to Google's NotebookLM: users create projects, upload documents, and chat with an AI that answers grounded in those documents, with citations back to source pages.

## Status
No version has shipped yet. v1 scoping/design is complete — see `v1-requirements.md` and `DECISIONS.md`. Build has not started.

## Target architecture (north star — not all needed for v1)
- **Frontend:** Next.js, TypeScript, Tailwind CSS, Clerk (auth)
- **Backend:** Python, FastAPI, Celery + Redis (async job queue)
- **Data:** PostgreSQL + pgvector, AWS S3 for raw files
- **AI/RAG:** Unstructured.io (partitioning), LangChain, LangGraph (supervisor agent pattern — routes between RAG tool and web-search tool), OpenAI (LLM + embeddings), Guardrails AI (PII redaction, prompt-injection defense, output validation)
- **Ops:** Docker, AWS Fargate, GitHub, Sentry, ELK, LangSmith, ragas (RAG eval)

## Full feature surface (menu across all versions, not a v1 checklist)
- Projects as top-level container, each with own settings: embedding model (locked once documents uploaded), RAG strategy, agent type, chunking/retrieval params
- Ingestion pipeline as visible multi-step process (Upload → Queued → Partitioning → Chunking → Summarization → Vectorization/Storage → View Chunks)
- Configurable retrieval strategy per project: Vector / Hybrid (BM25+semantic) / Multi-Query Vector / Multi-Query Hybrid, optional reranking
- Two agent modes: "Simple RAG" (documents-only) vs "Agentic RAG" (RAG + web search via supervisor agent)
- Cited chat answers (source doc + page)
- Auth + RBAC (multi-user, role-based)
- Eval harness with ragas, wired into pipeline
- Production deployment: containerized, Fargate, real monitoring/observability
- Multimodal ingestion: image/table extraction, AI summarization, dual-representation retrieval (deferred — see DECISIONS.md 004)

## Working principles
- Every version must be genuinely usable end-to-end, not a demo of one isolated piece
- No infra for scale the project doesn't have yet (e.g. K8s/autoscaling, Celery/Redis, S3 are all v-later, not v1)
- Full stack above is intentionally more than v1 needs — sequence across versions
- Diagrams are used for the data model, ingestion pipeline, and agent graph specifically
- Decisions (especially deferrals) get written down, not silently skipped — see `DECISIONS.md`

## v1 scope
See `v1-requirements.md` for the full v1 slice, definition of done, and out-of-scope list. In short: single project, single user, PDF-only, Simple RAG (no web search/agent), plain vector retrieval, synchronous ingestion, local disk storage, cited chat answers via marker-based references — API-first (FastAPI), Next.js frontend after.

## Related files
- `v1-requirements.md` — v1 scope, definition of done
- `DECISIONS.md` — decision log (8 entries as of v1 scoping)
- ER diagram — Users / Projects / Documents / Chunks
- Ingestion pipeline diagram — PDF → Storage / Partitioning → Chunk → Embed → Store, with status transitions
- Retrieval/chat diagram — Query → Embed → Retrieve (project_id filtered) → chunks → LLM (chunk_id + content only) → answer with reference markers
