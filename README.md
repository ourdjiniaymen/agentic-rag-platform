# Agentic RAG Platform

A RAG platform — upload documents, chat with an AI grounded in them, get cited
answers back to the source page. 

## Status

**v1 in progress.** Scope is locked (see `docs/v1-requirements.md`):
single project, single user, PDF-only, plain vector retrieval, synchronous
ingestion, cited chat answers. No auth, no multi-project, no agentic
mode yet — see `docs/PROJECT_OVERVIEW.md` for the full target architecture
and what's deferred to later versions.

## Stack (v1)

- **Backend:** FastAPI, SQLAlchemy, Alembic
- **Data:** PostgreSQL + pgvector
- **AI:** OpenAI (embeddings + chat), Unstructured.io (PDF partitioning)
- **Infra:** Docker Compose (dev override + prod compose), local disk storage

Full target stack (Next.js, Celery/Redis, S3, LangGraph, auth, etc.) lives in
`docs/PROJECT_OVERVIEW.md` — intentionally more than v1 needs.

## Getting started (dev)

```bash
cp .env.example .env   # fill in OPENAI_API_KEY at minimum
docker compose up --build
```

- API: http://localhost:8000 (`/health` to check it's up)
- pgAdmin: http://localhost:5050 (login from `.env`; add a server manually,
  host `db`, port `5432`)

Migrations run automatically on container start (see `backend/entrypoint.sh`).

## Prod

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

## Project structure

```
backend/
  app/
    core/       # settings
    db/         # session factory, declarative Base
    models/     # SQLAlchemy models
    schemas/    # Pydantic request/response schemas
    api/        # routers
    services/   # ingestion pipeline, retrieval, LLM calls
  alembic/      # migrations
  storage/      # local PDF storage (gitignored contents)
docs/
  PROJECT_OVERVIEW.md   # purpose, target architecture, working principles
  v1-requirements.md    # v1 scope, definition of done
  DECISIONS.md          # ADR-style decision log
```

## Decisions

Non-trivial architectural choices and their trade-offs are logged in
`docs/DECISIONS.md` as they're made. Read it before assuming something is
unfinished rather than deliberate.
