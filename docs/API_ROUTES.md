# API Routes Reference

## Base URL
- Development: `http://localhost:8000`
- API Prefix: `/api/v1`
- Interactive Docs: `http://localhost:8000/docs` (Swagger UI)

---

## Table of Contents

1. [Health & System](#health--system)
2. [Workspaces](#workspaces)
3. [Documents](#documents)
4. [Chat](#chat)
5. [Flashcards](#flashcards)
6. [Notes](#notes)
7. [Knowledge Graph](#knowledge-graph)
8. [Search](#search)
9. [Preferences](#preferences)
10. [Agent Runs](#agent-runs)
11. [Workspace Members](#workspace-members)
12. [Authentication](#authentication)

---

## Health & System

### Health Check
**GET** `/health`

Check application health (database and Qdrant connections).

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "database": "connected",
  "qdrant": "connected"
}
```

**Error Response:** `503 Service Unavailable` (if database or Qdrant unavailable)

**cURL Example:**
```bash
curl http://localhost:8000/health
```

---

## Workspaces

### Create Workspace
**POST** `/api/v1/workspaces?owner_username={username}`

Create a new workspace.

**Query Parameters:**
- `owner_username` (string, required): Owner username (e.g., "shree6791")

**Request Body:**
```json
{
  "name": "My Workspace",
  "plan_tier": "free"
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Workspace",
  "plan_tier": "free",
  "owner_id": "550e8400-e29b-41d4-a716-446655440001",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Error Responses:**
- `400 Bad Request`: Missing `owner_username` parameter
- `404 Not Found`: User with provided username not found (suggest signing up first)

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/workspaces?owner_username=shree6791" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Workspace",
    "plan_tier": "free"
  }'
```

---

### List Workspaces
**GET** `/api/v1/workspaces?owner_id={user_id}`

List workspaces.

**Query Parameters:**
- `owner_id` (UUID, optional): Filter by owner user ID

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Workspace",
    "plan_tier": "free",
    "owner_id": "550e8400-e29b-41d4-a716-446655440001",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**cURL Example:**
```bash
# List all workspaces
curl "http://localhost:8000/api/v1/workspaces"

# List workspaces for a specific owner
curl "http://localhost:8000/api/v1/workspaces?owner_id=550e8400-e29b-41d4-a716-446655440001"
```

---

### Get Workspace
**GET** `/api/v1/workspaces/{workspace_id}`

Get a workspace by ID.

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Workspace",
  "plan_tier": "free",
  "owner_id": "550e8400-e29b-41d4-a716-446655440001",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/workspaces/550e8400-e29b-41d4-a716-446655440000"
```

---

### Update Workspace
**PATCH** `/api/v1/workspaces/{workspace_id}`

Update a workspace.

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Request Body:**
```json
{
  "name": "Updated Workspace Name",
  "plan_tier": "pro"
}
```

**Response:** `200 OK` (WorkspaceRead)

**cURL Example:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/workspaces/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Workspace Name",
    "plan_tier": "pro"
  }'
```

---

### Delete Workspace
**DELETE** `/api/v1/workspaces/{workspace_id}`

Delete a workspace (cascade deletes all related data).

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Response:** `204 No Content`

**cURL Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/workspaces/550e8400-e29b-41d4-a716-446655440000"
```

---

## Documents

### Create Document
**POST** `/api/v1/documents`

Create a new document in a workspace.

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "My Study Document",
  "doc_type": "pdf",
  "source_url": "https://example.com/document.pdf",
  "language": "en",
  "content": "Your document text content here...",
  "metadata": {}
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "My Study Document",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "My Study Document",
    "doc_type": "pdf",
    "source_url": "https://example.com/document.pdf",
    "language": "en",
    "content": "Your document text content here...",
    "metadata": {}
  }'
```

---

### Create Document (Workspace-scoped)
**POST** `/api/v1/workspaces/{workspace_id}/documents`

Create a new document in a specific workspace (alternative endpoint).

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Request Body:** Same as above (without workspace_id in body)

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/workspaces/550e8400-e29b-41d4-a716-446655440000/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "My Study Document",
    "doc_type": "pdf",
    "source_url": "https://example.com/document.pdf",
    "language": "en",
    "content": "Your document text content here...",
    "metadata": {}
  }'
```

---

### List Documents
**GET** `/api/v1/workspaces/{workspace_id}/documents`

List all documents in a workspace.

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Response:** `200 OK` (list of DocumentRead)

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/workspaces/550e8400-e29b-41d4-a716-446655440000/documents"
```

---

### Get Document
**GET** `/api/v1/documents/{document_id}`

Get a document by ID (includes status, summary_text, last_run_id).

**Path Parameters:**
- `document_id` (UUID): Document ID

**Response:** `200 OK` (DocumentRead)

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002"
```

---

### Update Document
**PATCH** `/api/v1/documents/{document_id}`

Update a document.

**Path Parameters:**
- `document_id` (UUID): Document ID

**Request Body:**
```json
{
  "title": "Updated Title",
  "doc_type": "pdf",
  "source_url": "https://example.com/updated.pdf",
  "language": "en",
  "metadata": {}
}
```

**Response:** `200 OK` (DocumentRead)

**cURL Example:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "doc_type": "pdf",
    "source_url": "https://example.com/updated.pdf",
    "language": "en",
    "metadata": {}
  }'
```

---

### Delete Document
**DELETE** `/api/v1/documents/{document_id}`

Delete a document (cascade deletes chunks, embeddings, etc.).

**Path Parameters:**
- `document_id` (UUID: Document ID

**Response:** `204 No Content`

**cURL Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002"
```

---

### Get Document Status
**GET** `/api/v1/documents/{document_id}/status`

Get document status (alias to document GET).

**Path Parameters:**
- `document_id` (UUID): Document ID

**Response:** `200 OK` (DocumentRead)

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002/status"
```

---

### Ingest Document
**POST** `/api/v1/documents/{document_id}/ingest`

Process a document: chunk it and generate embeddings. Always runs asynchronously in background.

**Path Parameters:**
- `document_id` (UUID): Document ID to process

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "raw_text": "Optional: additional text to store"
}
```

**Response:** `202 Accepted`
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "queued",
  "message": "Document ingestion queued. Check agent_runs table for status."
}
```

**Note:** Uses OpenAI embeddings (`text-embedding-3-small`) and optionally generates summary with `gpt-4o-mini`. Ingestion also happens automatically during document upload if `auto_ingest_on_upload=true` in user preferences.

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "raw_text": "Optional: additional text to store"
  }'
```

---

### Get Document Summary
**GET** `/api/v1/documents/{document_id}/summary`

Get document summary.

**Path Parameters:**
- `document_id` (UUID): Document ID

**Response:** `200 OK`
```json
{
  "summary": "This document discusses...",
  "document_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002/summary"
```

---

### Regenerate Document Summary
**POST** `/api/v1/documents/{document_id}/summary?max_bullets=7`

Generate or regenerate document summary using SummaryAgent. Always runs asynchronously in background.

**Path Parameters:**
- `document_id` (UUID): Document ID

**Query Parameters:**
- `max_bullets` (integer, default: `7`, range: 1-20): Maximum number of bullet points in summary

**Response:** `202 Accepted`

**Response (`202 Accepted`):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "queued",
  "message": "Summary generation queued. Check agent_runs table for status."
}
```

**Note:** Uses OpenAI `gpt-4o-mini` for summary generation via SummaryAgent. The agent uses semantic retrieval to find important chunks and generates a conservative, quality-aware summary. The summary is stored in the `documents.summary_text` column.

**cURL Example:**
```bash
# Summary generation (default 7 bullets)
curl -X POST "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002/summary"

# Summary generation with custom max_bullets
curl -X POST "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002/summary?max_bullets=10"
```

---

### Generate Flashcards
**POST** `/api/v1/documents/{document_id}/flashcards`

Generate flashcards from a document. Always runs asynchronously in background.

**Path Parameters:**
- `document_id` (UUID): Source document ID

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "mode": "key_terms"
}
```

**Request Body Parameters:**
- `mode` (string, required): `key_terms`, `qa`, or `cloze`

**Response:** `202 Accepted`
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440004",
  "status": "queued",
  "message": "Flashcard generation queued. Check agent_runs table for status."
}
```

**Note:** Uses OpenAI `gpt-4o-mini` for flashcard generation. Flashcards are also generated automatically after ingestion if `auto_flashcards_after_ingest=true` in user preferences.

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002/flashcards" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "mode": "key_terms"
  }'
```

---

### Extract Knowledge Graph
**POST** `/api/v1/documents/{document_id}/kg`

Extract concepts and relationships from a document. Always runs asynchronously in background.

**Path Parameters:**
- `document_id` (UUID): Source document ID

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Response:** `202 Accepted`
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "queued",
  "message": "KG extraction queued. Check agent_runs table for status."
}
```

**Note:** Uses OpenAI `gpt-4o-mini` for KG extraction. Concepts and relationships are stored in Qdrant vector database.

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002/kg" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

---

### Reindex Document Embeddings
**POST** `/api/v1/documents/{document_id}/reindex?embedding_model=default`

Delete old embeddings and regenerate with current embedding model.

**Path Parameters:**
- `document_id` (UUID): Document ID to reindex

**Query Parameters:**
- `embedding_model` (string, default: `"default"`): Embedding model to use

**Response:** `200 OK`
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440002",
  "embeddings_regenerated": 10,
  "status": "completed"
}
```

**Note:** Uses OpenAI `text-embedding-3-small` for embeddings.

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440002/reindex?embedding_model=default"
```

---

## Chat

### Chat with Study Assistant
**POST** `/api/v1/chat`

Ask questions about documents in your workspace.

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "message": "What is the main topic of this document?",
  "document_id": "550e8400-e29b-41d4-a716-446655440002",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440005",
  "previous_messages": [
    {"role": "user", "content": "Previous question"},
    {"role": "assistant", "content": "Previous answer"}
  ],
  "top_k": 8
}
```

**Response:** `200 OK`
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440006",
  "content": "The main topic is...",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "citations": [
      {
        "chunk_id": "550e8400-e29b-41d4-a716-446655440007",
        "document_id": "550e8400-e29b-41d4-a716-446655440002",
        "chunk_index": 0,
        "score": 0.95
      }
    ],
    "suggested_note": {
      "title": "Main Topic",
      "body": "...",
      "document_id": "550e8400-e29b-41d4-a716-446655440002"
    },
    "confidence_score": 0.9,
    "insufficient_info": false
  }
}
```

**Note:** Uses OpenAI `text-embedding-3-small` for query embeddings and `gpt-4o-mini` for answer generation.

**cURL Example:**
```bash
# Basic chat query
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "message": "What is the main topic of this document?",
    "document_id": "550e8400-e29b-41d4-a716-446655440002",
    "top_k": 8
  }'

# Chat with conversation history
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "message": "Can you give an example?",
    "document_id": "550e8400-e29b-41d4-a716-446655440002",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440005",
    "previous_messages": [
      {"role": "user", "content": "What is machine learning?"},
      {"role": "assistant", "content": "Machine learning is..."}
    ],
    "top_k": 8
  }'
