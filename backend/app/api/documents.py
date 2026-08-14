import hashlib
import io
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.project import Project
from app.schemas.document import DocumentRead
from app.services.ingestion import ingest_document

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


def _get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


def _to_document_read(document: Document, chunk_count: int) -> dict:
    return {
        **DocumentRead.model_validate(document).model_dump(exclude={"chunk_count"}),
        "chunk_count": chunk_count,
    }


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentRead:
    _get_project(db, project_id)

    if file.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF files are supported in v1")

    raw = file.file.read()
    if not raw:
        raise HTTPException(400, "Uploaded file is empty")

    checksum = hashlib.sha256(raw).hexdigest()

    existing = (
        db.query(Document)
        .filter(Document.project_id == project_id, Document.checksum == checksum)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This file was already uploaded as document {existing.id} "
            f"({existing.filename}, status={existing.status.value})",
        )

    try:
        page_count = len(PdfReader(io.BytesIO(raw)).pages)
    except Exception:
        # Cheap structural check before the expensive hi_res pipeline runs -
        # a file that isn't a readable PDF at all should fail fast here,
        # not after minutes of partitioning.
        raise HTTPException(400, "File is not a valid PDF")

    title = os.path.splitext(file.filename or "untitled")[0]

    # id needed to build the storage path (DECISIONS.md 007), so flush
    # before writing to disk rather than guessing the next id.
    document = Document(
        project_id=project_id,
        path="",  # filled in below once we know the id
        filename=file.filename or "untitled.pdf",
        file_type="application/pdf",
        file_size_bytes=len(raw),
        page_count=page_count,
        title=title,
        status=DocumentStatus.PENDING,
        checksum=checksum,
    )
    db.add(document)
    db.flush()  # assigns document.id without committing yet

    doc_dir = os.path.join(settings.storage_root, str(project_id), str(document.id))
    os.makedirs(doc_dir, exist_ok=True)
    path = os.path.join(doc_dir, document.filename)
    with open(path, "wb") as f:
        f.write(raw)

    document.path = path
    db.commit()

    try:
        chunk_count = ingest_document(db, document)
    except Exception:
        # ingest_document already rolled back and set status=FAILED before
        # re-raising. The upload itself succeeded - a real Document row
        # exists - so this is a domain-level outcome, not a transport
        # failure. Swallow here and let the response body's `status`
        # field carry it; reserve 500 for genuinely unexpected server
        # bugs, not caught pipeline failures.
        chunk_count = 0

    db.refresh(document)
    return _to_document_read(document, chunk_count)


@router.get("", response_model=list[DocumentRead])
def list_documents(project_id: int, db: Session = Depends(get_db)) -> list[dict]:
    _get_project(db, project_id)

    documents = (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .order_by(Document.created_at)
        .all()
    )
    if not documents:
        return []

    counts = dict(
        db.execute(
            select(Chunk.document_id, func.count())
            .where(Chunk.document_id.in_([d.id for d in documents]))
            .group_by(Chunk.document_id)
        ).all()
    )
    return [_to_document_read(d, counts.get(d.id, 0)) for d in documents]