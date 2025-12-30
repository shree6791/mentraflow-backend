#!/bin/bash

# Document Upload Flow Test Script
# Tests the complete document upload flow with JWT authentication

BASE_URL="http://localhost:8000"
EMAIL="test@example.com"
PASSWORD="SecurePass123!"
USERNAME="testuser"

echo "🚀 Testing Document Upload Flow with JWT Authentication"
echo "======================================================"
echo ""

# Step 1: Signup (or login if user exists)
echo "Step 1: Signing up..."
SIGNUP_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"${USERNAME}\",
    \"email\": \"${EMAIL}\",
    \"password\": \"${PASSWORD}\",
    \"full_name\": \"Test User\"
  }")

# Check if signup failed (user might already exist)
if echo "$SIGNUP_RESPONSE" | grep -q "already exists"; then
  echo "⚠️  User already exists, logging in instead..."
  LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"${EMAIL}\",
      \"password\": \"${PASSWORD}\"
    }")
  ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
else
  ACCESS_TOKEN=$(echo $SIGNUP_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
fi

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "None" ]; then
  echo "❌ Failed to get access token"
  echo "Response: $SIGNUP_RESPONSE"
  exit 1
fi

echo "✅ Access token obtained"
echo ""

# Step 2: Create Workspace
echo "Step 2: Creating workspace..."
WORKSPACE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/workspaces" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d '{
    "name": "Test Workspace",
    "plan_tier": "free"
  }')

WORKSPACE_ID=$(echo $WORKSPACE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -z "$WORKSPACE_ID" ] || [ "$WORKSPACE_ID" == "None" ]; then
  echo "❌ Failed to create workspace"
  echo "Response: $WORKSPACE_RESPONSE"
  exit 1
fi

echo "✅ Workspace created: ${WORKSPACE_ID}"
echo ""

# Step 3: Create Document (JSON mode)
echo "Step 3: Creating document with text content..."
DOC_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/workspaces/${WORKSPACE_ID}/documents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d "{
    \"workspace_id\": \"${WORKSPACE_ID}\",
    \"title\": \"Introduction to Machine Learning\",
    \"doc_type\": \"text\",
    \"content\": \"Machine Learning (ML) is a type of Artificial Intelligence (AI) where computers learn to find patterns in large datasets and make predictions or decisions without being explicitly programmed for every task, improving performance as they process more data. It uses statistical algorithms to analyze data, learn relationships, and generalize from known examples to new, unseen data, powering things like recommendation engines, voice assistants, and fraud detection.\\n\\nHow it works\\n* Data Input: Systems are fed massive amounts of data (labeled or unlabeled).\\n* Algorithm Training: Algorithms analyze this data to identify patterns and relationships between inputs and desired outputs.\\n* Model Building: The process creates a \\\"model\\\" that can recognize these patterns.\\n* Prediction/Action: The model then uses what it learned to make predictions or classify new data, adjusting its approach as needed.\\n\\nKey types\\n* Supervised Learning: Uses labeled data (e.g., images with \\\"cat\\\" or \\\"dog\\\" labels) to predict or classify new data.\\n* Unsupervised Learning: Finds hidden patterns or structures in unlabeled data (e.g., grouping similar customer purchases).\\n* Reinforcement Learning: Learns by trial and error, receiving rewards for good actions (e.g., training a robot to navigate).\\n* Generative AI: Creates new content (text, images) by learning patterns from existing data.\\n\\nCommon applications\\n* Recommendations: Suggesting movies on Netflix or products on Amazon.\\n* Natural Language Processing: Google Translate, voice assistants like Siri and Alexa, and spam filters.\\n* Computer Vision: Facial recognition and medical image analysis (like cancer detection).\\n* Finance: Detecting fraudulent transactions.\",
    \"metadata\": {
      \"source\": \"test\",
      \"pages\": 1
    }
  }")

DOCUMENT_ID=$(echo $DOC_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null)

if [ -z "$DOCUMENT_ID" ] || [ "$DOCUMENT_ID" == "None" ]; then
  echo "❌ Failed to create document"
  echo "Full response:"
  echo "$DOC_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DOC_RESPONSE"
  echo ""
  echo "Debug: Checking if it's an error response..."
  ERROR_DETAIL=$(echo $DOC_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('detail', 'No detail field'))" 2>/dev/null)
  echo "Error detail: $ERROR_DETAIL"
  exit 1
fi

echo "✅ Document created: ${DOCUMENT_ID}"
echo ""

# Step 4: Check Document Status
echo "Step 4: Checking document status..."
echo "Note: Ingestion, summary, flashcards, and knowledge graph extraction happen automatically if preferences are enabled (default: true)"
sleep 5  # Wait a bit for processing to start

STATUS_RESPONSE=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${BASE_URL}/api/v1/documents/${DOCUMENT_ID}")

echo "✅ Document status:"
echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
echo ""

# Summary
echo "✅ Document upload flow test complete!"
echo ""
echo "📊 Summary:"
echo "   - Workspace ID: ${WORKSPACE_ID}"
echo "   - Document ID: ${DOCUMENT_ID}"
echo "   - Access Token: ${ACCESS_TOKEN:0:20}..."
echo ""
echo "🔗 Next Steps:"
echo "   - Wait for processing to complete (check document status)"
echo "   - Test flashcards: ./test_flashcards.sh ${WORKSPACE_ID} ${DOCUMENT_ID}"
echo "   - Check document: curl -H \"Authorization: Bearer ${ACCESS_TOKEN}\" ${BASE_URL}/api/v1/documents/${DOCUMENT_ID}"
echo "   - View flashcards: curl -H \"Authorization: Bearer ${ACCESS_TOKEN}\" \"${BASE_URL}/api/v1/flashcards?workspace_id=${WORKSPACE_ID}&document_id=${DOCUMENT_ID}\""
echo "   - View KG concepts: curl -H \"Authorization: Bearer ${ACCESS_TOKEN}\" \"${BASE_URL}/api/v1/kg/concepts?workspace_id=${WORKSPACE_ID}\""
echo ""