```

---

## Flashcards

### List Flashcards
**GET** `/api/v1/flashcards?workspace_id={workspace_id}&document_id={document_id}&user_id={user_id}&limit=20&offset=0`

List flashcards, optionally filtered by document or user.

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `document_id` (UUID, optional): Filter by document ID
- `user_id` (UUID, optional): Filter by user ID
- `limit` (int, default: 20, max: 100): Maximum number of results
- `offset` (int, default: 0): Offset for pagination

**Response:** `200 OK` (list of FlashcardRead)

**cURL Example:**
```bash
# List all flashcards in workspace
curl "http://localhost:8000/api/v1/flashcards?workspace_id=550e8400-e29b-41d4-a716-446655440000&limit=20&offset=0"

# List flashcards for a specific document
curl "http://localhost:8000/api/v1/flashcards?workspace_id=550e8400-e29b-41d4-a716-446655440000&document_id=550e8400-e29b-41d4-a716-446655440002"

# List flashcards for a specific user
curl "http://localhost:8000/api/v1/flashcards?workspace_id=550e8400-e29b-41d4-a716-446655440000&user_id=550e8400-e29b-41d4-a716-446655440001"
```

---

### Get Flashcard
**GET** `/api/v1/flashcards/{flashcard_id}`

Get a flashcard by ID.

**Path Parameters:**
- `flashcard_id` (UUID): Flashcard ID

**Response:** `200 OK` (FlashcardRead)

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/flashcards/550e8400-e29b-41d4-a716-446655440009"
```

