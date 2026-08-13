from types import SimpleNamespace


def test_create_and_list_conversations(client, seed_project):
    create = client.post("/projects/1/conversations", json={"title": "test"})
    assert create.status_code == 201
    assert create.json()["title"] == "test"

    listing = client.get("/projects/1/conversations")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_create_conversation_unknown_project(client):
    response = client.post("/projects/999/conversations", json={"title": "x"})
    assert response.status_code == 404


def test_list_conversations_unknown_project(client):
    response = client.get("/projects/999/conversations")
    assert response.status_code == 404


def test_post_message_unknown_conversation(client, mock_openai):
    response = client.post("/conversations/999/messages", json={"content": "hi"})
    assert response.status_code == 404


def test_list_messages_unknown_conversation(client):
    response = client.get("/conversations/999/messages")
    assert response.status_code == 404


def test_chat_turn_with_citation(
    client, seed_project, mock_openai, mock_ingestion_pipeline, db_session
):
    # ingest a document so there's something to retrieve/cite
    from pathlib import Path

    sample_pdf = Path(__file__).parent / "fixtures" / "sample.pdf"
    with open(sample_pdf, "rb") as f:
        upload = client.post(
            "/projects/1/documents",
            files={"file": ("sample.pdf", f, "application/pdf")},
        )
    chunk_id_in_answer = upload.json()  # confirmed indexed via chunk_count > 0
    assert chunk_id_in_answer["chunk_count"] == 1

    # find the real chunk id so the mocked answer can cite it correctly
    from app.models.chunk import Chunk

    chunk = db_session.query(Chunk).first()

    mock_openai.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=f"This is a fake grounded answer. [chunk_{chunk.id}]"
                )
            )
        ]
    )

    conv = client.post("/projects/1/conversations", json={"title": "t"})
    conv_id = conv.json()["id"]

    response = client.post(
        f"/conversations/{conv_id}/messages", json={"content": "What does it say?"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "assistant"
    assert f"[chunk_{chunk.id}]" in body["content"]
    assert len(body["references"]) == 1
    assert body["references"][0]["chunk_id"] == chunk.id


def test_chat_turn_ignores_fabricated_chunk_id(
    client, seed_project, mock_openai, mock_ingestion_pipeline
):
    """Per services/retrieval.py _parse_references: a cited chunk_id that
    wasn't actually retrieved gets dropped, not surfaced as a broken
    reference."""
    mock_openai.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="An answer citing [chunk_99999].")
            )
        ]
    )

    conv = client.post("/projects/1/conversations", json={"title": "t"})
    conv_id = conv.json()["id"]

    response = client.post(
        f"/conversations/{conv_id}/messages", json={"content": "hi"}
    )
    assert response.status_code == 201
    assert response.json()["references"] is None


def test_failed_chat_turn_rolls_back_user_message(
    client, seed_project, mock_openai, db_session
):
    """Per services/retrieval.py: on any failure mid-turn, db.rollback()
    runs before re-raising - the user's question should not be left
    persisted with no assistant reply."""
    import pytest

    from app.models.message import Message

    conv = client.post("/projects/1/conversations", json={"title": "t"})
    conv_id = conv.json()["id"]

    mock_openai.chat.completions.create.side_effect = RuntimeError("simulated LLM failure")

    with pytest.raises(RuntimeError):
        client.post(f"/conversations/{conv_id}/messages", json={"content": "hi"})

    remaining = db_session.query(Message).filter(Message.conversation_id == conv_id).count()
    assert remaining == 0