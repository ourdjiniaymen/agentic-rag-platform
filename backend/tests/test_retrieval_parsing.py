from types import SimpleNamespace

from app.services.ingestion import _page_range
from app.services.retrieval import MARKER_RE, _parse_references


def _fake_chunk(id, content, filename="doc.pdf", path="/storage/1/1/doc.pdf"):
    document = SimpleNamespace(filename=filename, file_type="application/pdf", path=path)
    return SimpleNamespace(
        id=id, content=content, page_start=1, page_end=1, document=document
    )


def test_marker_regex_finds_all_markers():
    text = "Some claim [chunk_12] and another [chunk_47][chunk_3]."
    assert MARKER_RE.findall(text) == ["12", "47", "3"]


def test_parse_references_maps_cited_chunks_to_metadata():
    chunks = [_fake_chunk(12, "a"), _fake_chunk(47, "b")]
    answer = "Claim one [chunk_12]. Claim two [chunk_47]."

    refs = _parse_references(answer, chunks)

    assert len(refs) == 2
    ids = {r["chunk_id"] for r in refs}
    assert ids == {12, 47}


def test_parse_references_drops_fabricated_chunk_id():
    chunks = [_fake_chunk(12, "a")]
    answer = "A claim citing an id that was never retrieved [chunk_99999]."

    refs = _parse_references(answer, chunks)

    assert refs == []


def test_parse_references_returns_empty_for_uncited_answer():
    chunks = [_fake_chunk(12, "a"), _fake_chunk(47, "b")]
    answer = "A conversational answer with no citations at all."

    refs = _parse_references(answer, chunks)

    assert refs == []


def test_parse_references_ignores_retrieved_but_uncited_chunks():
    """A chunk that was retrieved but never actually cited in the answer
    shouldn't end up in the references snapshot."""
    chunks = [_fake_chunk(12, "a"), _fake_chunk(47, "b")]
    answer = "Only cites one of the two retrieved chunks [chunk_12]."

    refs = _parse_references(answer, chunks)

    assert len(refs) == 1
    assert refs[0]["chunk_id"] == 12


def test_page_range_spans_multiple_original_elements():
    orig_elements = [
        SimpleNamespace(metadata=SimpleNamespace(page_number=3)),
        SimpleNamespace(metadata=SimpleNamespace(page_number=4)),
        SimpleNamespace(metadata=SimpleNamespace(page_number=5)),
    ]
    chunk = SimpleNamespace(metadata=SimpleNamespace(orig_elements=orig_elements))

    assert _page_range(chunk) == (3, 5)


def test_page_range_falls_back_to_sentinel_when_no_page_numbers():
    orig_elements = [SimpleNamespace(metadata=SimpleNamespace(page_number=None))]
    chunk = SimpleNamespace(metadata=SimpleNamespace(orig_elements=orig_elements))

    assert _page_range(chunk) == (0, 0)
