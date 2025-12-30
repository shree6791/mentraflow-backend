# API Routes Reference

## Base URL
- Development: `http://localhost:8000`
- API Prefix: `/api/v1`
- Interactive Docs: `http://localhost:8000/docs` (Swagger UI)

## Authentication

**Most endpoints require JWT authentication.** Include the JWT token in the `Authorization` header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

To obtain a JWT token:
1. **Sign up**: `POST /api/v1/auth/signup` (returns `access_token`)
2. **Login**: `POST /api/v1/auth/login` (returns `access_token`)
3. **Google Sign-In**: `POST /api/v1/auth/google` (returns `access_token`)

See the [Authentication](#authentication) section below for detailed endpoint documentation.

**Important:** All protected endpoints automatically filter results to show only data belonging to the authenticated user. You no longer need to pass `user_id` as a query parameter or in request bodies.

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
**POST** `/api/v1/workspaces`

Create a new workspace for the authenticated user.

**Authentication:** Required (JWT token in Authorization header)

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

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/workspaces" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Workspace",
    "plan_tier": "free"
  }'
```

---

### List Workspaces
**GET** `/api/v1/workspaces`

List workspaces for the authenticated user.

**Authentication:** Required (JWT token in Authorization header)

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

**Note:** Results are automatically filtered to show only workspaces owned by the authenticated user.

**cURL Example:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/workspaces"
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
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
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

Create a new document in a workspace for the authenticated user.

**Authentication:** Required (JWT token in Authorization header)

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "My Study Document",
  "doc_type": "pdf",
  "source_url": "https://example.com/document.pdf",
  "language": "en",
  "content": "Your document text content here...",
  "metadata": {}
}
```

**Note:** Supports both JSON (text content) and multipart/form-data (file upload). See [Document Upload Testing](./DOCUMENT_UPLOAD_TESTING.md) for details.

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
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
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
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
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
  "mode": "mcq"
}
```

**Request Body Parameters:**
- `mode` (string, required): `qa` or `mcq` (default: `mcq`)

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
    "mode": "mcq"
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
**GET** `/api/v1/flashcards?workspace_id={workspace_id}&document_id={document_id}&limit=20&offset=0`

List flashcards for the authenticated user, optionally filtered by workspace and/or document.

**Authentication:** Required (JWT token in Authorization header)

**Query Parameters:**
- `workspace_id` (UUID, optional): Workspace ID. If not provided, will be inferred from `document_id`
- `document_id` (UUID, optional): Filter by document ID. If provided without `workspace_id`, the workspace will be automatically determined from the document
- `limit` (int, default: 20, max: 100): Maximum number of results
- `offset` (int, default: 0): Offset for pagination

**Note:** At least one of `workspace_id` or `document_id` must be provided.

**Response:** `200 OK` (list of FlashcardRead)

**cURL Example:**
```bash
# List all flashcards in workspace
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/flashcards?workspace_id=550e8400-e29b-41d4-a716-446655440000&limit=20&offset=0"

# List flashcards for a specific document (workspace_id inferred automatically)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/flashcards?document_id=550e8400-e29b-41d4-a716-446655440002"

# List flashcards with both workspace and document filters
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/flashcards?workspace_id=550e8400-e29b-41d4-a716-446655440000&document_id=550e8400-e29b-41d4-a716-446655440002"
```

---

### Get Flashcard
**GET** `/api/v1/flashcards/{flashcard_id}`

Get a flashcard by ID. Only accessible by the flashcard owner.

**Authentication:** Required (JWT token in Authorization header)

**Path Parameters:**
- `flashcard_id` (UUID): Flashcard ID

**Response:** `200 OK` (FlashcardRead)

**Error Responses:**
- `403 Forbidden`: User doesn't have permission to access this flashcard
- `404 Not Found`: Flashcard not found

**cURL Example:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/flashcards/550e8400-e29b-41d4-a716-446655440009"
```

---

### Get Due Flashcards
**GET** `/api/v1/flashcards/due?workspace_id={workspace_id}&limit=20`

Get flashcards due for review (SRS algorithm) for the authenticated user.

