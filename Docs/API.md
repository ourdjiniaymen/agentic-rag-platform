# v1 API Reference

Base URL (dev): `http://localhost:8000`

No auth (`DECISIONS.md` 011). Single seeded project: `project_id = 1`.

---

## Health

`GET /health` → `{"status": "ok"}`

---

## Documents

### `POST /projects/{project_id}/documents`
Multipart upload, field name `file`, PDF only. Synchronous - runs the
full ingestion pipeline (partition → chunk → embed → store,
`DECISIONS.md` 006) before responding. Can take a while.

**Response `201`** (`DocumentRead`) - on both success and pipeline
failure (`DECISIONS.md` 013):
```json
{
  "id": 1,
  "project_id": 1,
  "filename": "sample.pdf",
  "file_type": "application/pdf",
  "file_size_bytes": 12345,
  "page_count": 10,
  "title": "sample",
  "status": "indexed",           // or "processing" transiently, or "failed"
  "checksum": "sha256 hex",
  "chunk_count": 42,             // 0 if status is "failed"
  "created_at": "2026-08-10T12:00:00Z",
  "updated_at": "2026-08-10T12:00:05Z"
}
```

**Errors:**
- `400` - not a PDF, or file failed to parse as a valid PDF, or empty file
- `404` - project not found
- `409` - duplicate upload (same checksum already exists in this project);
  `detail` names the existing document's id/filename/status

### `GET /projects/{project_id}/documents`
List all documents in the project, ordered by upload time.

**Response `200`**: `DocumentRead[]` (same shape as above, empty array if none)

**Errors:** `404` - project not found

---

## Conversations

### `POST /projects/{project_id}/conversations`
**Request:**
```json
{"title": "optional string or null"}
```

**Response `201`** (`ConversationRead`):
```json
{
  "id": 1,
  "project_id": 1,
  "title": "optional string or null",
  "created_at": "2026-08-10T12:00:00Z",
  "updated_at": "2026-08-10T12:00:00Z"
}
```

**Errors:** `404` - project not found

### `GET /projects/{project_id}/conversations`
**Response `200`**: `ConversationRead[]`, ordered by creation time.

**Errors:** `404` - project not found

---

## Messages

### `POST /conversations/{conversation_id}/messages`
Ask a question. Blocking - embeds the query, retrieves chunks, calls the
LLM, and returns the full assistant answer in one response. No
streaming. Persists both the user's question and the assistant's reply
server-side.

**Request:**
```json
{"content": "What does the document say about X?"}
```

**Response `201`** (`MessageRead` - the **assistant's** message, not the
user's):
```json
{
  "id": 2,
  "conversation_id": 1,
  "role": "assistant",
  "content": "The document states that... [chunk_42]",
  "references": [
    {
      "chunk_id": 42,
      "filename": "sample.pdf",
      "file_type": "application/pdf",
      "file_path": "/app/storage/1/1/sample.pdf",
      "start_page": 3,
      "end_page": 4
    }
  ],
  "created_at": "2026-08-10T12:00:10Z"
}
```
`references` is `null` if the answer didn't cite anything (e.g. a
greeting, or an out-of-scope question the model declined to answer from
outside knowledge - `DECISIONS.md` prompt-flexibility note).

Citation markers (`[chunk_N]`) appear literally in `content` - the
frontend is responsible for rendering them as visible citations using
the `references` array, not stripping or re-parsing them itself.

**Errors:**
- `404` - conversation not found
- `500` - chat turn failed (LLM/embedding error). The user's question is
  rolled back, not persisted (`DECISIONS.md` 019) - safe to let the user
  retry the same message.

### `GET /conversations/{conversation_id}/messages`
Full history for a conversation, both roles, in order.

**Response `200`**: `MessageRead[]` (user messages have `references: null`
always - only assistant messages carry citations)

**Errors:** `404` - conversation not found

---

## Enums

- `Document.status`: `pending` | `processing` | `indexed` | `failed`
- `Message.role`: `user` | `assistant`
