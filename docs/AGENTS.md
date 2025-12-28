# MentraFlow Agents Documentation

## Overview

MentraFlow uses a centralized agent architecture built on **LangGraph** for multi-step LLM workflows. All agents follow a consistent pattern:

- **BaseAgent** pattern with logging and run tracking
- **LangGraph** workflows for state management and conditional logic
- **Structured I/O** using Pydantic models
- **Shared GraphRegistry** for performance (singleton pattern)
- **Async support** with background task execution
- **Agent run tracking** in the `agent_runs` table

---

## Table of Contents

1. [IngestionAgent](#ingestionagent)
2. [StudyChatAgent](#studychatagent)
3. [FlashcardAgent](#flashcardagent)
4. [KGExtractionAgent](#kgextractionagent)
5. [SummaryAgent](#summaryagent)

---

## IngestionAgent

**Purpose:** Process and ingest documents: chunk text, generate embeddings, and optionally create summaries.

**Agent Name:** `ingestion`

**API Endpoint:** `POST /api/v1/documents/{document_id}/ingest`

### Input Schema

```python
class IngestionAgentInput(BaseModel):
    document_id: uuid.UUID          # Document ID to process
    workspace_id: uuid.UUID         # Workspace ID
    user_id: uuid.UUID              # User ID
    raw_text: str | None            # Optional raw text to store
```

### Output Schema

```python
class IngestionAgentOutput(BaseModel):
    document_id: uuid.UUID          # Processed document ID
    chunks_created: int              # Number of chunks created
    embeddings_created: int          # Number of embeddings created
    status: str                     # Final document status
    run_id: uuid.UUID | None        # Agent run ID for tracking
```

### Workflow Steps

1. **Validate Document** - Check document exists and is in valid state
2. **Chunk Document** - Split document into semantic chunks using `ChunkingService`
3. **Generate Embeddings** - Create vector embeddings using OpenAI `text-embedding-3-small`
4. **Store in Qdrant** - Upsert vectors to Qdrant collection (`mentraflow_chunks`)
5. **Generate Summary** (optional) - If `auto_summary_after_ingest` preference is enabled, generate summary using `SummaryAgent`
6. **Update Status** - Mark document as `ready` or `failed`

### Key Features

- **Idempotency:** Prevents duplicate ingestion runs
- **Status Tracking:** Updates document status throughout process (`storing` → `chunking` → `embedding` → `ready`)
- **Error Handling:** Graceful failure with document status update
- **Step Logging:** Logs each step in `agent_runs.steps` JSONB field
- **Auto-summary:** Optionally generates summary based on user preferences

### Technologies

- **LLM:** None (uses embeddings only)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Vector DB:** Qdrant (`mentraflow_chunks` collection)
- **Services:** `ChunkingService`, `EmbeddingService`, `SummaryAgent` (optional)

### Graph File

`app/agents/graphs/ingestion_graph.py`

---

## StudyChatAgent

**Purpose:** Answer study questions using semantic retrieval with citations. Ensures answers are based ONLY on retrieved chunks.

**Agent Name:** `study_chat`

**API Endpoint:** `POST /api/v1/chat`

### Input Schema

```python
class StudyChatAgentInput(BaseModel):
    workspace_id: uuid.UUID                    # Workspace ID
    user_id: uuid.UUID                        # User ID
    message: str                               # User's question or message
    document_id: uuid.UUID | None              # Optional document ID to focus on
    conversation_id: uuid.UUID | None          # Optional conversation ID for follow-up
    previous_messages: list[dict] | None        # Previous messages for context
    top_k: int = 8                             # Number of chunks to retrieve (1-50)
```

### Output Schema

```python
class StudyChatAgentOutput(BaseModel):
    answer: str                                # Answer to user's question
    citations: list[Citation]                  # Citations from retrieved chunks
    suggested_note: SuggestedNote | None       # Optional suggested note
    confidence_score: float | None             # Confidence score (0.0-1.0)
    insufficient_info: bool                    # Whether chunks contain insufficient info
```

### Workflow Steps

1. **Reformulate Query** - Use conversation history to reformulate query for better retrieval
2. **Semantic Search** - Retrieve relevant chunks using Qdrant semantic search
3. **Generate Answer** - Use LLM with structured output to generate answer based ONLY on retrieved chunks
4. **Validate Citations** - Verify and repair citations to ensure they reference actual retrieved chunks
5. **Build Output** - Construct final response with answer, citations, and optional suggested note

### Key Features

- **Guardrails:** Answers ONLY using retrieved chunks (no hallucination)
- **Citation Validation:** Ensures all citations reference actual retrieved chunks
- **Empty Retrieval Handling:** Returns helpful message if no chunks found
- **Conversation Context:** Supports follow-up questions with conversation history
- **Confidence Scoring:** LLM provides confidence score for answer quality
- **Document Scoping:** Can focus search on specific document

### Technologies

- **LLM:** OpenAI `gpt-4o-mini` (via `OPENAI_MODEL` setting)
- **Embeddings:** OpenAI `text-embedding-3-small` for query embedding
- **Vector DB:** Qdrant (`mentraflow_chunks` collection)
- **Services:** `RetrievalService`, `ConversationService`

### Prompt File

`app/agents/prompts/study_chat.txt`

### Graph File

`app/agents/graphs/study_chat_graph.py`

---

## FlashcardAgent

**Purpose:** Generate flashcards from documents in various modes (key_terms, qa, cloze) with quality validation.

**Agent Name:** `flashcard`

**API Endpoint:** `POST /api/v1/documents/{document_id}/flashcards`

### Input Schema

```python
class FlashcardAgentInput(BaseModel):
    workspace_id: uuid.UUID                    # Workspace ID
    user_id: uuid.UUID                        # User ID
    source_document_id: uuid.UUID              # Source document ID
    mode: str = "key_terms"                   # Generation mode: key_terms, qa, or cloze
```

### Output Schema

```python
class FlashcardAgentOutput(BaseModel):
    flashcards_created: int                    # Number of flashcards created
    preview: list[FlashcardPreview]            # Preview of created flashcards
    reason: str | None                        # Reason for empty result
    dropped_count: int                         # Number of cards dropped due to validation
    dropped_reasons: list[dict]                 # Details of dropped cards and reasons
    batch_id: uuid.UUID | None                # Batch/generation ID
```

### Workflow Steps

1. **Retrieve Chunks** - Semantic search for relevant chunks from document
2. **Generate Flashcards** - LLM generates flashcards in requested mode
3. **Validate Cards** - Validate and prune flashcards (length limits, content quality, mode matching)
4. **Create Flashcards** - Store validated flashcards in database
5. **Build Preview** - Create preview of generated flashcards

### Key Features

- **Multiple Modes:** Supports `key_terms`, `qa`, and `cloze` flashcard types
- **Quality Control:** Validates flashcards for length, content quality, and mode matching
- **Duplicate Prevention:** Tracks flashcards by `batch_id` and can detect existing flashcards
- **Bad Card Pruning:** Drops trivial, repetitive, or invalid flashcards
- **Short Doc Handling:** Detects insufficient content and returns appropriate reason
- **Source Tracking:** Links flashcards to source chunks via `source_chunk_ids`

### Technologies

- **LLM:** OpenAI `gpt-4o-mini` (via `OPENAI_MODEL` setting)
- **Embeddings:** OpenAI `text-embedding-3-small` for semantic search
- **Vector DB:** Qdrant (`mentraflow_chunks` collection)
- **Services:** `RetrievalService`, `FlashcardService`

### Prompt File

`app/agents/prompts/flashcard.txt`

### Graph File

`app/agents/graphs/flashcard_graph.py`

---

## KGExtractionAgent

**Purpose:** Extract concepts and relationships from documents to build a knowledge graph.

**Agent Name:** `kg_extraction`

**API Endpoint:** `POST /api/v1/documents/{document_id}/kg`

### Input Schema

```python
class KGExtractionAgentInput(BaseModel):
    workspace_id: uuid.UUID                    # Workspace ID
    user_id: uuid.UUID                        # User ID
    source_document_id: uuid.UUID              # Source document ID
```

### Output Schema

```python
class KGExtractionAgentOutput(BaseModel):
    concepts_written: int                       # Number of concepts written
    edges_written: int                          # Number of edges written
    concepts: list[ExtractedConcept]            # Extracted concepts
    edges: list[ExtractedEdge]                  # Extracted edges
```

### Workflow Steps

1. **Retrieve Chunks** - Semantic search for relevant chunks from document
2. **Extract Concepts** - LLM extracts key concepts with descriptions and types
3. **Extract Relationships** - LLM extracts relationships between concepts
4. **Store Concepts** - Store concepts in database and Qdrant (`mentraflow_concepts` collection)
5. **Store Edges** - Store relationships as edges in knowledge graph

### Key Features

- **Concept Extraction:** Identifies key concepts with descriptions, types, and confidence scores
- **Relationship Extraction:** Extracts relationships between concepts with types and weights
- **Vector Storage:** Stores concept embeddings in Qdrant for semantic search
- **Graph Building:** Creates knowledge graph structure in PostgreSQL
- **Confidence Scoring:** Provides confidence scores for extracted concepts and edges

### Technologies

- **LLM:** OpenAI `gpt-4o-mini` (via `OPENAI_MODEL` setting)
- **Embeddings:** OpenAI `text-embedding-3-small` for concept embeddings
- **Vector DB:** Qdrant (`mentraflow_concepts` collection)
- **Services:** `RetrievalService`, `KGService`

### Prompt File

`app/agents/prompts/kg_extraction.txt`

### Graph File

`app/agents/graphs/kg_graph.py`

---

## SummaryAgent

**Purpose:** Generate concise, quality-aware document summaries using semantic retrieval and conservative LLM generation.

**Agent Name:** `summary`

**API Endpoint:** `POST /api/v1/documents/{document_id}/summary`

### Input Schema

```python
class SummaryAgentInput(BaseModel):
    document_id: uuid.UUID                     # Document ID to summarize
    workspace_id: uuid.UUID                   # Workspace ID
    user_id: uuid.UUID                        # User ID
    max_bullets: int = 7                       # Maximum bullet points (1-20)
```

### Output Schema

```python
class SummaryAgentOutput(BaseModel):
    document_id: uuid.UUID                     # Document ID that was summarized
    summary: str                               # Generated summary text
    summary_length: int                        # Length of summary in characters
    run_id: uuid.UUID | None                  # Agent run ID for tracking
```

### Workflow Steps

1. **Retrieve Chunks** - Semantic search for most important chunks using multiple queries
2. **Analyze Quality** - Analyze content quality (repetition, substance, diversity)
3. **Generate Summary** - LLM generates conservative summary with quality-aware prompts
4. **Store Summary** - Store summary in document record

### Key Features

- **Semantic Retrieval:** Uses multiple semantic queries to find important chunks
- **Quality Analysis:** Detects repetitive content and lacks substance
- **Conservative Generation:** Avoids fabrication, focuses on explicitly stated information
- **Diversity Filtering:** Ensures chunks are from different sections of document
- **Fallback Handling:** Falls back to first chunks if semantic retrieval fails
- **Quality-Aware Prompts:** Adjusts prompts based on content quality metrics

### Technologies

- **LLM:** OpenAI `gpt-4o-mini` (via `OPENAI_MODEL` setting)
- **Embeddings:** OpenAI `text-embedding-3-small` for semantic search
- **Vector DB:** Qdrant (`mentraflow_chunks` collection)
- **Services:** `RetrievalService`, `SummaryService` (for storage)

### Prompt File

`app/agents/prompts/summary.txt`

### Graph File

`app/agents/graphs/summary_graph.py`

---

## Common Architecture

### BaseAgent Pattern

All agents inherit from `BaseAgent` which provides:

- **Logging:** Automatic agent run logging to `agent_runs` table
- **Error Handling:** Standardized error handling and status updates
- **Run Tracking:** Tracks run status (`queued` → `running` → `succeeded`/`failed`)
- **Shared LLM:** Uses centralized LLM from `GraphRegistry` for performance

### GraphRegistry (Singleton)

- **Shared Resources:** Single instance across all requests
- **Lazy Loading:** Graphs created on first access
- **Stateless Graphs:** Service tools and DB passed in state at runtime
- **Performance:** Reuses compiled graphs for better performance

### Agent Router

The `AgentRouter` provides a unified interface for running agents:

```python
agent_router.run_ingestion(input_data)
agent_router.run_study_chat(input_data)
agent_router.run_flashcard(input_data)
agent_router.run_kg_extraction(input_data)
agent_router.run_summary(input_data)
```

### Async Support

All agents support async execution:

- **Sync Mode:** Returns agent output directly
- **Async Mode:** Returns `AsyncTaskResponse` with `run_id` for status tracking
- **Background Tasks:** Uses FastAPI `BackgroundTasks` for async execution
- **Status Tracking:** Check `agent_runs` table or use `GET /api/v1/agent-runs/{run_id}`

### Error Handling

- **Graceful Failures:** Agents update status to `failed` and log errors
- **User-Friendly Messages:** Returns actionable error messages
- **Run Tracking:** All errors logged in `agent_runs` table
- **Retry Support:** Failed runs can be retried using the same input

---

## Agent Run Tracking

All agent executions are tracked in the `agent_runs` table:

- **Run ID:** Unique identifier for each run
- **Status:** `queued`, `running`, `succeeded`, `failed`
- **Input/Output:** JSON storage of input and output data
- **Steps:** JSONB field for step-by-step progress (when implemented)
- **Timestamps:** Created, started, and completed timestamps

Query agent runs:
- `GET /api/v1/agent-runs` - List all runs with filters
- `GET /api/v1/agent-runs/{run_id}` - Get specific run details

---

## OpenAI Usage

All agents that use LLMs consume OpenAI API:

- **Model:** `gpt-4o-mini` (configurable via `OPENAI_MODEL`)
- **Embeddings:** `text-embedding-3-small` (configurable via `OPENAI_EMBEDDING_MODEL`)
- **Cost Tracking:** Monitor usage via OpenAI dashboard
- **Rate Limiting:** Consider implementing rate limiting for production

See `docs/OPENAI_SETUP_GUIDE.md` for setup and cost estimation.

---

## Development

### Adding a New Agent

1. Create input/output types in `app/agents/types.py`
2. Create agent class in `app/agents/{agent_name}_agent.py`
3. Create LangGraph workflow in `app/agents/graphs/{agent_name}_graph.py`
4. Create prompt file in `app/agents/prompts/{agent_name}.txt`
5. Update `GraphRegistry` to include new graph
6. Update `AgentRouter` to include new agent
7. Create API endpoint in appropriate router
8. Update this documentation

### Testing Agents

- Use `AgentRouter` directly in tests
- Mock `GraphRegistry` and services for unit tests
- Use test database and Qdrant for integration tests
- Check `agent_runs` table for execution logs

---

## Summary

MentraFlow has **5 agents** covering all LLM-based operations:

1. **IngestionAgent** - Document processing and embedding
2. **StudyChatAgent** - Q&A with citations
3. **FlashcardAgent** - Flashcard generation
4. **KGExtractionAgent** - Knowledge graph extraction
5. **SummaryAgent** - Document summarization

All agents use:
- **LangGraph** for workflow orchestration
- **Structured I/O** with Pydantic models
- **Shared resources** via GraphRegistry
- **Run tracking** in database
- **Async support** for long-running operations

