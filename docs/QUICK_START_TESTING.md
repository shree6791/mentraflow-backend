# Quick Start: Testing Upload → Summary → Quiz Flow

This is the **exact order** of API calls to test your main flow: **Upload Data → Generate Summary → Generate Quiz (Flashcards)**

---

## 🎯 The Flow (5 Steps)

```
1. Create Workspace (or use existing)
   ↓
2. Upload Document
   ↓
3. Ingest Document (process: chunk + embed)
   ↓
4. Generate Summary
   ↓
5. Generate Flashcards (Quiz)
```

---

## Step-by-Step API Calls

### **Step 0: Create User (if you don't have one)** 👤

**Endpoint:** `POST /api/v1/auth/signup`

```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "shree6791",
    "email": "your-email@example.com",
    "password": "your-password",
    "full_name": "Your Name"
  }'
```

**Save the `username` from response → `USERNAME`**

---

### **Step 1: Create Workspace** ✅

**Endpoint:** `POST /api/v1/workspaces?owner_username={username}`

```bash
curl -X POST "http://localhost:8000/api/v1/workspaces?owner_username=shree6791" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Study Workspace",
    "plan_tier": "free"
  }'
```

**Save the `id` from response → `WORKSPACE_ID`**

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Study Workspace",
  "plan_tier": "free",
  "owner_id": "YOUR_USER_ID",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### **Step 2: Upload Document** 📄

**Endpoint:** `POST /api/v1/workspaces/{workspace_id}/documents`

```bash
curl -X POST "http://localhost:8000/api/v1/workspaces/YOUR_WORKSPACE_ID/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID",
    "title": "Introduction to Machine Learning",
    "doc_type": "pdf",
    "source_url": "https://example.com/ml-intro.pdf",
    "language": "en",
    "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data. It enables computers to improve their performance on a task through experience without being explicitly programmed for every scenario. There are three main types of machine learning: supervised learning, unsupervised learning, and reinforcement learning. Supervised learning uses labeled data to train models, while unsupervised learning finds patterns in unlabeled data. Reinforcement learning involves training agents to make decisions through trial and error.",
    "metadata": {}
  }'
```

**Save the `id` from response → `DOCUMENT_ID`**

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "workspace_id": "YOUR_WORKSPACE_ID",
  "title": "Introduction to Machine Learning",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Note:** If `auto_ingest_on_upload=true` in your preferences, Step 3 will happen automatically. Otherwise, proceed to Step 3.

---

### **Step 3: Ingest Document** (Process: Chunk + Embed) ⚙️

**Endpoint:** `POST /api/v1/documents/{document_id}/ingest?async=false`

```bash
curl -X POST "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/ingest?async=false" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID"
  }'
```

**Wait for response** (this processes the document: chunks it, generates embeddings, stores in Qdrant)

**Example Response:**
```json
{
  "document_id": "YOUR_DOCUMENT_ID",
  "chunks_created": 3,
  "embeddings_created": 3,
  "status": "processed",
  "run_id": "550e8400-e29b-41d4-a716-446655440003"
}
```

**Verify Status:**
```bash
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID"
```

**Expected:** `"status": "processed"`

---

### **Step 4: Generate Summary** 📝

**Endpoint:** `POST /api/v1/documents/{document_id}/summary?async=false`

```bash
curl -X POST "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/summary?async=false" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID",
    "max_bullets": 7
  }'
```

**Example Response:**
```json
{
  "document_id": "YOUR_DOCUMENT_ID",
  "summary": "• Machine learning is a subset of AI focused on algorithms that learn from data\n• Three main types: supervised, unsupervised, and reinforcement learning\n• Supervised learning uses labeled data to train models\n• Unsupervised learning finds patterns in unlabeled data\n• Reinforcement learning trains agents through trial and error",
  "summary_length": 245,
  "run_id": "550e8400-e29b-41d4-a716-446655440004"
}
```

