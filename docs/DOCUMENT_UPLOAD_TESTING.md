# Document Upload Flow Testing Guide

This guide walks you through testing the complete document upload and processing flow using the MentraFlow API.

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

## Complete Document Upload Flow

### Step 0: Create User (if you don't have one)

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

### Step 1: Create a Workspace (if you don't have one)

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

### Step 2: Upload/Create a Document

The unified endpoint `POST /api/v1/documents` supports **two modes**:

#### Option A: Create Document with Text Content (JSON)

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
  "created_by": "550e8400-e29b-41d4-a716-446655440001",
  "title": "Introduction to Machine Learning",
  "status": "processed",
  "metadata": {
    "source": "test",
    "pages": 1
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Option B: Upload File (Multipart Form Data)

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
- If `auto_ingest_on_upload=true` in user preferences, ingestion will start automatically in the background

#### Option C: Create Document via Workspace Endpoint (Backward Compatible)

```bash
curl -X POST "http://localhost:8000/api/v1/workspaces/YOUR_WORKSPACE_ID/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID",
    "title": "Introduction to Machine Learning",
    "doc_type": "text",
    "content": "Machine learning is a subset of artificial intelligence...",
    "metadata": {}
  }'
```

**Note:** This endpoint delegates to the unified `/documents` endpoint for backward compatibility.

---

### Step 3: Check Document Status

```bash
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID"
```

**Status Values:**
- `pending` - Document created, not yet processed
- `storing` - Storing raw text
- `chunking` - Breaking into chunks
- `embedding` - Generating embeddings
- `processed` - Successfully processed and ready
- `failed` - Processing failed

---

### Step 4: Ingest the Document (Process it)

This step chunks the document, generates embeddings, and stores them in Qdrant.

#### Option A: Synchronous Ingestion (Wait for completion)

```bash
curl -X POST "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/ingest?async=false" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID",
    "raw_text": null
  }'
```

**Response (200 OK):**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440002",
  "chunks_created": 3,
  "embeddings_created": 3,
  "status": "processed",
  "run_id": "550e8400-e29b-41d4-a716-446655440003"
}
```

#### Option B: Asynchronous Ingestion (Returns immediately)

```bash
curl -X POST "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/ingest?async=true" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID"
  }'
```

**Response (202 Accepted):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "queued",
  "message": "Document ingestion queued. Check agent_runs table for status."
}
```

**Then check status:**
```bash
curl "http://localhost:8000/api/v1/agent-runs/YOUR_RUN_ID"
```

---

### Step 5: Verify Document is Processed

```bash
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID"
```

**Expected Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "status": "processed",
  "summary_text": null,
  "last_run_id": "550e8400-e29b-41d4-a716-446655440003",
  ...
}
```

---

### Step 6: Test Using the Document

Once the document is processed, you can:

#### A. Chat with the Document

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID",
    "message": "What is machine learning?",
    "document_id": "YOUR_DOCUMENT_ID",
    "top_k": 8
  }'
```

#### B. Generate Summary

```bash
curl -X POST "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/summary?async=false" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID",
    "max_bullets": 7
  }'
```

#### C. Generate Flashcards

```bash
curl -X POST "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/flashcards?mode=key_terms&async=false" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID",
    "mode": "key_terms"
  }'
```

#### D. Extract Knowledge Graph

```bash
curl -X POST "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/kg?async=false" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID"
  }'
```

---

## Quick Test Script

Save this as `test_document_upload.sh`:

```bash
#!/bin/bash

# Configuration
BASE_URL="http://localhost:8000"
USER_ID="550e8400-e29b-41d4-a716-446655440001"  # Replace with your user ID
WORKSPACE_ID=""  # Will be set after workspace creation

echo "🚀 Testing Document Upload Flow"
echo "================================"

# Configuration
BASE_URL="http://localhost:8000"
USERNAME="testuser"  # Replace with your username
USER_ID=""  # Will be fetched by username
WORKSPACE_ID=""  # Will be set after workspace creation

echo "🚀 Testing Document Upload Flow"
echo "================================"

# Step 0: Get User ID by Username
echo ""
echo "Step 0: Getting user ID by username..."
USER_RESPONSE=$(curl -s "${BASE_URL}/api/v1/users/by-username/${USERNAME}")
USER_ID=$(echo $USER_RESPONSE | grep -o '"user_id":"[^"]*' | cut -d'"' -f4)
echo "✅ User ID: ${USER_ID}"

# Step 1: Create Workspace
echo ""
echo "Step 1: Creating workspace..."
WORKSPACE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/workspaces?owner_username=${USERNAME}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workspace",
    "plan_tier": "free"
  }')
WORKSPACE_ID=$(echo $WORKSPACE_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
echo "✅ Workspace created: ${WORKSPACE_ID}"

# Step 2: Create Document
echo ""
echo "Step 2: Creating document..."
DOC_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace_id\": \"${WORKSPACE_ID}\",
    \"user_id\": \"${USER_ID}\",
    \"title\": \"Test ML Document\",
    \"doc_type\": \"text\",
    \"content\": \"Machine learning is a subset of artificial intelligence. It enables computers to learn from data.\"
  }")
DOCUMENT_ID=$(echo $DOC_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
echo "✅ Document created: ${DOCUMENT_ID}"

# Step 3: Ingest Document (Synchronous)
echo ""
echo "Step 3: Ingesting document (this may take a moment)..."
INGEST_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/documents/${DOCUMENT_ID}/ingest?async=false" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace_id\": \"${WORKSPACE_ID}\",
    \"user_id\": \"${USER_ID}\"
  }")
echo "✅ Ingestion response:"
echo $INGEST_RESPONSE | python3 -m json.tool

# Step 4: Check Document Status
echo ""
echo "Step 4: Checking document status..."
STATUS_RESPONSE=$(curl -s "${BASE_URL}/api/v1/documents/${DOCUMENT_ID}")
echo "✅ Document status:"
echo $STATUS_RESPONSE | python3 -m json.tool

# Step 5: Test Chat
echo ""
echo "Step 5: Testing chat with document..."
CHAT_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace_id\": \"${WORKSPACE_ID}\",
    \"user_id\": \"${USER_ID}\",
    \"message\": \"What is machine learning?\",
    \"document_id\": \"${DOCUMENT_ID}\"
  }")
echo "✅ Chat response:"
echo $CHAT_RESPONSE | python3 -m json.tool

echo ""
echo "✅ Document upload flow test complete!"
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
**Solution:** Make sure you're using the correct `document_id` from Step 2.

### Issue: "Ingestion already in progress" (409)
**Solution:** Wait for the current ingestion to complete, or check the document status first.

### Issue: "No chunks found" in chat
**Solution:** Make sure ingestion completed successfully (status = "processed"). Check the ingestion response for `chunks_created > 0`.

### Issue: Document status stuck at "pending"
**Solution:** 
1. Check if ingestion was triggered
2. Check agent run status: `GET /api/v1/agent-runs/{run_id}`
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

## Testing Different Scenarios

### Scenario 1: Small Document (< 1 page)
- Upload a short document
- Should process quickly
- Should generate a few chunks

### Scenario 2: Large Document (10+ pages)
- Upload a longer document
- Use `async=true` for ingestion
- Monitor progress via agent runs

### Scenario 3: Duplicate Detection
- Upload the same document twice (same content)
- Check `content_hash` matches
- System should detect duplicate

### Scenario 4: Auto-ingest on Upload
- Set `auto_ingest_on_upload=true` in preferences
- Upload document via `/workspaces/{id}/documents`
- Ingestion should start automatically

---

## Next Steps

After successful upload and ingestion:
1. ✅ Test chat functionality
2. ✅ Generate flashcards
3. ✅ Extract knowledge graph
4. ✅ Generate summary
5. ✅ Test semantic search

See `API_ROUTES.md` for detailed endpoint documentation.