---

### Get Due Flashcards
**GET** `/api/v1/flashcards/due?workspace_id={workspace_id}&user_id={user_id}&limit=20`

Get flashcards due for review (SRS algorithm).

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `user_id` (UUID, required): User ID
- `limit` (int, default: 20, max: 100): Maximum number of results

**Response:** `200 OK` (list of FlashcardRead)

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/flashcards/due?workspace_id=550e8400-e29b-41d4-a716-446655440000&user_id=550e8400-e29b-41d4-a716-446655440001&limit=20"
```

---

### Review Flashcard
**POST** `/api/v1/flashcards/{flashcard_id}/review?force=false`

Record a flashcard review and update SRS state.

**Path Parameters:**
- `flashcard_id` (UUID): Flashcard ID

**Query Parameters:**
- `force` (boolean, default: `false`): Bypass due check and cooldown

**Request Body:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "grade": 2,
  "response_time_ms": 5000
}
```

**Grade Scale:**
- `0` = Again (forgot)
- `1` = Hard
- `2` = Good
- `3` = Easy
- `4` = Perfect

**Response:** `200 OK`
```json
{
  "review_id": "550e8400-e29b-41d4-a716-446655440008",
  "flashcard_id": "550e8400-e29b-41d4-a716-446655440009",
  "next_review_due": "2024-01-02T00:00:00Z",
  "interval_days": 1,
  "ease_factor": 2.5,
  "reviewed_at": "2024-01-01T00:00:00Z"
}
```