**Authentication:** Required (JWT token in Authorization header)

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `limit` (int, default: 20, max: 100): Maximum number of results

**Response:** `200 OK` (list of FlashcardRead)

**cURL Example:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/flashcards/due?workspace_id=550e8400-e29b-41d4-a716-446655440000&limit=20"
```

---

### Review Flashcard
**POST** `/api/v1/flashcards/{flashcard_id}/review?force=false`

Record a flashcard review and update SRS state. Only accessible by the flashcard owner.

**Authentication:** Required (JWT token in Authorization header)

**Path Parameters:**
- `flashcard_id` (UUID): Flashcard ID

**Query Parameters:**
- `force` (boolean, default: `false`): Bypass due check and cooldown

**Request Body:**
```json
{
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
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "grade": 2,
    "response_time_ms": 5000
  }'

# Force review (bypass due check and cooldown)
curl -X POST "http://localhost:8000/api/v1/flashcards/550e8400-e29b-41d4-a716-446655440009/review?force=true" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "grade": 4,
    "response_time_ms": 3000
  }'
```

---

## Notes

### Create Note
**POST** `/api/v1/notes`

Create a new note for the authenticated user.

**Authentication:** Required (JWT token in Authorization header)

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
curl -X POST "http://localhost:8000/api/v1/notes" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
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
**GET** `/api/v1/notes?workspace_id={workspace_id}&document_id={document_id}`

List notes, optionally filtered by document or user.

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `document_id` (UUID, optional): Filter by document ID

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
**GET** `/api/v1/preferences?workspace_id={workspace_id}`

Get user preferences, creating defaults if not exists.

**Query Parameters:**
- `workspace_id` (UUID, optional): Workspace ID

**Response:** `200 OK`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "auto_ingest_on_upload": true,
  "auto_summary_after_ingest": true,
  "auto_flashcards_after_ingest": true,
  "auto_kg_after_ingest": true,
  "default_flashcard_mode": "mcq"
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
- `workspace_id` (UUID, optional): Workspace ID

**Request Body:**
```json
{
  "auto_ingest_on_upload": false,
  "auto_summary_after_ingest": true,
  "auto_flashcards_after_ingest": true,
  "auto_kg_after_ingest": true,
  "default_flashcard_mode": "mcq"
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
    "auto_kg_after_ingest": true,
    "default_flashcard_mode": "mcq"
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
**GET** `/api/v1/agent-runs?workspace_id={workspace_id}&agent_name={agent_name}&status={status}&limit=20&offset=0`

List agent runs for the authenticated user, optionally filtered by workspace, agent, or status.

**Authentication:** Required (JWT token in Authorization header)

**Query Parameters:**
- `workspace_id` (UUID, optional): Filter by workspace ID
- `agent_name` (string, optional): Filter by agent name (`ingestion`, `study_chat`, `flashcard`, `kg_extraction`)
- `status` (string, optional): Filter by status (`queued`, `running`, `completed`, `failed`)
- `limit` (int, default: 20, max: 100): Maximum number of results
- `offset` (int, default: 0): Offset for pagination

**Note:** Results are automatically filtered to show only agent runs for the authenticated user.

**Response:** `200 OK` (list of AgentRunRead)

**cURL Example:**
```bash
# List all agent runs for authenticated user
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/agent-runs?limit=20&offset=0"

# Filter by workspace
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/agent-runs?workspace_id=550e8400-e29b-41d4-a716-446655440000"

# Filter by agent name
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/agent-runs?agent_name=ingestion"

# Filter by status
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/agent-runs?status=completed"

# Combined filters
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/agent-runs?workspace_id=550e8400-e29b-41d4-a716-446655440000&agent_name=flashcard&status=running"
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

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

**Rate Limiting:** 5 requests per minute per IP

**Note:** ✅ Fully implemented with bcrypt password hashing and JWT token generation.

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

**Rate Limiting:** 10 requests per minute per IP (prevents brute force attacks)

**Note:** ✅ Fully implemented with bcrypt password verification and JWT token generation.

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

**Note:** ✅ Fully implemented with google-auth token verification and JWT token generation. Requires `GOOGLE_CLIENT_ID` in environment variables.

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

### Get Current User
**GET** `/api/v1/auth/me`

Get the current authenticated user from JWT token. Requires authentication.

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Response:** `200 OK`
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

**cURL Example:**
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "http://localhost:8000/api/v1/auth/me"
```

---

### Forgot Password
**POST** `/api/v1/auth/forgot-password`

Request a password reset. Generates a reset token (valid for 1 hour). In production, this token should be sent via email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:** `200 OK`
```json
{
  "message": "If an account with that email exists, a password reset link has been sent.",
  "reset_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": "1 hour",
  "note": "Use this token with /auth/reset-password endpoint. In production, send via email."
}
```

**Rate Limiting:** 3 requests per hour per IP

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

---

### Reset Password
**POST** `/api/v1/auth/reset-password`

Reset password using reset token.

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "new_password": "NewSecurePass123!"
}
```

**Password Requirements:** Same as signup (8+ chars, uppercase, lowercase, number, special char)

**Response:** `200 OK`
```json
{
  "message": "Password has been reset successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "email": "user@example.com"
}
```

**Rate Limiting:** 5 requests per hour per IP

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "new_password": "NewSecurePass123!"
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

## Authentication & Authorization

**All protected endpoints require JWT authentication:**

Include the access token in the `Authorization` header:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Protected endpoints:** All endpoints except:
- `/health` and `/api/v1/health`
- `/api/v1/version`
- `/api/v1/auth/signup`
- `/api/v1/auth/login`
- `/api/v1/auth/google`
- `/api/v1/auth/forgot-password`
- `/api/v1/auth/reset-password`
- `/api/v1/users/by-username/{username}` (public user lookup)

**Authorization:** Users can only access/modify their own resources (notes, flashcards, documents they created) or resources in workspaces they belong to.

---

### Get Current User
**GET** `/api/v1/auth/me`

Get current authenticated user information.

**Authentication:** Required (JWT token in Authorization header)

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "username": "shree6791",
  "email": "user@example.com",
  "full_name": "John Doe",
  "display_name": "John",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**cURL Example:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/auth/me"
```

