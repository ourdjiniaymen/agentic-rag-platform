from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.embeddings import embed_texts


def test_embed_texts_preserves_input_order_even_if_api_returns_shuffled(monkeypatch):
    """
    Regression test for the exact correctness bug flagged in
    services/embeddings.py: we must sort on the response's own `index`
    field rather than trust the array order, since silently mismatching
    a text to the wrong embedding would be a very hard bug to notice.
    """
    mock_client = MagicMock()

    def shuffled_response(model, input):
        # Deliberately return embeddings out of order, tagged distinctly
        # so we can verify they get reassembled correctly.
        data = [
            SimpleNamespace(embedding=[float(i)], index=i) for i in range(len(input))
        ]
        return SimpleNamespace(data=list(reversed(data)))

    mock_client.embeddings.create.side_effect = shuffled_response
    monkeypatch.setattr("app.services.embeddings.client", mock_client)

    result = embed_texts(["a", "b", "c"])

    assert result == [[0.0], [1.0], [2.0]]


def test_embed_texts_batches_by_configured_size(monkeypatch):
    from app.core.config import settings

    mock_client = MagicMock()
    call_sizes = []

    def record_batch(model, input):
        call_sizes.append(len(input))
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.0], index=i) for i in range(len(input))]
        )

    mock_client.embeddings.create.side_effect = record_batch
    monkeypatch.setattr("app.services.embeddings.client", mock_client)
    monkeypatch.setattr(settings, "embedding_batch_size", 2)

    embed_texts(["a", "b", "c", "d", "e"])

    assert call_sizes == [2, 2, 1]
