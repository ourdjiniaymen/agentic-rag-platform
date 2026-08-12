from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentStatus


class DocumentRead(BaseModel):
    """
    Response shape for a Document. No request/create schema here on
    purpose - creation happens via multipart file upload (UploadFile),
    not a JSON body, so there's nothing to validate as a Pydantic model
    on the way in. The router builds the Document row directly from the
    uploaded file plus path params.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    filename: str
    file_type: str
    file_size_bytes: int
    page_count: int
    title: str
    status: DocumentStatus
    checksum: str
    # Not a real Document attribute - model_validate(document) needs a
    # default so validation doesn't fail on the missing field. The router
    # always overrides this before returning.
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime