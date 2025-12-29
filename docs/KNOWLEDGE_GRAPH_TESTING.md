# Knowledge Graph Testing Guide

This guide walks you through testing the knowledge graph extraction and exploration flow using the MentraFlow API.

## Prerequisites

1. **Server Running**: Make sure your FastAPI server is running
   ```bash
   make run
   # or
   make run-debug
   ```

2. **Have a Document Ready**: You should have a document that has been:
   - Uploaded and ingested (status = `ready`)
   - Has summary and flashcards (optional, but recommended)
   - Contains meaningful content for concept extraction

3. **Have Credentials Ready**: You'll need:
   - `workspace_id` - Your workspace ID
   - `user_id` - Your user ID
   - `document_id` - ID of the document you want to extract KG from

---

## Step 1: Extract Knowledge Graph from Document

**Endpoint:** `POST /api/v1/documents/{document_id}/kg`

Extract concepts and relationships from a document. This runs asynchronously in the background.

```bash
curl -X POST "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/kg" \
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
  "message": "KG extraction queued. Check agent_runs table for status."
}
```

**Note:** 
- KG extraction always runs asynchronously
- Uses OpenAI `gpt-4o-mini` to extract concepts and relationships
- Concepts are stored in the database and Qdrant (`mentraflow_concepts` collection)
- Relationships are stored as edges in the knowledge graph

**Check Agent Run Status:**
```bash
curl "http://localhost:8000/api/v1/agent-runs/YOUR_RUN_ID"
```

**Expected Output:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "completed",
  "agent_name": "kg_extraction",
  "output_json": {
    "concepts_written": 15,
    "edges_written": 12,
    "concepts": [...],
    "edges": [...]
  }
}
```

---

## Step 2: List Concepts

**Endpoint:** `GET /api/v1/kg/concepts?workspace_id={workspace_id}`

List all concepts extracted from documents in your workspace.

```bash
curl "http://localhost:8000/api/v1/kg/concepts?workspace_id=YOUR_WORKSPACE_ID&limit=20&offset=0"
```

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `document_id` (UUID, optional): Filter by document ID (when implemented)
- `q` (string, optional): Search query to filter by name/description
- `limit` (int, default: 20, max: 100): Maximum number of results
- `offset` (int, default: 0): Offset for pagination

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440014",
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Machine Learning",
    "description": "A subset of artificial intelligence that focuses on algorithms that can learn from data",
    "type": "concept",
    "aliases": ["ML", "ML algorithms"],
    "tags": ["AI", "data science"],
    "metadata": {},
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440015",
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Supervised Learning",
    "description": "Machine learning approach that uses labeled data to train models",
    "type": "concept",
    "aliases": null,
    "tags": ["ML", "training"],
    "metadata": {},
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

**Search Concepts:**
```bash
curl "http://localhost:8000/api/v1/kg/concepts?workspace_id=YOUR_WORKSPACE_ID&q=machine%20learning"
```

---

## Step 3: Get Concept Details

**Endpoint:** `GET /api/v1/kg/concepts/{concept_id}`

Get detailed information about a specific concept.

```bash
curl "http://localhost:8000/api/v1/kg/concepts/YOUR_CONCEPT_ID"
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440014",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Machine Learning",
  "description": "A subset of artificial intelligence that focuses on algorithms that can learn from data",
  "type": "concept",
  "aliases": ["ML", "ML algorithms"],
  "tags": ["AI", "data science"],
  "metadata": {},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

## Step 4: Explore Concept Neighbors

**Endpoint:** `GET /api/v1/kg/concepts/{concept_id}/neighbors?depth=1`

Get neighboring concepts connected to a specific concept through relationships.

```bash
# Get neighbors at depth 1 (direct connections)
curl "http://localhost:8000/api/v1/kg/concepts/YOUR_CONCEPT_ID/neighbors?depth=1"
```

**Query Parameters:**
- `depth` (int, default: 1, min: 1, max: 3): How many levels of neighbors to traverse

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440015",
    "name": "Supervised Learning",
    "description": "Machine learning approach that uses labeled data",
    "type": "concept",
    ...
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440016",
    "name": "Unsupervised Learning",
    "description": "Machine learning approach that finds patterns in unlabeled data",
    "type": "concept",
    ...
  }
]
```

**Get Neighbors at Depth 2:**
```bash
curl "http://localhost:8000/api/v1/kg/concepts/YOUR_CONCEPT_ID/neighbors?depth=2"
```

This will return concepts that are 1 or 2 steps away from the target concept.

---

## Step 5: List Knowledge Graph Edges

**Endpoint:** `GET /api/v1/kg/edges?workspace_id={workspace_id}`

List all relationships (edges) between concepts in your workspace.

```bash
# List all edges in workspace
curl "http://localhost:8000/api/v1/kg/edges?workspace_id=YOUR_WORKSPACE_ID&limit=20&offset=0"
```

**Query Parameters:**
- `workspace_id` (UUID, required): Workspace ID
- `concept_id` (UUID, optional): Filter edges by concept (where concept is either source or destination)
- `limit` (int, default: 20, max: 100): Maximum number of results
- `offset` (int, default: 0): Offset for pagination

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440020",
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "src_type": "concept",
    "src_id": "550e8400-e29b-41d4-a716-446655440014",
    "rel_type": "is_type_of",
    "dst_type": "concept",
    "dst_id": "550e8400-e29b-41d4-a716-446655440015",
    "weight": 0.95,
    "evidence": {
      "source": "document_chunk_123",
      "confidence": 0.9
    },
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**List Edges for a Specific Concept:**
```bash
curl "http://localhost:8000/api/v1/kg/edges?workspace_id=YOUR_WORKSPACE_ID&concept_id=YOUR_CONCEPT_ID"
```

This returns all edges where the concept is either the source or destination.

---

## Quick Test Script

Save this as `test_kg_flow.sh`:

```bash
#!/bin/bash

# Configuration
BASE_URL="http://localhost:8000"
WORKSPACE_ID="YOUR_WORKSPACE_ID"  # Replace with your workspace ID
USER_ID="YOUR_USER_ID"  # Replace with your user ID
DOCUMENT_ID="YOUR_DOCUMENT_ID"  # Replace with your document ID

echo "🧠 Testing Knowledge Graph Flow"
echo "================================"

# Step 1: Extract Knowledge Graph
echo ""
echo "Step 1: Extracting knowledge graph from document..."
KG_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/documents/${DOCUMENT_ID}/kg" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace_id\": \"${WORKSPACE_ID}\",
    \"user_id\": \"${USER_ID}\"
  }")
RUN_ID=$(echo $KG_RESPONSE | grep -o '"run_id":"[^"]*' | cut -d'"' -f4)
echo "✅ KG extraction queued:"
echo $KG_RESPONSE | python3 -m json.tool
echo "Run ID: ${RUN_ID}"

# Wait for processing
echo ""
echo "Waiting for KG extraction to complete (checking every 2 seconds)..."
for i in {1..30}; do
  sleep 2
  RUN_STATUS=$(curl -s "${BASE_URL}/api/v1/agent-runs/${RUN_ID}")
  STATUS=$(echo $RUN_STATUS | grep -o '"status":"[^"]*' | cut -d'"' -f4)
  echo "  Status: ${STATUS}"
  if [ "$STATUS" = "completed" ]; then
    echo "✅ KG extraction completed!"
    echo $RUN_STATUS | python3 -m json.tool
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "❌ KG extraction failed!"
    echo $RUN_STATUS | python3 -m json.tool
    exit 1
  fi
done

# Step 2: List Concepts
echo ""
echo "Step 2: Listing concepts..."
CONCEPTS=$(curl -s "${BASE_URL}/api/v1/kg/concepts?workspace_id=${WORKSPACE_ID}&limit=10")
echo "✅ Concepts found:"
echo $CONCEPTS | python3 -m json.tool