**Verify Summary Saved:**
```bash
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/summary"
```

---

### **Step 5: Generate Flashcards (Quiz)** 🎯

**Endpoint:** `POST /api/v1/documents/{document_id}/flashcards?mode=qa&async=false`

```bash
curl -X POST "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/flashcards?mode=qa&async=false" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "YOUR_WORKSPACE_ID",
    "user_id": "YOUR_USER_ID",
    "mode": "qa"
  }'
```

**Available Modes:**
- `key_terms` - Key term definitions
- `qa` - Question and answer pairs
- `cloze` - Fill-in-the-blank questions

**Example Response:**
```json
{
  "flashcards_created": 5,
  "preview": [
    {
      "front": "What is machine learning?",
      "back": "A subset of artificial intelligence that focuses on algorithms that can learn from data.",
      "card_type": "qa",
      "source_chunk_ids": ["550e8400-e29b-41d4-a716-446655440005"]
    },
    {
      "front": "What are the three main types of machine learning?",
      "back": "Supervised learning, unsupervised learning, and reinforcement learning.",
      "card_type": "qa",
      "source_chunk_ids": ["550e8400-e29b-41d4-a716-446655440006"]
    }
  ],
  "dropped_count": 0,
  "dropped_reasons": [],
  "batch_id": "550e8400-e29b-41d4-a716-446655440007"
}
```

**View All Flashcards:**
```bash
curl "http://localhost:8000/api/v1/flashcards?workspace_id=YOUR_WORKSPACE_ID&user_id=YOUR_USER_ID"
```

---

## 🚀 Complete Test Script

Save this as `test_main_flow.sh`:

```bash
#!/bin/bash

# ============================================
# Configuration - UPDATE THESE VALUES
# ============================================
BASE_URL="http://localhost:8000"
USERNAME="shree6791"  # Replace with your username
WORKSPACE_ID=""
DOCUMENT_ID=""

# ============================================
# Step 0: Create User (if needed)
# ============================================
echo "👤 Step 0: Creating user (if not exists)..."
# Try to create user (will fail if exists, that's okay)
curl -s -X POST "${BASE_URL}/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"${USERNAME}\",
    \"email\": \"${USERNAME}@example.com\",
    \"password\": \"test123456\",
    \"full_name\": \"Test User\"
  }" > /dev/null 2>&1 || echo "User may already exist, continuing..."
echo ""

# ============================================
# Step 1: Create Workspace
# ============================================
echo "📦 Step 1: Creating workspace..."
WORKSPACE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/workspaces?owner_username=${USERNAME}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workspace",
    "plan_tier": "free"
  }')
WORKSPACE_ID=$(echo $WORKSPACE_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
echo "✅ Workspace ID: ${WORKSPACE_ID}"
echo ""

# ============================================
# Step 2: Upload Document
# ============================================
echo "📄 Step 2: Uploading document..."
DOC_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/workspaces/${WORKSPACE_ID}/documents" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"${USER_ID}\",
    \"title\": \"Introduction to Machine Learning\",
    \"doc_type\": \"pdf\",
    \"source_url\": \"https://example.com/ml-intro.pdf\",
    \"language\": \"en\",
    \"content\": \"Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data. It enables computers to improve their performance on a task through experience without being explicitly programmed for every scenario. There are three main types of machine learning: supervised learning, unsupervised learning, and reinforcement learning. Supervised learning uses labeled data to train models, while unsupervised learning finds patterns in unlabeled data. Reinforcement learning involves training agents to make decisions through trial and error.\",
    \"metadata\": {}
  }")
DOCUMENT_ID=$(echo $DOC_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
echo "✅ Document ID: ${DOCUMENT_ID}"
echo ""

# ============================================
# Step 3: Ingest Document
# ============================================
echo "⚙️  Step 3: Ingesting document (chunking + embedding)..."
INGEST_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/documents/${DOCUMENT_ID}/ingest?async=false" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace_id\": \"${WORKSPACE_ID}\",
    \"user_id\": \"${USER_ID}\"
  }")
echo "✅ Ingestion complete:"
echo $INGEST_RESPONSE | python3 -m json.tool
echo ""

# ============================================
# Step 4: Generate Summary
# ============================================
echo "📝 Step 4: Generating summary..."
SUMMARY_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/documents/${DOCUMENT_ID}/summary?async=false" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace_id\": \"${WORKSPACE_ID}\",
    \"user_id\": \"${USER_ID}\",
    \"max_bullets\": 7
  }")
echo "✅ Summary generated:"
echo $SUMMARY_RESPONSE | python3 -m json.tool
echo ""

# ============================================
# Step 5: Generate Flashcards (Quiz)
# ============================================
echo "🎯 Step 5: Generating flashcards (quiz)..."
FLASHCARD_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/documents/${DOCUMENT_ID}/flashcards?mode=qa&async=false" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace_id\": \"${WORKSPACE_ID}\",
    \"user_id\": \"${USER_ID}\",
    \"mode\": \"qa\"
  }")
echo "✅ Flashcards generated:"
echo $FLASHCARD_RESPONSE | python3 -m json.tool
echo ""

echo "🎉 Complete flow test finished!"
echo "📊 Summary:"
echo "   - Workspace: ${WORKSPACE_ID}"
echo "   - Document: ${DOCUMENT_ID}"
echo "   - Check document: ${BASE_URL}/api/v1/documents/${DOCUMENT_ID}"
```

