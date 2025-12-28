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
12. [Authentication](#authentication-stubs)

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

---

## Workspaces

### Create Workspace
**POST** `/api/v1/workspaces?owner_user_id={user_id}`

Create a new workspace.

**Query Parameters:**
- `owner_user_id` (UUID, required): Owner user ID

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

---

### List Workspaces
**GET** `/api/v1/workspaces?owner_user_id={user_id}`

List workspaces.

**Query Parameters:**
- `owner_user_id` (UUID, optional): Filter by owner

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

---

### Delete Workspace
**DELETE** `/api/v1/workspaces/{workspace_id}`

Delete a workspace (cascade deletes all related data).

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Response:** `204 No Content`

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
  "created_by": "550e8400-e29b-41d4-a716-446655440001",
  "title": "My Study Document",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### Create Document (Workspace-scoped)
**POST** `/api/v1/workspaces/{workspace_id}/documents`

Create a new document in a specific workspace (alternative endpoint).

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Request Body:** Same as above (without workspace_id in body)

---

### List Documents
**GET** `/api/v1/workspaces/{workspace_id}/documents`

List all documents in a workspace.

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Response:** `200 OK` (list of DocumentRead)

---

### Get Document
**GET** `/api/v1/documents/{document_id}`

Get a document by ID (includes status, summary_text, last_run_id).

**Path Parameters:**
- `document_id` (UUID): Document ID

**Response:** `200 OK` (DocumentRead)

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

---

### Delete Document
**DELETE** `/api/v1/documents/{document_id}`

Delete a document (cascade deletes chunks, embeddings, etc.).

**Path Parameters:**
- `document_id` (UUID: Document ID

**Response:** `204 No Content`

---

### Get Document Status
**GET** `/api/v1/documents/{document_id}/status`

Get document status (alias to document GET).

**Path Parameters:**
- `document_id` (UUID): Document ID

**Response:** `200 OK` (DocumentRead)

---

### Ingest Document
**POST** `/api/v1/documents/{document_id}/ingest?async=false`

Process a document: chunk it and generate embeddings.

**Path Parameters:**
- `document_id` (UUID): Document ID to process

**Query Parameters:**
- `async` (boolean, default: `false`): Run in background

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "raw_text": "Optional: additional text to store"
}
```

**Response:** `200 OK` (synchronous) or `202 Accepted` (async)
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440002",
  "chunks_created": 10,
  "embeddings_generated": 10,
  "status": "processed",
  "run_id": "550e8400-e29b-41d4-a716-446655440003"
}
```

**Note:** Uses OpenAI embeddings (`text-embedding-3-small`) and optionally generates summary with `gpt-4o-mini`.

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

---

### Regenerate Document Summary
**POST** `/api/v1/documents/{document_id}/summary?async=false`

Regenerate document summary.

**Path Parameters:**
- `document_id` (UUID): Document ID

**Query Parameters:**
- `async` (boolean, default: `false`): Run in background

**Response:** `200 OK`
```json
{
  "summary": "This document discusses...",
  "document_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**Note:** Uses OpenAI `gpt-4o-mini` for summary generation.

---

### Generate Flashcards
**POST** `/api/v1/documents/{document_id}/flashcards?mode=key_terms&async=false`

Generate flashcards from a document.

**Path Parameters:**
- `document_id` (UUID): Source document ID

**Query Parameters:**
- `async` (boolean, default: `false`): Run in background
- `mode` (string): `key_terms`, `qa`, or `cloze`

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "mode": "key_terms"
}
```

**Response:** `200 OK`
```json
{
  "flashcards_created": 5,
  "preview": [
    {
      "front": "What is...?",
      "back": "...",
      "card_type": "key_terms",
      "source_chunk_ids": ["..."]
    }
  ],
  "dropped_count": 0,
  "dropped_reasons": [],
  "batch_id": "550e8400-e29b-41d4-a716-446655440004"
}
```

**Note:** Uses OpenAI `gpt-4o-mini` for flashcard generation.

---

### Extract Knowledge Graph
**POST** `/api/v1/documents/{document_id}/kg?async=false`

Extract concepts and relationships from a document.

**Path Parameters:**
- `document_id` (UUID): Source document ID

**Query Parameters:**
- `async` (boolean, default: `false`): Run in background

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Response:** `200 OK`
```json
{
  "concepts_written": 10,
  "edges_written": 15,
  "concepts": [
    {
      "id": "...",
      "name": "Machine Learning",
      "description": "...",
      "type": "concept"
    }
  ],
  "edges": [
    {
      "id": "...",
      "src_id": "...",
      "rel_type": "relates_to",
      "dst_id": "..."
    }
  ]
}
```

**Note:** Uses OpenAI `gpt-4o-mini` for KG extraction.

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

---

### Get Flashcard
**GET** `/api/v1/flashcards/{flashcard_id}`

Get a flashcard by ID.

**Path Parameters:**
- `flashcard_id` (UUID): Flashcard ID

**Response:** `200 OK` (FlashcardRead)

---

### Get Due Flashcards
**GET** `/api/v1/flashcards/due?workspace_id={workspace_id}&user_id={user_id}&limit=20`

Get flashcards due for review (SRS algorithm).

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `user_id` (UUID, required): User ID
- `limit` (int, default: 20, max: 100): Maximum number of results

**Response:** `200 OK` (list of FlashcardRead)

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

---

### List Notes
**GET** `/api/v1/notes?workspace_id={workspace_id}&document_id={document_id}&user_id={user_id}`

List notes, optionally filtered by document or user.

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `document_id` (UUID, optional): Filter by document ID
- `user_id` (UUID, optional): Filter by user ID

**Response:** `200 OK` (list of NoteRead)

---

### Get Note
**GET** `/api/v1/notes/{note_id}`

Get a note by ID.

**Path Parameters:**
- `note_id` (UUID): Note ID

**Response:** `200 OK` (NoteRead)

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

---

### Delete Note
**DELETE** `/api/v1/notes/{note_id}`

Delete a note.

**Path Parameters:**
- `note_id` (UUID): Note ID

**Response:** `204 No Content`

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

---

### Get Concept
**GET** `/api/v1/kg/concepts/{concept_id}`

Get a concept by ID.

**Path Parameters:**
- `concept_id` (UUID): Concept ID

**Response:** `200 OK` (ConceptRead)

---

### Get Concept Neighbors
**GET** `/api/v1/kg/concepts/{concept_id}/neighbors?depth=1`

Get neighboring concepts up to specified depth.

**Path Parameters:**
- `concept_id` (UUID): Concept ID

**Query Parameters:**
- `depth` (int, default: 1, min: 1, max: 3): Traversal depth

**Response:** `200 OK` (list of ConceptRead)

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
  "auto_flashcards_after_ingest": false,
  "default_flashcard_mode": "qa"
}
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

