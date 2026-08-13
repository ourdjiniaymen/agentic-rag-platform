from pathlib import Path

SAMPLE_PDF = Path(__file__).parent / "fixtures" / "sample.pdf"


def _upload(client, project_id=1, filename="sample.pdf"):
    with open(SAMPLE_PDF, "rb") as f:
        return client.post(
            f"/projects/{project_id}/documents",
            files={"file": (filename, f, "application/pdf")},
        )


def test_upload_document_success(
    client, seed_project, mock_openai, mock_ingestion_pipeline
):
    response = _upload(client)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "indexed"
    assert body["chunk_count"] == 1
    assert body["filename"] == "sample.pdf"
    assert "uploaded_by" not in body  # DECISIONS.md 012


def test_upload_rejects_non_pdf(client, seed_project):
    response = client.post(
        f"/projects/1/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_unknown_project(client, mock_openai, mock_ingestion_pipeline):
    response = _upload(client, project_id=999)
    assert response.status_code == 404


def test_upload_duplicate_checksum_returns_409(
    client, seed_project, mock_openai, mock_ingestion_pipeline
):
    first = _upload(client)
    assert first.status_code == 201

    second = _upload(client)
    assert second.status_code == 409
    assert str(first.json()["id"]) in second.json()["detail"]


def test_list_documents(client, seed_project, mock_openai, mock_ingestion_pipeline):
    _upload(client)

    response = client.get("/projects/1/documents")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["chunk_count"] == 1


def test_list_documents_unknown_project(client, seed_project):
    response = client.get("/projects/999/documents")
    assert response.status_code == 404


def test_ingestion_failure_returns_201_with_failed_status(
    client, seed_project, mock_openai, monkeypatch
):
    """
    Per DECISIONS.md: a pipeline failure is a domain outcome, not a
    transport error - the request still succeeds (a Document row exists),
    it's just marked failed.
    """

    def raise_error(elements):
        raise RuntimeError("simulated partitioning failure")

    monkeypatch.setattr("app.services.ingestion._partition", lambda path: [])
    monkeypatch.setattr("app.services.ingestion._chunk", raise_error)

    response = _upload(client)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["chunk_count"] == 0