**cURL Example:**
```bash
# Normal review (respects due date and cooldown)
curl -X POST "http://localhost:8000/api/v1/flashcards/550e8400-e29b-41d4-a716-446655440009/review" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "grade": 2,
    "response_time_ms": 5000
  }'

# Force review (bypass due check and cooldown)
curl -X POST "http://localhost:8000/api/v1/flashcards/550e8400-e29b-41d4-a716-446655440009/review?force=true" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "grade": 4,
    "response_time_ms": 3000
  }'
```

---

## Notes

### Create Note
**POST** `/api/v1/notes?user_id={user_id}`

Create a new note.

**Query Parameters:**
- `user_id` (UUID, required): User ID

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "My Note",
  "body": "Note content...",
  "document_id": "550e8400-e29b-41d4-a716-446655440002",
  "note_type": "summary",
  "metadata": {}
}
```

**Response:** `201 Created` (NoteRead)

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/notes?user_id=550e8400-e29b-41d4-a716-446655440001" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "My Note",
    "body": "Note content...",
    "document_id": "550e8400-e29b-41d4-a716-446655440002",
    "note_type": "summary",
    "metadata": {}
  }'
```

---

### List Notes
**GET** `/api/v1/notes?workspace_id={workspace_id}&document_id={document_id}&user_id={user_id}`

List notes, optionally filtered by document or user.

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `document_id` (UUID, optional): Filter by document ID
- `user_id` (UUID, optional): Filter by user ID

**Response:** `200 OK` (list of NoteRead)

**cURL Example:**
```bash
# List all notes in workspace
curl "http://localhost:8000/api/v1/notes?workspace_id=550e8400-e29b-41d4-a716-446655440000"

# List notes for a specific document
curl "http://localhost:8000/api/v1/notes?workspace_id=550e8400-e29b-41d4-a716-446655440000&document_id=550e8400-e29b-41d4-a716-446655440002"

# List notes for a specific user
curl "http://localhost:8000/api/v1/notes?workspace_id=550e8400-e29b-41d4-a716-446655440000&user_id=550e8400-e29b-41d4-a716-446655440001"
```

---

### Get Note
**GET** `/api/v1/notes/{note_id}`

Get a note by ID.

**Path Parameters:**
- `note_id` (UUID): Note ID