---

### List Workspace Members
**GET** `/api/v1/workspaces/{workspace_id}/members`

List all members of a workspace.

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID

**Response:** `200 OK` (list of WorkspaceMemberRead)

---

### Remove Workspace Member
**DELETE** `/api/v1/workspaces/{workspace_id}/members/{member_id}`

Remove a member from a workspace.

**Path Parameters:**
- `workspace_id` (UUID): Workspace ID
- `member_id` (UUID): Membership ID

**Response:** `204 No Content`

---

## Authentication (Stubs)

All auth endpoints return `501 Not Implemented`. These are placeholders for future implementation.

### Signup
**POST** `/api/v1/auth/signup`

**Status:** `501 Not Implemented`

---

### Login
**POST** `/api/v1/auth/login`

**Status:** `501 Not Implemented`

---

### Logout
**POST** `/api/v1/auth/logout`

**Status:** `501 Not Implemented`

---

### Get Current User
**GET** `/api/v1/auth/me`

**Status:** `501 Not Implemented`

---

## Complete Testing Flow

### Step 1: Health Check
```bash
curl http://localhost:8000/health
```

### Step 2: Create a Workspace
```bash
curl -X POST "http://localhost:8000/api/v1/workspaces?owner_user_id=550e8400-e29b-41d4-a716-446655440001" \
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

### Step 4: Ingest the Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/ingest?async=false" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "{workspace_id}",
    "user_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

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
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/flashcards?mode=key_terms&async=false" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "{workspace_id}",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "mode": "key_terms"
  }'
```

### Step 7: Extract Knowledge Graph (Optional)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/kg?async=false" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "{workspace_id}",
    "user_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

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
3. **Async Mode**: Add `?async=true` to any document processing endpoint to run in background
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
| Authentication | Stubs (501) | 4 |
| **Total** | | **45 routes** |
