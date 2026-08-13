import logging
import re

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.openai_client import client
from app.models.chunk import Chunk
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.enums import MessageRole
from app.models.message import Message
from app.services.embeddings import embed_texts

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a research assistant for a document-based Q&A \
product. You have access to excerpts from the user's uploaded document, \
provided with each question below.

How to respond:
- Reply in the same language the user's question is written in.
- Greetings, small talk, and questions about what you can do (e.g. "hi", \
"what can you help with?") get a normal conversational reply - no \
excerpts needed, no citation markers required.
- Questions answerable from the excerpts: answer only using them. Every \
factual claim must be tagged with the excerpt(s) it came from, using \
the exact marker format [chunk_<id>], e.g. [chunk_42]. Place the marker \
immediately after the claim it supports. If multiple excerpts support \
one claim, include multiple markers, e.g. [chunk_12][chunk_47]. Do not \
invent chunk ids that weren't provided.
- Questions that need outside/general knowledge not in the excerpts \
(e.g. current events, facts about unrelated topics): say plainly that \
you can only answer from the uploaded document, and don't answer from \
your own general knowledge - even if you know the answer.
- If the excerpts don't contain the answer to an otherwise in-scope \
question, say so plainly rather than guessing.
"""

MARKER_RE = re.compile(r"\[chunk_(\d+)\]")


def _retrieve_chunks(db: Session, project_id: int, query_embedding: list[float]) -> list[Chunk]:
    """
    Vector search scoped to project_id (DECISIONS.md 001 - shared HNSW
    index, filtered per query).

    hnsw.iterative_scan is a session-level Postgres setting, not something
    SQLAlchemy applies automatically - must be set explicitly per query
    or the mitigation from DECISIONS.md 005 silently doesn't happen.
    SET LOCAL scopes it to the current transaction only.

    top_k is a ceiling; similarity_threshold is a floor applied after the
    fetch - a chunk within the top_k nearest can still be dropped if it's
    not actually similar enough to be useful.
    """
    db.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))

    distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
    stmt = (
        select(Chunk, distance)
        .where(Chunk.project_id == project_id)
        .options(selectinload(Chunk.document))
        .order_by(distance)
        .limit(settings.retrieval_top_k)
    )
    rows = db.execute(stmt).all()

    max_distance = 1 - settings.retrieval_similarity_threshold
    return [chunk for chunk, dist in rows if dist <= max_distance]


def _build_llm_messages(
    history: list[Message], question: str, chunks: list[Chunk]
) -> list[dict]:
    """
    LLM sees only chunk_id + content per DECISIONS.md 008 - no filename,
    path, or page numbers. Full prior history is resent per DECISIONS.md
    014. The retrieved-chunk context is appended only to the current
    turn's question, not written back into persisted message content.
    """
    context = "\n\n".join(f"[chunk_{c.id}]\n{c.content}" for c in chunks)
    augmented_question = f"Excerpts:\n\n{context}\n\nQuestion: {question}"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history:
        messages.append({"role": m.role.value, "content": m.content})
    messages.append({"role": "user", "content": augmented_question})
    return messages


def _parse_references(answer: str, chunks: list[Chunk]) -> list[dict]:
    """
    Maps markers found in the answer back to full chunk metadata already
    held in memory from retrieval - no second DB call (DECISIONS.md 008).
    Only chunks actually cited end up in the snapshot, not the full
    retrieved set - an uncited chunk that was retrieved but unused isn't
    a "reference" for this answer.
    """
    chunks_by_id = {c.id: c for c in chunks}
    cited_ids = {int(m) for m in MARKER_RE.findall(answer)}

    references = []
    for chunk_id in cited_ids:
        chunk = chunks_by_id.get(chunk_id)
        if chunk is None:
            # Model cited an id we didn't provide - drop it rather than
            # surface a broken/fabricated citation to the user.
            logger.warning("LLM cited unknown chunk_id=%s", chunk_id)
            continue
        references.append(
            {
                "chunk_id": chunk.id,
                "filename": chunk.document.filename,
                "file_type": chunk.document.file_type,
                "file_path": chunk.document.path,
                "start_page": chunk.page_start,
                "end_page": chunk.page_end,
            }
        )
    return references


def answer_question(db: Session, conversation: Conversation, question: str) -> Message:
    """
    Full retrieval + chat turn: embed query -> vector search -> LLM call
    -> persist both the user question and the assistant answer.

    The user Message is persisted with the raw question only (no chunk
    context baked in) - what gets augmented for the LLM call is a
    prompt-time concern, not something that belongs in stored history.
    """
    history = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
        .all()
    )

    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=question,
    )
    db.add(user_message)
    db.flush()

    try:
        query_embedding = embed_texts([question])[0]
        chunks = _retrieve_chunks(db, conversation.project_id, query_embedding)

        llm_messages = _build_llm_messages(history, question, chunks)
        response = client.chat.completions.create(
            model=settings.chat_model,
            messages=llm_messages,
        )
        answer = response.choices[0].message.content

        references = _parse_references(answer, chunks)

        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=answer,
            references=references or None,
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        return assistant_message
    except Exception as exc:
        conv_id, proj_id = conversation.id, conversation.project_id
        db.rollback()
        logger.exception(
            "Chat turn failed: %s",
            exc,
            extra={"conversation_id": conv_id, "project_id": proj_id},
        )
        raise