# Extract first concept ID
FIRST_CONCEPT_ID=$(echo $CONCEPTS | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
if [ -n "$FIRST_CONCEPT_ID" ]; then
  echo ""
  echo "Using concept ID: ${FIRST_CONCEPT_ID}"
  
  # Step 3: Get Concept Details
  echo ""
  echo "Step 3: Getting concept details..."
  CONCEPT=$(curl -s "${BASE_URL}/api/v1/kg/concepts/${FIRST_CONCEPT_ID}")
  echo "✅ Concept details:"
  echo $CONCEPT | python3 -m json.tool
  
  # Step 4: Get Concept Neighbors
  echo ""
  echo "Step 4: Getting concept neighbors..."
  NEIGHBORS=$(curl -s "${BASE_URL}/api/v1/kg/concepts/${FIRST_CONCEPT_ID}/neighbors?depth=1")
  echo "✅ Neighbors:"
  echo $NEIGHBORS | python3 -m json.tool
else
  echo "⚠️  No concepts found"
fi

# Step 5: List Edges
echo ""
echo "Step 5: Listing knowledge graph edges..."
EDGES=$(curl -s "${BASE_URL}/api/v1/kg/edges?workspace_id=${WORKSPACE_ID}&limit=10")
echo "✅ Edges found:"
echo $EDGES | python3 -m json.tool

echo ""
echo "✅ Knowledge graph flow test complete!"
echo "📊 Summary:"
echo "   - Workspace: ${WORKSPACE_ID}"
echo "   - Document: ${DOCUMENT_ID}"
echo "   - Run ID: ${RUN_ID}"
echo "   - View concepts: ${BASE_URL}/api/v1/kg/concepts?workspace_id=${WORKSPACE_ID}"
echo "   - View edges: ${BASE_URL}/api/v1/kg/edges?workspace_id=${WORKSPACE_ID}"
```

**Make it executable:**
```bash
chmod +x test_kg_flow.sh
./test_kg_flow.sh
```

---

## Common Issues & Solutions

### Issue: "Document {document_id} not found" (404)
**Solution:** 
- Make sure the document exists and you're using the correct `document_id`
- Verify the document has been uploaded and ingested (status = `ready`)

### Issue: KG extraction stuck at "queued" or "running"
**Solution:**
1. Check agent run status: `GET /api/v1/agent-runs/{run_id}`
2. Look for errors in the agent run `error` field
3. Check server logs for detailed error messages
4. Verify OpenAI API key is configured correctly

### Issue: "No concepts found" after extraction
**Solution:**
- The document content might not contain extractable concepts
- Try with a document that has clear concepts and relationships (e.g., technical documentation, educational content)
- Check the agent run output to see if concepts were extracted but not stored

### Issue: "Concept {concept_id} not found" (404)
**Solution:**
- Make sure you're using a valid concept ID from your workspace
- Verify the concept exists by listing concepts first

### Issue: Empty neighbors list
**Solution:**
- The concept might not have any relationships (edges) connected to it
- Try increasing the depth parameter: `?depth=2` or `?depth=3`
- Check if edges exist: `GET /api/v1/kg/edges?workspace_id={workspace_id}`

---

## Understanding the Knowledge Graph

### Concepts
- **Concepts** are key entities extracted from documents (e.g., "Machine Learning", "Neural Network", "Supervised Learning")
- Each concept has:
  - `name`: The concept name
  - `description`: Detailed description of the concept
  - `type`: Concept type (e.g., "concept", "entity", "term")
  - `aliases`: Alternative names for the concept
  - `tags`: Categorization tags

### Edges (Relationships)
- **Edges** represent relationships between concepts
- Each edge has:
  - `src_id`: Source concept ID
  - `dst_id`: Destination concept ID
  - `rel_type`: Type of relationship (e.g., "is_type_of", "related_to", "uses")
  - `weight`: Relationship strength (0.0-1.0)
  - `evidence`: Supporting evidence from the document

### Example Knowledge Graph Structure

**Concepts:**
- A: "Machine Learning"
- B: "Supervised Learning"
- C: "Unsupervised Learning"
- D: "Neural Network"

**Edges:**
- A → B: "is_type_of" (Machine Learning is type of Supervised Learning)
- A → C: "is_type_of" (Machine Learning is type of Unsupervised Learning)
- B → D: "uses" (Supervised Learning uses Neural Network)

---

## Next Steps

After successful KG extraction:
- ✅ Explore concepts: `GET /api/v1/kg/concepts`
- ✅ Find related concepts: `GET /api/v1/kg/concepts/{concept_id}/neighbors`
- ✅ Analyze relationships: `GET /api/v1/kg/edges`
- ✅ Build visualizations using the graph structure
- ✅ Use concepts for enhanced search and recommendations

See `API_ROUTES.md` for detailed endpoint documentation.