**Response:** `200 OK` (NoteRead)

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/notes/550e8400-e29b-41d4-a716-446655440013"
```

---

### Update Note
**PATCH** `/api/v1/notes/{note_id}`

Update a note.

**Path Parameters:**
- `note_id` (UUID): Note ID

**Request Body:**
```json
{
  "title": "Updated Title",
  "body": "Updated content",
  "note_type": "summary",
  "metadata": {}
}
```

**Response:** `200 OK` (NoteRead)

**cURL Example:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/notes/550e8400-e29b-41d4-a716-446655440013" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "body": "Updated content",
    "note_type": "summary",
    "metadata": {}
  }'
```

---

### Delete Note
**DELETE** `/api/v1/notes/{note_id}`

Delete a note.

**Path Parameters:**
- `note_id` (UUID): Note ID

**Response:** `204 No Content`

**cURL Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/notes/550e8400-e29b-41d4-a716-446655440013"
```

---

## Knowledge Graph

### List Concepts
**GET** `/api/v1/kg/concepts?workspace_id={workspace_id}&document_id={document_id}&q={query}&limit=20&offset=0`

List concepts, optionally filtered by document or search query.

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `document_id` (UUID, optional): Filter by document ID
- `q` (string, optional): Search query (name/description)
- `limit` (int, default: 20, max: 100): Maximum number of results
- `offset` (int, default: 0): Offset for pagination

**Response:** `200 OK` (list of ConceptRead)

**cURL Example:**
```bash
# List all concepts in workspace
curl "http://localhost:8000/api/v1/kg/concepts?workspace_id=550e8400-e29b-41d4-a716-446655440000&limit=20&offset=0"

# Search concepts by name/description
curl "http://localhost:8000/api/v1/kg/concepts?workspace_id=550e8400-e29b-41d4-a716-446655440000&q=machine%20learning"

# Filter by document (when implemented)
curl "http://localhost:8000/api/v1/kg/concepts?workspace_id=550e8400-e29b-41d4-a716-446655440000&document_id=550e8400-e29b-41d4-a716-446655440002"
```

---

### Get Concept
**GET** `/api/v1/kg/concepts/{concept_id}`

Get a concept by ID.

**Path Parameters:**
- `concept_id` (UUID): Concept ID

**Response:** `200 OK` (ConceptRead)

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/kg/concepts/550e8400-e29b-41d4-a716-446655440014"
```

---

### Get Concept Neighbors
**GET** `/api/v1/kg/concepts/{concept_id}/neighbors?depth=1`

Get neighboring concepts up to specified depth.

**Path Parameters:**
- `concept_id` (UUID): Concept ID

**Query Parameters:**
- `depth` (int, default: 1, min: 1, max: 3): Traversal depth

**Response:** `200 OK` (list of ConceptRead)

**cURL Example:**
```bash
# Get neighbors at depth 1
curl "http://localhost:8000/api/v1/kg/concepts/550e8400-e29b-41d4-a716-446655440014/neighbors?depth=1"

# Get neighbors at depth 2
curl "http://localhost:8000/api/v1/kg/concepts/550e8400-e29b-41d4-a716-446655440014/neighbors?depth=2"
```

---

### List KG Edges
**GET** `/api/v1/kg/edges?workspace_id={workspace_id}&concept_id={concept_id}&limit=20&offset=0`

List KG edges, optionally filtered by concept.

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `concept_id` (UUID, optional): Filter by concept ID (src or dst)
- `limit` (int, default: 20, max: 100): Maximum number of results
- `offset` (int, default: 0): Offset for pagination

**Response:** `200 OK` (list of EdgeRead)

**cURL Example:**
```bash
# List all edges in workspace
curl "http://localhost:8000/api/v1/kg/edges?workspace_id=550e8400-e29b-41d4-a716-446655440000&limit=20&offset=0"

# List edges for a specific concept
curl "http://localhost:8000/api/v1/kg/edges?workspace_id=550e8400-e29b-41d4-a716-446655440000&concept_id=550e8400-e29b-41d4-a716-446655440014"
```

---

## Search

### Semantic Search
**POST** `/api/v1/search`

Perform semantic search across workspace documents.

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "machine learning algorithms",
  "top_k": 8,
  "document_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**Response:** `200 OK`
