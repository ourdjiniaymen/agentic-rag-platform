from app.core.config import settings
from app.core.openai_client import client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batches embedding calls per settings.embedding_batch_size rather than
    one call per text (fewer round trips) or one call for everything at
    once (risks per-request token limits on large inputs).

    OpenAI's embeddings response is documented to preserve input order,
    but each returned object also carries its own `index` - we sort on
    it explicitly rather than trust ordering implicitly, since silently
    mismatching a text to the wrong embedding is a correctness bug that
    would be very hard to notice later.

    Shared by ingestion (chunk embedding) and retrieval (query embedding)
    so both go through the same model/batching path.
    """
    all_embeddings: list[list[float]] = []
    batch_size = settings.embedding_batch_size

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        sorted_data = sorted(response.data, key=lambda d: d.index)
        all_embeddings.extend(d.embedding for d in sorted_data)

    return all_embeddings
