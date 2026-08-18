from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.core.config import settings

app = FastAPI(title="Agentic RAG Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(conversations_router)


@app.get("/health")
def health():
    return {"status": "ok"}
