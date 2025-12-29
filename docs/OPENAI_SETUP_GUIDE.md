# OpenAI Platform Setup Guide

## Step-by-Step: What to Select on OpenAI Platform

### 1. **Get Your API Key**

1. Go to: https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Name it: `MentraFlow Production` (or similar)
4. **Copy the key immediately** - you won't see it again!
5. Paste it into your `.env` file: `OPENAI_API_KEY=sk-...`

### 2. **Choose Your Models**

#### For Chat/LLM Operations (StudyChatAgent, FlashcardAgent, etc.)
- **Model**: `gpt-4o-mini` ✅ (Already configured)
- **Why**: Cost-effective, fast, great for most tasks
- **Cost**: $0.15/$0.60 per 1M tokens (input/output)
- **Location**: Already set in `.env` as `OPENAI_MODEL=gpt-4o-mini`

#### For Embeddings (Document Processing)
- **Model**: `text-embedding-3-small` ✅ (Now configured)
- **Why**: Perfect for 15-page PDFs, cost-effective
- **Cost**: $0.02 per 1M tokens
- **Location**: Set in `.env` as `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`

### 3. **API Access & Billing**

#### Enable API Access
1. Go to: https://platform.openai.com/account/billing
2. Add payment method (required for API access)
3. Set usage limits if desired (recommended for production)

#### Recommended Usage Limits
- **Hard Limit**: $100/month (adjust based on needs)
- **Soft Limit**: $50/month (warning threshold)
- **Rate Limits**: Default is usually fine for development

### 4. **What You DON'T Need to Select**

❌ **Don't need to select**:
- Fine-tuning (you're using base models)
- Custom models
- Assistants API (you're using direct API calls)
- Whisper (audio transcription - not needed)
- DALL-E (image generation - not needed)

✅ **What you're using**:
- Chat Completions API (for LLM agents)
- Embeddings API (for document embeddings)

### 5. **API Endpoints That Use OpenAI**

Your MentraFlow backend uses OpenAI in the following routes:

#### Routes Using OpenAI Chat Completions (`gpt-4o-mini`)

1. **POST** `/api/v1/chat` - Study Chat Assistant
   - Uses: `gpt-4o-mini` for answering questions with citations
   - Input: User questions about documents
   - Output: Answers with citations from retrieved chunks

2. **POST** `/api/v1/documents/{document_id}/ingest` - Document Ingestion
   - Uses: `gpt-4o-mini` for generating document summaries (optional)
   - Uses: `text-embedding-3-small` for chunk embeddings
   - Processes: Document chunking, embedding generation, and optional summary

3. **POST** `/api/v1/documents/{document_id}/flashcards` - Flashcard Generation
   - Uses: `gpt-4o-mini` for generating flashcards from document content
   - Modes: `qa` or `mcq` (default: `mcq`)
   - Output: Flashcards with front/back content (MCQ includes options and correct_answer)

4. **POST** `/api/v1/documents/{document_id}/kg` - Knowledge Graph Extraction
   - Uses: `gpt-4o-mini` for extracting concepts and relationships
   - Output: Concepts and edges for knowledge graph

5. **POST** `/api/v1/documents/{document_id}/summary` - Document Summary
   - Uses: `gpt-4o-mini` for generating document summaries
   - Output: Concise summary of document content

#### Routes Using OpenAI Embeddings (`text-embedding-3-small`)

1. **POST** `/api/v1/documents/{document_id}/ingest` - Document Ingestion
   - Generates embeddings for all document chunks
   - Stores embeddings in Qdrant vector database

2. **POST** `/api/v1/search` - Semantic Search
   - Uses embeddings to find relevant document chunks
   - Searches across workspace documents

3. **POST** `/api/v1/chat` - Study Chat Assistant
   - Uses embeddings for semantic retrieval of relevant chunks
   - Retrieves chunks before generating answer

#### OpenAI API Calls Made Internally

**Chat Completions API:**
```
POST https://api.openai.com/v1/chat/completions
Model: gpt-4o-mini
```

**Embeddings API:**
```
POST https://api.openai.com/v1/embeddings
Model: text-embedding-3-small
```

### 6. **Cost Estimation for Your Use Case**

**15-page PDF processing:**
- Embeddings: ~10,000 tokens × $0.02/1M = **$0.0002 per document**
- Summary generation: ~1,000 tokens × $0.15/1M = **$0.00015 per document**
- Flashcard generation: ~2,000 tokens × $0.15/1M = **$0.0003 per document**
- KG extraction: ~1,500 tokens × $0.15/1M = **$0.000225 per document**

**Chat queries:**
- Embeddings (query): ~50 tokens × $0.02/1M = **$0.000001 per query**
- Chat response: ~500 tokens × $0.15/1M = **$0.000075 per query**

**Monthly estimate (100 documents, 1000 queries, 500 flashcard generations, 200 KG extractions):**
- Document embeddings: 100 × $0.0002 = **$0.02**
- Document summaries: 100 × $0.00015 = **$0.015**
- Flashcard generation: 500 × $0.0003 = **$0.15**
- KG extraction: 200 × $0.000225 = **$0.045**
- Chat queries (embeddings): 1000 × $0.000001 = **$0.001**
- Chat responses: 1000 × $0.000075 = **$0.075**
- **Total: ~$0.31/month** (very affordable!)

### 7. **Security Best Practices**

1. ✅ **Never commit `.env` file** (already in `.gitignore`)
2. ✅ **Use environment variables** (already configured)
3. ✅ **Rotate API keys** periodically
4. ✅ **Set usage limits** on OpenAI dashboard
5. ✅ **Monitor usage** at https://platform.openai.com/usage

### 8. **Testing Your Setup**

After adding your API key to `.env`, test with:

#### Test 1: Health Check
```bash
curl http://localhost:8000/health
```
Should return: `{"status": "healthy", "database": "connected", "qdrant": "connected"}`

#### Test 2: Document Ingestion (uses embeddings)
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "your-workspace-id",
    "user_id": "your-user-id",
    "title": "Test Document",
    "doc_type": "text",
    "content": "Machine learning is a subset of artificial intelligence."
  }'

# Then ingest (this will use OpenAI embeddings)
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "your-workspace-id",
    "user_id": "your-user-id"
  }'
