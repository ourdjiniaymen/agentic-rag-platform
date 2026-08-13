import logging

from sqlalchemy.orm import Session
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element
from unstructured.partition.pdf import partition_pdf

from app.core.config import settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.services.embeddings import embed_texts

logger = logging.getLogger(__name__)


def _partition(path: str) -> list[Element]:
    """
    Text-only partitioning per DECISIONS.md 004 (multimodal deferred to v2).

    hi_res per DECISIONS.md 012 - layout-model-based, handles multi-column
    and scanned pages correctly, at the cost of slower synchronous ingestion.

    infer_table_structure=False / extract_image_block_to_payload=False:
    v1 doesn't use tables or images at all, so there's no reason to pay
    the extra processing cost of extracting/structuring them. Flip both
    to True (and pass extract_image_block_types=["Image"]) when
    multimodal ingestion (v2, DECISIONS.md 004) is built.
    """
    return partition_pdf(
        filename=path,
        strategy="hi_res",
        infer_table_structure=False,
        extract_image_block_to_payload=False,
    )


def _chunk(elements: list[Element]) -> list[Element]:
    """
    chunk_by_title groups elements under detected section headers.

    include_orig_elements=True is required to recover per-chunk
    page_start/page_end after merging - a chunk's own .metadata.page_number
    can't be trusted alone once elements from multiple pages are combined
    (multipage_sections defaults to True, so a chunk can legitimately span
    pages). We derive the true range from .metadata.orig_elements instead.
    """
    return chunk_by_title(
        elements,
        max_characters=settings.chunk_max_characters,
        new_after_n_chars=settings.chunk_new_after_n_chars,
        combine_text_under_n_chars=settings.chunk_combine_text_under_n_chars,
        include_orig_elements=True,
    )


def _page_range(chunk: Element) -> tuple[int, int]:
    orig_elements = chunk.metadata.orig_elements or []
    pages = [
        e.metadata.page_number
        for e in orig_elements
        if getattr(e.metadata, "page_number", None) is not None
    ]
    if not pages:
        # Fallback: some element types may not carry page_number at all.
        # Better to record an obviously-wrong sentinel than silently drop
        # the chunk - surfaces as a visible bug rather than a missing one.
        return (0, 0)
    return (min(pages), max(pages))


def ingest_document(db: Session, document: Document) -> int:
    """
    Full synchronous ingestion pipeline (DECISIONS.md 006):
    partition -> chunk -> embed -> store.

    All-or-nothing per document: nothing commits until every chunk has
    been embedded and added successfully. On any failure, the document
    is marked FAILED and no partial Chunk rows are left behind - a failed
    document is safe to retry from scratch, never half-indexed.

    Returns the number of chunks stored, so callers don't need a second
    COUNT(*) query.
    """
    document.status = DocumentStatus.PROCESSING
    db.commit()

    try:
        elements = _partition(document.path)
        chunks = _chunk(elements)
        embeddings = embed_texts([c.text for c in chunks])

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            page_start, page_end = _page_range(chunk)
            db.add(
                Chunk(
                    project_id=document.project_id,
                    document_id=document.id,
                    content=chunk.text,
                    embedding=embedding,
                    page_start=page_start,
                    page_end=page_end,
                    chunk_index=i,
                )
            )

        document.status = DocumentStatus.INDEXED
        db.commit()
        return len(chunks)
    except Exception as exc:
        document_id, project_id = document.id, document.project_id
        db.rollback()
        document.status = DocumentStatus.FAILED
        db.commit()
        logger.exception(
            "Document ingestion failed: %s",
            exc,
            extra={"document_id": document_id, "project_id": project_id},
        )
        raise