---

## Complete Testing Flow

### Step 0: Sign Up / Login (Required)
```bash
# Sign up with email/password
SIGNUP_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "shree6791",
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }')

# Extract access token (save this for all subsequent requests)
ACCESS_TOKEN=$(echo $SIGNUP_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

# Or login if you already have an account
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }')
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")
```

**Note:** When a user signs up or logs in for the first time, default user preferences are automatically created. Save the `access_token` from the response for all subsequent authenticated requests.

### Step 1: Health Check
```bash
curl http://localhost:8000/health
```

### Step 2: Create a Workspace
```bash
WORKSPACE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/workspaces" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Study Workspace",
    "plan_tier": "free"
  }')

# Extract workspace_id
WORKSPACE_ID=$(echo $WORKSPACE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")
```

**Save the `workspace_id` from the response.**

### Step 3: Create a Document
```bash
DOC_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/workspaces/$WORKSPACE_ID/documents" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "'$WORKSPACE_ID'",
    "title": "Introduction to Machine Learning",
    "doc_type": "text",
    "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data. It enables computers to improve their performance on a task through experience without being explicitly programmed for every scenario."
  }')

# Extract document_id
DOCUMENT_ID=$(echo $DOC_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")
```

**Save the `document_id` from the response.**

### Step 4: Ingest the Document (if not auto-ingested)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/$DOCUMENT_ID/ingest" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "'$WORKSPACE_ID'"
  }'
```

**Note:** Ingestion happens automatically during document upload if `auto_ingest_on_upload=true`. Ingestion always runs asynchronously.

### Step 5: Chat with the Document
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "'$WORKSPACE_ID'",
    "message": "What is machine learning?",
    "document_id": "'$DOCUMENT_ID'"
  }'
```

### Step 6: Generate Flashcards (Optional)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/$DOCUMENT_ID/flashcards" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "'$WORKSPACE_ID'",
    "mode": "mcq"
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
| Authentication | Signup, Login, Google, Logout, Me, Forgot Password, Reset Password | 7 |
| **Total** | | **48 routes** |