```

#### Test 3: Chat (uses embeddings + chat completions)
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "your-workspace-id",
    "user_id": "your-user-id",
    "message": "What is machine learning?",
    "document_id": "{document_id}"
  }'
```

#### Test 4: Direct OpenAI API Test (Python)
```python
# Test embedding
from openai import OpenAI
client = OpenAI(api_key="your-key")
response = client.embeddings.create(
    model="text-embedding-3-small",
    input="test text"
)
print(f"Dimensions: {len(response.data[0].embedding)}")  # Should be 1536

# Test chat
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### 9. **Troubleshooting**

**"Insufficient quota" error:**
- Add payment method at https://platform.openai.com/account/billing

**"Invalid API key" error:**
- Check key is correct in `.env`
- Ensure no extra spaces
- Regenerate key if needed

**Rate limit errors:**
- Default: 3,500 requests/minute for gpt-4o-mini
- Default: 1,000,000 tokens/minute for embeddings
- Should be fine for your use case

---

## Complete API Routes Reference

### Routes Using OpenAI

| Route | Method | OpenAI Usage | Model |
|-------|--------|--------------|-------|
| `/api/v1/chat` | POST | Chat completions + Embeddings | `gpt-4o-mini` + `text-embedding-3-small` |
| `/api/v1/documents/{id}/ingest` | POST | Embeddings + Optional summaries | `text-embedding-3-small` + `gpt-4o-mini` |
| `/api/v1/documents/{id}/flashcards` | POST | Chat completions | `gpt-4o-mini` |
| `/api/v1/documents/{id}/kg` | POST | Chat completions | `gpt-4o-mini` |
| `/api/v1/documents/{id}/summary` | POST | Chat completions | `gpt-4o-mini` |
| `/api/v1/search` | POST | Embeddings | `text-embedding-3-small` |

### Routes NOT Using OpenAI

| Route | Method | Purpose |
|-------|--------|---------|
| `/health` | GET | Health check |
| `/api/v1/workspaces` | GET, POST, PATCH, DELETE | Workspace management |
| `/api/v1/documents` | GET, POST, PATCH, DELETE | Document CRUD |
| `/api/v1/flashcards` | GET, POST | Flashcard management |
| `/api/v1/flashcards/{id}/review` | POST | SRS review tracking |
| `/api/v1/notes` | GET, POST, PATCH, DELETE | Notes management |
| `/api/v1/preferences` | GET, PATCH | User preferences |
| `/api/v1/agent-runs` | GET | Agent run status |
| `/api/v1/kg/concepts` | GET | Knowledge graph concepts |
| `/api/v1/kg/edges` | GET | Knowledge graph edges |
| `/api/v1/workspace-members` | GET, POST, DELETE | Workspace membership |

For complete API documentation, visit: `http://localhost:8000/docs` (Swagger UI)

---

## Quick Checklist

- [ ] Created API key at https://platform.openai.com/api-keys
- [ ] Added key to `.env` file: `OPENAI_API_KEY=sk-...`
- [ ] Added payment method at https://platform.openai.com/account/billing
- [ ] Set usage limits (optional but recommended)
- [ ] Verified `.env` has both `OPENAI_MODEL` and `OPENAI_EMBEDDING_MODEL`
- [ ] Tested health endpoint: `curl http://localhost:8000/health`
- [ ] Tested document ingestion (uses embeddings)
- [ ] Tested chat endpoint (uses embeddings + chat)

---

**You're all set!** Your configuration is ready:
- ✅ `OPENAI_MODEL=gpt-4o-mini` (for chat/LLM operations)
- ✅ `OPENAI_EMBEDDING_MODEL=text-embedding-3-small` (for embeddings)

**Next Steps:**
1. Start your server: `make run`
2. Visit API docs: `http://localhost:8000/docs`
3. Test endpoints using the examples above

