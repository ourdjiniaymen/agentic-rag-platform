from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.project import Project
from app.schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from app.services.retrieval import answer_question

router = APIRouter(tags=["conversations"])


def _get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


def _get_conversation(db: Session, conversation_id: int) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    return conversation


@router.post(
    "/projects/{project_id}/conversations",
    response_model=ConversationRead,
    status_code=201,
)
def create_conversation(
    project_id: int, body: ConversationCreate, db: Session = Depends(get_db)
) -> Conversation:
    _get_project(db, project_id)
    conversation = Conversation(project_id=project_id, title=body.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get(
    "/projects/{project_id}/conversations",
    response_model=list[ConversationRead],
)
def list_conversations(project_id: int, db: Session = Depends(get_db)) -> list[Conversation]:
    _get_project(db, project_id)
    return (
        db.query(Conversation)
        .filter(Conversation.project_id == project_id)
        .order_by(Conversation.created_at)
        .all()
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=201,
)
def post_message(
    conversation_id: int, body: MessageCreate, db: Session = Depends(get_db)
) -> Message:
    conversation = _get_conversation(db, conversation_id)
    return answer_question(db, conversation, body.content)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageRead],
)
def list_messages(conversation_id: int, db: Session = Depends(get_db)) -> list[Message]:
    _get_conversation(db, conversation_id)
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )