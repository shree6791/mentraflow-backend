# Document Upload Testing Guide

This guide walks you through testing the document upload flow using the MentraFlow API.

## Prerequisites

1. **Server Running**: Make sure your FastAPI server is running
   ```bash
   make run
   # or
   make run-debug
   ```

2. **Health Check**: Verify the server is healthy
   ```bash
   curl http://localhost:8000/health
   ```

3. **Have Credentials Ready**: You'll need:
   - A `username` (create via signup)
   - A `workspace_id` (create one first using username)
   - A `user_id` (UUID - get it by username or from signup response)

---

## Step 1: Create User (if you don't have one)

**Endpoint:** `POST /api/v1/auth/signup`

```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword",
    "full_name": "Test User"
  }'
```

**Save the `username` from response → `USERNAME`**

**To get user_id by username:**
```bash
curl "http://localhost:8000/api/v1/users/by-username/testuser"
```

**Save the `user_id` from response → `USER_ID`**

---

## Step 2: Create a Workspace (if you don't have one)

**Endpoint:** `POST /api/v1/workspaces?owner_username={username}`

```bash
curl -X POST "http://localhost:8000/api/v1/workspaces?owner_username=testuser" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workspace",
    "plan_tier": "free"
  }'
```

**Save the `id` from the response as `WORKSPACE_ID`**

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Test Workspace",
  "plan_tier": "free",
  "owner_id": "550e8400-e29b-41d4-a716-446655440001",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## Step 3: Upload/Create a Document

The unified endpoint `POST /api/v1/documents` supports **two modes**:

### Option A: Create Document with Text Content (JSON)

**Endpoint:** `POST /api/v1/documents` (Content-Type: `application/json`)

```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID",
    "title": "Introduction to Machine Learning",
    "doc_type": "text",
    "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data. It enables computers to improve their performance on a task through experience without being explicitly programmed for every scenario. There are three main types of machine learning: supervised learning, unsupervised learning, and reinforcement learning. Supervised learning uses labeled data to train models, while unsupervised learning finds patterns in unlabeled data. Reinforcement learning involves training agents to make decisions through trial and error.",
    "metadata": {
      "source": "test",
      "pages": 1
    }
  }'
```