```json
{
  "results": [
    {
      "chunk_id": "550e8400-e29b-41d4-a716-446655440010",
      "document_id": "550e8400-e29b-41d4-a716-446655440002",
      "chunk_index": 5,
      "score": 0.92,
      "snippet": "Machine learning algorithms are..."
    }
  ],
  "query": "machine learning algorithms",
  "total": 1
}
```

**Note:** Uses OpenAI `text-embedding-3-small` for query embeddings.

**cURL Example:**
```bash
# Search across all documents in workspace
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "machine learning algorithms",
    "top_k": 8
  }'

# Search within a specific document
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "neural networks",
    "top_k": 5,
    "document_id": "550e8400-e29b-41d4-a716-446655440002"
  }'
```

---

## Preferences

### Get User Preferences
**GET** `/api/v1/preferences?user_id={user_id}&workspace_id={workspace_id}`

Get user preferences, creating defaults if not exists.

**Query Parameters:**
- `user_id` (UUID, required): User ID
- `workspace_id` (UUID, optional): Workspace ID

**Response:** `200 OK`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "auto_ingest_on_upload": true,
  "auto_summary_after_ingest": true,
  "auto_flashcards_after_ingest": true,
  "default_flashcard_mode": "qa"
}
```

**cURL Example:**
```bash
# Get preferences for a user
curl "http://localhost:8000/api/v1/preferences?user_id=550e8400-e29b-41d4-a716-446655440001"

# Get workspace-specific preferences
curl "http://localhost:8000/api/v1/preferences?user_id=550e8400-e29b-41d4-a716-446655440001&workspace_id=550e8400-e29b-41d4-a716-446655440000"
```

---

### Update User Preferences
**PATCH** `/api/v1/preferences?user_id={user_id}&workspace_id={workspace_id}`

Update user preferences.

**Query Parameters:**
- `user_id` (UUID, required): User ID
- `workspace_id` (UUID, optional): Workspace ID

**Request Body:**
```json
{
  "auto_ingest_on_upload": false,
  "auto_summary_after_ingest": true,
  "auto_flashcards_after_ingest": true,
  "default_flashcard_mode": "key_terms"
}
```

**Response:** `200 OK` (PreferenceRead)

**cURL Example:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/preferences?user_id=550e8400-e29b-41d4-a716-446655440001&workspace_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "auto_ingest_on_upload": false,
    "auto_summary_after_ingest": true,
    "auto_flashcards_after_ingest": true,
    "default_flashcard_mode": "key_terms"
  }'
```

---

## Agent Runs

### Get Agent Run
**GET** `/api/v1/agent-runs/{run_id}`

Get an agent run by ID (includes step-by-step progress logs).

**Path Parameters:**
- `run_id` (UUID): Agent run ID

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440011",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "agent_name": "ingestion",
  "status": "completed",
  "input": {...},
  "output": {...},
  "error": null,
  "steps": [
    {
      "step_name": "chunk",
      "step_status": "completed",
      "details": {"chunks_created": 10},
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ],
  "started_at": "2024-01-01T00:00:00Z",
  "finished_at": "2024-01-01T00:01:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/agent-runs/550e8400-e29b-41d4-a716-446655440011"
```

---

### List Agent Runs
**GET** `/api/v1/agent-runs?workspace_id={workspace_id}&user_id={user_id}&agent_name={agent_name}&status={status}&limit=20&offset=0`

List agent runs, optionally filtered by workspace, user, agent, or status.

**Query Parameters:**
- `workspace_id` (UUID, optional): Filter by workspace ID
- `user_id` (UUID, optional): Filter by user ID
- `agent_name` (string, optional): Filter by agent name (`ingestion`, `study_chat`, `flashcard`, `kg_extraction`)
- `status` (string, optional): Filter by status (`queued`, `running`, `completed`, `failed`)
- `limit` (int, default: 20, max: 100): Maximum number of results
- `offset` (int, default: 0): Offset for pagination

**Response:** `200 OK` (list of AgentRunRead)

**cURL Example:**
```bash
# List all agent runs
curl "http://localhost:8000/api/v1/agent-runs?limit=20&offset=0"

# Filter by workspace
curl "http://localhost:8000/api/v1/agent-runs?workspace_id=550e8400-e29b-41d4-a716-446655440000"

# Filter by user
curl "http://localhost:8000/api/v1/agent-runs?user_id=550e8400-e29b-41d4-a716-446655440001"

# Filter by agent name
curl "http://localhost:8000/api/v1/agent-runs?agent_name=ingestion"

# Filter by status
curl "http://localhost:8000/api/v1/agent-runs?status=completed"

# Combined filters
curl "http://localhost:8000/api/v1/agent-runs?workspace_id=550e8400-e29b-41d4-a716-446655440000&agent_name=flashcard&status=running"
```

---

## Workspace Members

### Add Workspace Member
**POST** `/api/v1/workspaces/{workspace_id}/members`

Add a member to a workspace.

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Request Body:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440012",
  "role": "member",
  "status": "active"
}
```

**Roles:** `owner`, `admin`, `member`

**Response:** `201 Created` (WorkspaceMemberRead)

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/workspaces/550e8400-e29b-41d4-a716-446655440000/members" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440012",
    "role": "member",
    "status": "active"
  }'
