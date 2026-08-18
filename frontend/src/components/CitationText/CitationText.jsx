import { useState } from 'react';
import './CitationText.css';

const CHUNK_MARKER = /\[chunk_(\d+)\]/g;

export default function CitationText({ content, references }) {
  const [openIndex, setOpenIndex] = useState(null);

  if (!references || references.length === 0) {
    return <p>{content}</p>;
  }

  const referencesByChunkId = new Map(references.map((ref) => [ref.chunk_id, ref]));

  // Assign display numbers in order of first appearance in the text,
  // not by their position in the references array.
  const displayNumberByChunkId = new Map();

  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = CHUNK_MARKER.exec(content)) !== null) {
    const [fullMatch, chunkIdStr] = match;
    const chunkId = Number(chunkIdStr);

    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: content.slice(lastIndex, match.index) });
    }

    const reference = referencesByChunkId.get(chunkId);

    if (reference) {
      if (!displayNumberByChunkId.has(chunkId)) {
        displayNumberByChunkId.set(chunkId, displayNumberByChunkId.size + 1);
      }
      parts.push({
        type: 'citation',
        displayNumber: displayNumberByChunkId.get(chunkId),
        reference,
      });
    } else {
      // Marker in the text has no matching reference - fall back to
      // showing the raw text rather than silently dropping it.
      parts.push({ type: 'text', value: fullMatch });
    }

    lastIndex = match.index + fullMatch.length;
  }

  if (lastIndex < content.length) {
    parts.push({ type: 'text', value: content.slice(lastIndex) });
  }

  return (
    <p className="citation-text">
      {parts.map((part, i) => {
        if (part.type === 'text') {
          return <span key={i}>{part.value}</span>;
        }

        const isOpen = openIndex === i;

        return (
          <span className="citation-wrapper" key={i}>
            <button
              type="button"
              className="citation-marker"
              onClick={() => setOpenIndex(isOpen ? null : i)}
            >
              [{part.displayNumber}]
            </button>
            {isOpen && (
              <span className="citation-popover">
                <strong>{part.reference.filename}</strong>
                <span>
                  {part.reference.start_page === part.reference.end_page
                    ? `Page ${part.reference.start_page}`
                    : `Pages ${part.reference.start_page}–${part.reference.end_page}`}
                </span>
              </span>
            )}
          </span>
        );
      })}
    </p>
  );
}