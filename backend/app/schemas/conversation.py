from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import MessageRole


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: MessageRole
    content: str
    references: Optional[list[dict[str, Any]]]
    created_at: datetime