```

---

### List Workspace Members
**GET** `/api/v1/workspaces/{workspace_id}/members`

List all members of a workspace.

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Response:** `200 OK` (list of WorkspaceMemberRead)

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/workspaces/550e8400-e29b-41d4-a716-446655440000/members"
```

---

### Remove Workspace Member
**DELETE** `/api/v1/workspaces/{workspace_id}/members/{member_id}`

Remove a member from a workspace.

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID
- `member_id` (UUID): Membership ID

**Response:** `204 No Content`

**cURL Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/workspaces/550e8400-e29b-41d4-a716-446655440000/members/550e8400-e29b-41d4-a716-446655440015"
```

---

## Authentication

Authentication endpoints support both Google Sign-In and username/password authentication. When a user is created (via signup or first-time Google login), default user preferences are automatically created.

### Signup (Email/Password)
**POST** `/api/v1/auth/signup`

Create a new user account with username, email and password. Automatically creates default user preferences.

**Request Body:**
```json
{
  "username": "shree6791",
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe",
  "display_name": "John"
}
```

**Response:** `201 Created`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "username": "shree6791",
  "email": "user@example.com",
  "full_name": "John Doe",
  "display_name": "John",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Note:** Password hashing and JWT token generation are placeholders (TODO: implement with bcrypt and python-jose).

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "shree6791",
    "email": "user@example.com",
    "password": "password123",
    "full_name": "John Doe",
    "display_name": "John"
  }'
```

---

### Login (Email/Password)
**POST** `/api/v1/auth/login`

Login with email and password. If user doesn't exist, creates user automatically (first-time login).

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:** `200 OK`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "email": "user@example.com",
  "full_name": "John Doe",
  "display_name": "John",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Note:** Password verification and JWT token generation are placeholders (TODO: implement).

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

---

### Google Sign-In
**POST** `/api/v1/auth/google`

Authenticate with Google Sign-In. Verifies Google ID token and creates/updates user. Automatically creates default user preferences for new users.

**Request Body:**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6Ij...",
  "email": "user@gmail.com",
  "full_name": "John Doe",
  "display_name": "John"
}
```

**Response:** `201 Created` (new user) or `200 OK` (existing user)
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "email": "user@gmail.com",
  "full_name": "John Doe",
  "display_name": "John",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Note:** Google ID token verification and JWT token generation are placeholders (TODO: implement with google-auth and python-jose).

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/google" \
  -H "Content-Type: application/json" \
  -d '{
    "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6Ij...",
    "email": "user@gmail.com",
    "full_name": "John Doe",
    "display_name": "John"
  }'
```

---

### Logout
**POST** `/api/v1/auth/logout`

Logout endpoint. With JWT tokens, logout is typically handled client-side by removing the token.

**Response:** `200 OK`
```json
{
  "message": "Logged out successfully"
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout"
```

---

### Get Current User
**GET** `/api/v1/auth/me?user_id={user_id}`

Get current authenticated user information.

**Query Parameters:**
- `user_id` (UUID, required): User ID (TODO: Extract from JWT token instead of query parameter)

