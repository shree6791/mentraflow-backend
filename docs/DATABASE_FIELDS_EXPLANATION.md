# Database Fields Explanation

This document explains why certain fields exist in our database tables and how they're used.

---

## 1. `agent_runs.steps` (JSONB)

### **What It Is:**
A JSONB array that stores step-by-step progress logs for agent execution.

### **Why We Need It:**

#### **1. Progress Tracking for Async Operations**
Agents run asynchronously in the background. The `steps` field allows the UI to show real-time progress:

```json
{
  "steps": [
    {
      "step_name": "retrieve_chunks",
      "status": "started",
      "timestamp": "2025-01-15T10:00:00Z"
    },
    {
      "step_name": "retrieve_chunks",
      "status": "completed",
      "details": {"chunks_retrieved": 15},
      "timestamp": "2025-01-15T10:00:05Z"
    },
    {
      "step_name": "generate_summary",
      "status": "started",
      "timestamp": "2025-01-15T10:00:06Z"
    }
  ]
}
```

**UI Use Case:**
- Show progress bar: "Step 2 of 5: Generating summary..."
- Display detailed status: "Retrieved 15 chunks, generating summary..."
- Debug failed operations: "Failed at step 'generate_summary' with error..."

#### **2. Debugging & Troubleshooting**
When an agent fails, `steps` shows exactly where it failed:

```json
{
  "status": "failed",
  "steps": [
    {"step_name": "chunking", "status": "completed"},
    {"step_name": "embedding", "status": "started"},
    {"step_name": "embedding", "status": "failed", "error": "OpenAI API rate limit exceeded"}
  ]
}
```

**Use Case:**
- Identify which step failed
- See error messages for each step
- Understand execution flow

#### **3. Analytics & Monitoring**
Track how long each step takes:

```json
{
  "steps": [
    {"step_name": "chunking", "status": "completed", "duration_ms": 1200},
    {"step_name": "embedding", "status": "completed", "duration_ms": 3500}
  ]
}
```

**Use Case:**
- Performance monitoring
- Identify bottlenecks
- Optimize slow steps

### **How It's Used in Code:**

```python
# In ingestion_graph.py
async def _log_step(
    state: IngestionState,
    step_name: str,
    step_status: str,
    details: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Log a step to agent_runs.steps"""
    if state.get("run_id"):
        step = {
            "step_name": step_name,
            "status": step_status,
            "details": details,
            "error": error,
        }
        await agent_run_service.update_status(
            run_id=state["run_id"],
            step=step,  # This appends to steps array
        )
```

### **Example from Ingestion Agent:**
```json
{
  "steps": [
    {"step_name": "store_raw_text", "status": "completed"},
    {"step_name": "chunk_document", "status": "completed", "details": {"chunks_created": 12}},
    {"step_name": "generate_embeddings", "status": "completed", "details": {"embeddings_created": 12}},
    {"step_name": "upsert_to_qdrant", "status": "completed"},
    {"step_name": "generate_summary", "status": "completed", "details": {"summary_length": 250}},
    {"step_name": "generate_flashcards", "status": "completed", "details": {"flashcards_created": 8, "mode": "mcq"}},
    {"step_name": "generate_kg", "status": "completed", "details": {"concepts_created": 15, "edges_created": 20}}
  ]
}
```

### **Can We Remove It?**
❌ **No** - It's essential for:
- UI progress indicators
- Debugging async operations
- Performance monitoring
- User experience (showing "Processing..." states)

---

## 2. `documents.metadata` (JSONB)

### **What It Is:**
A flexible JSONB field for storing document-specific metadata that doesn't fit in structured columns.

### **Why We Need It:**

#### **1. File Upload Information**
When users upload files, we store file-specific info:

```json
{
  "metadata": {
    "original_filename": "machine_learning_notes.pdf",
    "file_size": 2456789,
    "file_type": "application/pdf",
    "upload_method": "file_upload"
  }
}
```

**Use Case:**
- Display original filename (user might rename document)
- Show file size in UI
- Track upload source

#### **2. Source Information**
Track where documents came from:

```json
{
  "metadata": {
    "source": "web_scraper",
    "source_url": "https://example.com/article",
    "scraped_at": "2025-01-15T10:00:00Z"
  }
}
```

**Use Case:**
- Link back to original source
- Track document provenance
- Support different import methods

#### **3. Processing Information**
Store processing-related data:

```json
{
  "metadata": {
    "pages": 15,
    "word_count": 3500,
    "processing_time_seconds": 12.5,
    "embedding_model": "text-embedding-3-small"
  }
}
```

**Use Case:**
- Show document statistics
- Track processing metrics
- Version control (which embedding model was used)

#### **4. Custom User Data**
Allow users to add custom metadata:

```json
{
  "metadata": {
    "tags": ["machine-learning", "ai"],
    "course": "CS229",
    "semester": "Fall 2024",
    "priority": "high"
  }
}
```

**Use Case:**
- User-defined tags/categories
- Custom organization
- Integration with external systems

### **How It's Used in Code:**

```python
# In documents.py endpoint
if file:
    metadata = {
        "original_filename": file.filename,
        "file_size": len(file_content),
    }
    
document = await document_service.create_document(
    workspace_id=workspace_id,
    user_id=user_id,
    title=title,
    doc_type=doc_type,
    metadata=metadata,  # Stored in documents.metadata
)
```

### **Example Values:**

**File Upload:**
```json
{
  "original_filename": "study_notes.pdf",
  "file_size": 1024000,
  "mime_type": "application/pdf"
}
```

**Text Input:**
```json
{
  "source": "manual_input",
  "word_count": 500
}
```

**Web Import:**
```json
{
  "source": "web_import",
  "source_url": "https://example.com/article",
  "imported_at": "2025-01-15T10:00:00Z"
}
```

### **Can We Remove It?**
⚠️ **Maybe, but not recommended:**
- Could add specific columns for common fields (filename, file_size)
- But metadata provides flexibility for:
  - Future features (tags, categories)
  - Different import sources
  - Custom user data
  - Processing metadata

**Recommendation:** Keep it for flexibility, but consider adding common fields as dedicated columns if they become critical.

---

## 3. `document_chunks.metadata` (JSONB)

### **What It Is:**
A flexible JSONB field for storing chunk-specific metadata.

### **Why We Need It:**

#### **1. Chunk Quality Metrics**
Store quality/confidence scores for chunks:

```json
{
  "metadata": {
    "quality_score": 0.85,
    "completeness": 0.9,
    "relevance_score": 0.92
  }
}
```

**Use Case:**
- Filter low-quality chunks
- Prioritize high-quality chunks in search
- Analytics on chunk quality

#### **2. Chunk Source Information**
Track where chunk came from in original document:

```json
{
  "metadata": {
    "page_number": 5,
    "section": "Introduction",
    "paragraph_index": 2,
    "original_formatting": "heading"
  }
}
```

**Use Case:**
- Better citations (show "Page 5, Section 2")
- Preserve document structure
- Context-aware display

#### **3. Processing Information**
Store chunk processing details:

```json
{
  "metadata": {
    "chunking_method": "recursive",
    "chunk_size": 800,
    "overlap": 120,
    "embedding_model": "text-embedding-3-small",
    "embedding_version": "v1"
  }
}
```

**Use Case:**
- Track which chunking strategy was used
- Version control for embeddings
- Re-chunking decisions

#### **4. Search/Retrieval Metadata**
Store search-related data:

```json
{
  "metadata": {
    "retrieval_count": 15,
    "last_retrieved_at": "2025-01-15T10:00:00Z",
    "average_relevance_score": 0.87
  }
}
```

**Use Case:**
- Analytics on chunk usage
- Identify frequently accessed chunks
- Optimize retrieval

### **How It's Used in Code:**

Currently, `document_chunks.metadata` is **not heavily used** in the codebase, but it's available for:

1. **Future Features:**
   - Chunk quality scoring
   - Better citation display
   - Chunk analytics

2. **Processing Metadata:**
   - Track chunking parameters
   - Store embedding model info

### **Example Values:**

**With Page Numbers (if extracted):**
```json
{
  "page_number": 3,
  "section": "Methods",
  "chunking_method": "recursive"
}
```

**With Quality Scores (future):**
```json
{
  "quality_score": 0.88,
  "completeness": 0.92,
  "semantic_coherence": 0.85
}
```

### **Can We Remove It?**
✅ **Yes, but keep it for future use:**
- Currently not heavily used
- But provides flexibility for:
  - Better citations (page numbers, sections)
  - Chunk quality metrics
  - Analytics
  - Future features

**Recommendation:** Keep it for future extensibility, but it's not critical for current functionality.

---

## Summary

| Field | Table | Critical? | Current Usage | Future Use |
|-------|-------|-----------|---------------|------------|
| `steps` | `agent_runs` | ✅ **Yes** | Progress tracking, debugging | Analytics, monitoring |
| `metadata` | `documents` | ⚠️ **Medium** | File info, source tracking | Tags, custom data, analytics |
| `metadata` | `document_chunks` | ❌ **Low** | Not heavily used | Quality scores, citations, analytics |

### **Recommendations:**

1. **`agent_runs.steps`** - ✅ **Keep** - Essential for async operation tracking
2. **`documents.metadata`** - ✅ **Keep** - Useful for file info and future features
3. **`document_chunks.metadata`** - ⚠️ **Keep for now** - Not critical but useful for future features

---

## UI Implementation Notes

### **For `agent_runs.steps`:**
```typescript
// Show progress in UI
interface AgentStep {
  step_name: string;
  status: "started" | "completed" | "failed";
  details?: Record<string, any>;
  error?: string;
  timestamp: string;
}

// Display in UI:
// "Step 3 of 7: Generating flashcards..."
// "✅ Chunking completed (12 chunks created)"
// "❌ Embedding failed: Rate limit exceeded"
```

### **For `documents.metadata`:**
```typescript
// Display file info
interface DocumentMetadata {
  original_filename?: string;
  file_size?: number;
  source?: string;
  tags?: string[];
  // ... other custom fields
}

// Display in UI:
// "Original: study_notes.pdf (2.4 MB)"
// "Source: File Upload"
// "Tags: machine-learning, ai"
```

### **For `document_chunks.metadata`:**
```typescript
// Future: Better citations
interface ChunkMetadata {
  page_number?: number;
  section?: string;
  quality_score?: number;
}

// Display in UI:
// "Page 5, Section: Introduction"
// "Quality: 85%"
```

---

**Last Updated:** 2025-01-XX

