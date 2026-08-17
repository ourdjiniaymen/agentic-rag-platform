# Agentic RAG Platform — v1 Frontend Requirements

## Goal
Consume the already-complete v1 API (see `API.md`) with react js
UI. Same principle as the backend: genuinely usable end-to-end, not a
demo of one isolated screen.

## In scope for v1

**Project**
- Single project only - `project_id` is fixed (matches the backend's
  seeded single project, `DECISIONS.md` 011). No project switcher, no
  project creation/settings UI.

**Document upload & list**
- File picker restricted to PDF, upload button.
- Upload is a single synchronous request that can take a while (`hi_res`
  partitioning, `DECISIONS.md` 006/012) - show a clear loading/in-progress
  state for the duration, not just a spinner with no explanation.
- On completion, show the result: `status` (`indexed`/`failed`),
  `chunk_count`, filename, page count.
- Document list: all documents in the project, with filename, status
  badge, page count, chunk count, upload date.
- Surface upload errors distinctly: non-PDF (400), invalid/corrupt PDF
  (400), duplicate upload (409 - show which existing document it
  duplicates), unknown project (404, shouldn't happen in practice but
  handle it).

**Conversations & chat**
- Conversation list for the project; create a new conversation
  (optional title).
- Chat view: send a message, see the full conversation history
  (user/assistant turns in order).
- Sending a message is a blocking request (no streaming - the API
  returns the full answer at once, `DECISIONS.md` 009/010) - show a
  clear waiting state, this can take several seconds.
- Render assistant answers' `[chunk_N]` citation markers as visible
  references, not raw bracket text - e.g. superscript/footnote style,
  clickable to reveal the source: filename + page range (from the
  message's `references` array, not by re-deriving anything).
- Uncited answers (`references: null`) render normally, no citation UI.
- Handle a failed chat turn (500, per `DECISIONS.md` 019) gracefully -
  clear error state, retry affordance. The failed question is not
  persisted server-side (rolled back), so don't show it as a sent
  message that silently vanished.

**Error/empty states**
- Empty document list, empty conversation list, empty message list -
  each needs a real empty state, not a blank screen.
- 404s (unknown project/conversation) shouldn't happen through normal
  navigation, but the UI shouldn't break silently if they do.

## Explicitly out of scope for v1 (deferred, not forgotten)
- Multi-project UI, project creation/settings
- Streaming/typewriter-style answer rendering (backend doesn't stream)
- Editing or deleting documents/conversations/messages (no such
  endpoints exist yet)
- Real-time updates (polling, websockets) - single-user, one browser tab
- Auth/login UI (`DECISIONS.md` 011 - no login flow in v1)
- Advanced retrieval controls (top_k, threshold, RAG strategy) -
  project-settings concept doesn't exist yet (`DECISIONS.md` 003 ER note)
- Dark mode / extensive theming polish - clean and usable, not a design
  showcase

## Definition of done for v1 frontend
From the UI alone (no curl/Postman needed), a user can:
1. Upload a PDF and see its processing result (indexed or failed)
2. See it in the document list
3. Start a conversation and ask a question
4. See the assistant's answer with visible, clickable citations back to
   the source document and page

## Open questions to resolve before/during build
- Exact citation UI treatment (inline superscript vs. end-of-message
  footnote list vs. hover tooltip) - a design decision, not yet made.
- How long to show the upload-in-progress state before treating it as
  "taking too long" (no timeout exists server-side yet, per
  `DECISIONS.md` 006/018 gaps).