**Response:** `200 OK`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "email": "user@example.com",
  "full_name": "John Doe",
  "display_name": "John",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Note:** Currently requires `user_id` query parameter. TODO: Extract from JWT token in Authorization header.

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/auth/me?user_id=550e8400-e29b-41d4-a716-446655440001"
```

---

## Complete Testing Flow

### Step 0: Sign Up / Login (Optional)
```bash
# Sign up with email/password
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "shree6791",
    "email": "user@example.com",
    "password": "password123",
    "full_name": "Test User"
  }'

# Or login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'

# Save the username from the response for subsequent requests (e.g., "shree6791")
```

**Note:** When a user signs up or logs in for the first time, default user preferences are automatically created. Use the `username` from the response for workspace creation.

### Step 1: Health Check
```bash
curl http://localhost:8000/health
```

### Step 2: Create a Workspace
```bash
curl -X POST "http://localhost:8000/api/v1/workspaces?owner_username=shree6791" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Study Workspace",
    "plan_tier": "free"
  }'
```

**Save the `workspace_id` from the response.**

### Step 3: Create a Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "{workspace_id}",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "Introduction to Machine Learning",
    "doc_type": "pdf",
    "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data. It enables computers to improve their performance on a task through experience without being explicitly programmed for every scenario."
  }'
```

**Save the `document_id` from the response.**

### Step 4: Ingest the Document (if not auto-ingested)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "{workspace_id}",
    "user_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

**Note:** Ingestion happens automatically during document upload if `auto_ingest_on_upload=true`. Ingestion always runs asynchronously.

### Step 5: Chat with the Document
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "{workspace_id}",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "message": "What is machine learning?",
    "document_id": "{document_id}"
  }'
```

### Step 6: Generate Flashcards (Optional)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/flashcards" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "{workspace_id}",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "mode": "key_terms"
  }'
```

**Note:** Flashcard generation always runs asynchronously. The response includes a `run_id` for tracking.

### Step 7: Extract Knowledge Graph (Optional)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/kg" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "{workspace_id}",
    "user_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

**Note:** KG extraction always runs asynchronously. The response includes a `run_id` for tracking.
    "mode": "key_terms"
  }'
```

### Step 7: Extract Knowledge Graph (Optional)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/kg" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "{workspace_id}",
    "user_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

**Note:** KG extraction always runs asynchronously. The response includes a `run_id` for tracking.

### Step 8: Review Flashcards (Optional)
```bash
curl -X POST "http://localhost:8000/api/v1/flashcards/{flashcard_id}/review" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "workspace_id": "{workspace_id}",
    "grade": 2,
    "response_time_ms": 5000
  }'
```

---

## Notes

1. **UUIDs**: Replace all UUID placeholders with actual UUIDs from your database
2. **Workspace & User IDs**: You need valid `workspace_id` and `user_id` values
3. **Async Operations**: All document processing endpoints (ingest, summary, flashcards, KG extraction) run asynchronously by default. Responses include a `run_id` for tracking status.
4. **OpenAPI Docs**: Visit `http://localhost:8000/api/v1/openapi.json` or `http://localhost:8000/docs` for interactive API documentation
5. **OpenAI Usage**: Routes that use OpenAI are marked with notes. See `OPENAI_SETUP_GUIDE.md` for details
6. **Error Responses**: All endpoints return standard error responses with `ErrorResponse` schema:
   ```json
   {
     "detail": "Error message here"
   }
   ```

---

## Route Summary

| Category | Routes | Count |
|----------|--------|-------|
| Health & System | `/health` | 1 |
| Workspaces | CRUD operations | 5 |
| Documents | CRUD + processing | 13 |
| Chat | Chat endpoint | 1 |
| Flashcards | List, Get, Due, Review | 4 |
| Notes | CRUD operations | 5 |
| Knowledge Graph | Concepts, Edges, Neighbors | 4 |
| Search | Semantic search | 1 |
| Preferences | Get, Update | 2 |
| Agent Runs | Get, List | 2 |
| Workspace Members | Add, List, Remove | 3 |
| Authentication | Signup, Login, Google, Logout, Me | 5 |
| **Total** | | **46 routes** |