**Make it executable and run:**
```bash
chmod +x test_main_flow.sh
./test_main_flow.sh
```

---

## 📋 Quick Reference: API Order

| Step | Method | Endpoint | Purpose |
|------|--------|----------|---------|
| 0 | POST | `/api/v1/auth/signup` | Create user (if needed) |
| 1 | POST | `/api/v1/workspaces?owner_username={username}` | Create workspace |
| 2 | POST | `/api/v1/workspaces/{id}/documents` | Upload document |
| 3 | POST | `/api/v1/documents/{id}/ingest?async=false` | Process document |
| 4 | POST | `/api/v1/documents/{id}/summary?async=false` | Generate summary |
| 5 | POST | `/api/v1/documents/{id}/flashcards?mode=qa&async=false` | Generate quiz |

---

## ⚠️ Important Notes

1. **Username Required**: All endpoints use `username` (e.g., "shree6791") for consistency:
   - Create user first: `POST /api/v1/auth/signup` with `username` field
   - Use `owner_username` parameter in workspace creation
   - Username must be unique across the system

2. **Async vs Sync**: 
   - Use `async=false` for testing (waits for completion)
   - Use `async=true` for production (returns immediately, check status later)

3. **Document Status**: After Step 3, verify `status: "processed"` before proceeding to Steps 4-5

4. **Content Required**: Step 2 requires `content` field with the actual document text. For PDFs, extract text first or use a text extraction service.

---

## 🐛 Troubleshooting

**Issue: "Document not found"**
- Make sure Step 2 completed successfully
- Check the `DOCUMENT_ID` is correct

**Issue: "Ingestion already in progress"**
- Wait for current ingestion to finish
- Or check document status first

**Issue: Summary/Flashcards return empty**
- Make sure Step 3 (ingestion) completed successfully
- Check `chunks_created > 0` in ingestion response
- Document must have sufficient content

---

## ✅ Success Checklist

After running all 5 steps, you should have:
- ✅ A workspace created
- ✅ A document uploaded and processed
- ✅ A summary generated and saved
- ✅ Flashcards (quiz) generated and saved

**Verify everything:**
```bash
# Check document
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID"

# Check summary
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/summary"

# Check flashcards
curl "http://localhost:8000/api/v1/flashcards?workspace_id=YOUR_WORKSPACE_ID&user_id=YOUR_USER_ID"
```