**Save the `id` from the response as `DOCUMENT_ID`**

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "Introduction to Machine Learning",
  "status": "pending",
  "metadata": {
    "source": "test",
    "pages": 1
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Option B: Upload File (Multipart Form Data)

**Endpoint:** `POST /api/v1/documents` (Content-Type: `multipart/form-data`)

**Supported file types:** PDF (.pdf), DOC/DOCX (.doc, .docx), TXT (.txt), MD (.md)

```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@/path/to/your/document.pdf" \
  -F "workspace_id=YOUR_WORKSPACE_ID" \
  -F "user_id=YOUR_USER_ID" \
  -F "title=My Study Document"
```

**Or with a text file:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@/path/to/your/document.txt" \
  -F "workspace_id=YOUR_WORKSPACE_ID" \
  -F "user_id=YOUR_USER_ID" \
  -F "title=My Study Document"
```

**Note:** 
- The endpoint automatically extracts text from PDF, DOC, DOCX files
- Text files are read directly
- If `auto_ingest_on_upload=true` in user preferences (default: `true`), ingestion will start automatically in the background
- During ingestion, summary and flashcards are also generated automatically if preferences are enabled (default: `true`)

---

## Step 4: Check Document Status

**Endpoint:** `GET /api/v1/documents/{document_id}`

```bash
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID"
```

**Status Values:**
- `pending` - Document created, not yet processed
- `storing` - Storing raw text
- `chunking` - Breaking into chunks
- `embedding` - Generating embeddings
- `ready` - Successfully processed and ready
- `failed` - Processing failed

**Example Response (after processing):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "status": "ready",
  "summary_text": "• Machine learning is a subset of AI...",
  "last_run_id": "550e8400-e29b-41d4-a716-446655440003",
  ...
}
```

**To check agent run status:**
```bash
curl "http://localhost:8000/api/v1/agent-runs/YOUR_RUN_ID"
```

---

## Quick Test Script

Save this as `test_document_upload.sh`:

```bash
#!/bin/bash

# Configuration
BASE_URL="http://localhost:8000"
USERNAME="testuser"  # Replace with your username
USER_ID=""  # Will be fetched by username
WORKSPACE_ID=""  # Will be set after workspace creation

echo "🚀 Testing Document Upload Flow"
echo "================================"

# Step 1: Get User ID by Username
echo ""
echo "Step 1: Getting user ID by username..."
USER_RESPONSE=$(curl -s "${BASE_URL}/api/v1/users/by-username/${USERNAME}")
USER_ID=$(echo $USER_RESPONSE | grep -o '"user_id":"[^"]*' | cut -d'"' -f4)
echo "✅ User ID: ${USER_ID}"

# Step 2: Create Workspace
echo ""
echo "Step 2: Creating workspace..."
WORKSPACE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/workspaces?owner_username=${USERNAME}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workspace",
    "plan_tier": "free"
  }')
WORKSPACE_ID=$(echo $WORKSPACE_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
echo "✅ Workspace created: ${WORKSPACE_ID}"

# Step 3: Create Document
echo ""
echo "Step 3: Creating document..."
DOC_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace_id\": \"${WORKSPACE_ID}\",
    \"user_id\": \"${USER_ID}\",
    \"title\": \"Test ML Document\",
    \"doc_type\": \"text\",
    \"content\": \"Machine learning is a subset of artificial intelligence. It enables computers to learn from data. There are three main types: supervised learning, unsupervised learning, and reinforcement learning.\"
  }")
DOCUMENT_ID=$(echo $DOC_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
echo "✅ Document created: ${DOCUMENT_ID}"

# Step 4: Check Document Status
echo ""
echo "Step 4: Checking document status..."
echo "Note: Ingestion, summary, and flashcards happen automatically if preferences are enabled (default: true)"
sleep 5  # Wait a bit for processing to start
STATUS_RESPONSE=$(curl -s "${BASE_URL}/api/v1/documents/${DOCUMENT_ID}")
echo "✅ Document status:"
echo $STATUS_RESPONSE | python3 -m json.tool

echo ""
echo "✅ Document upload flow test complete!"
echo "📊 Summary:"
echo "   - Workspace: ${WORKSPACE_ID}"
echo "   - Document: ${DOCUMENT_ID}"
echo "   - Check document: ${BASE_URL}/api/v1/documents/${DOCUMENT_ID}"
```

**Make it executable:**
```bash
chmod +x test_document_upload.sh
./test_document_upload.sh
```

---

## Common Issues & Solutions

### Issue: "Workspace {workspace_id} not found" (404)
**Solution:** 
- Make sure the workspace exists (create it first using `POST /api/v1/workspaces?owner_username={username}`)
- Verify you're using the correct `workspace_id` UUID

### Issue: "User {user_id} not found" (404)
**Solution:**
- Make sure the user exists (create via `POST /api/v1/auth/signup`)
- Get the correct `user_id` UUID using `GET /api/v1/users/by-username/{username}`

### Issue: "Document not found" (404)
**Solution:** Make sure you're using the correct `document_id` from Step 3.

### Issue: Document status stuck at "pending"
**Solution:** 
1. Check if auto-ingestion is enabled in user preferences (default: `true`)
2. Check agent run status: `GET /api/v1/agent-runs/{run_id}` (use `last_run_id` from document)
3. Look for errors in the agent run `error` field

### Issue: "Failed to extract text from PDF/DOC"
**Solution:**
- For PDF: Make sure `pypdf` is installed: `pip install pypdf`
- For DOC/DOCX: Make sure `python-docx` is installed: `pip install python-docx`
- Check that the file is not corrupted or password-protected

### Issue: "Unsupported file type"
**Solution:** Currently supported file types are:
- PDF (.pdf)
- DOC/DOCX (.doc, .docx)
- Text files (.txt, .md)

---

## What Happens Automatically

When you upload a document with default preferences:

1. **Ingestion** (if `auto_ingest_on_upload=true` - default: `true`):
   - Document is chunked
   - Embeddings are generated
   - Vectors are stored in Qdrant

2. **Summary Generation** (if `auto_summary_after_ingest=true` - default: `true`):
   - Summary is generated using LLM
   - Stored in `documents.summary_text` column

3. **Flashcard Generation** (if `auto_flashcards_after_ingest=true` - default: `true`):
   - Flashcards are generated using LLM
   - Stored in `flashcards` table
   - Uses `default_flashcard_mode` from preferences (default: `qa`)

All of these run asynchronously in the background. Check the document status or agent run status to monitor progress.

---

## Next Steps

After successful upload and processing:
- ✅ Test chat functionality: `POST /api/v1/chat`
- ✅ View summary: `GET /api/v1/documents/{document_id}/summary`
- ✅ View flashcards: `GET /api/v1/flashcards?document_id={document_id}`
- ✅ Test semantic search: `POST /api/v1/search`

See `API_ROUTES.md` for detailed endpoint documentation.
