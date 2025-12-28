# API Routes Reference

## Base URL
- Development: `http://localhost:8000`
- API Prefix: `/api/v1`

## Available Endpoints

### 1. **Create Document** (NEW)
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
  "created_at": "2024-01-01T00:00:00Z",
  ...
}
```

---

### 2. **Ingest Document**
**POST** `/api/v1/documents/{document_id}/ingest`

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
  "status": "processed"
}
```

---

### 3. **Chat with Study Assistant**
**POST** `/api/v1/chat`

Ask questions about documents in your workspace.

**Request Body:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "message": "What is the main topic of this document?",
  "document_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**Response:** `200 OK`
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440003",
  "content": "The main topic is...",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "citations": [
      {
        "chunk_id": "...",
        "document_id": "...",
        "chunk_index": 0,
        "score": 0.95
      }
    ],
    "suggested_note": {
      "title": "...",
      "body": "..."
    }
  }
}
```

---

### 4. **Generate Flashcards**
**POST** `/api/v1/documents/{document_id}/flashcards`

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
      "back": "..."
    }
  ]
}
```

---

### 5. **Extract Knowledge Graph**
**POST** `/api/v1/documents/{document_id}/kg`

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
  "concepts_extracted": 10,
  "edges_extracted": 15,
  "confidence_scores": {
    "avg": 0.85
  }
}
```

---

### 6. **Health Check**
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

---

## Complete Testing Flow

### Step 1: Create a Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "Introduction to Machine Learning",
    "doc_type": "pdf",
    "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data. It enables computers to improve their performance on a task through experience without being explicitly programmed for every scenario."
  }'
```

**Save the `document_id` from the response.**

### Step 2: Ingest the Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

### Step 3: Chat with the Document
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "message": "What is machine learning?",
    "document_id": "{document_id}"
  }'
```

### Step 4: Generate Flashcards (Optional)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/flashcards" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "mode": "key_terms"
  }'
```

### Step 5: Extract Knowledge Graph (Optional)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/kg" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

---

## Notes

1. **UUIDs**: Replace all UUID placeholders with actual UUIDs from your database
2. **Workspace & User IDs**: You need valid `workspace_id` and `user_id` values
3. **Async Mode**: Add `?async=true` to any document processing endpoint to run in background
4. **OpenAPI Docs**: Visit `http://localhost:8000/api/v1/openapi.json` or `http://localhost:8000/docs` for interactive API documentation

