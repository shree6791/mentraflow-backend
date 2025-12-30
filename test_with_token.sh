#!/bin/bash

# Quick test script using an existing access token
# Usage: ./test_with_token.sh <workspace_id> <document_id> <access_token>

BASE_URL="http://localhost:8000"

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
  echo "Usage: ./test_with_token.sh <workspace_id> <document_id> <access_token>"
  echo ""
  echo "Example:"
  echo "  ./test_with_token.sh 878d0e2f-a621-472f-b3e5-cb1fa4eb21c0 85715f20-4b39-402a-9ea0-9910fbe03141 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'"
  exit 1
fi

WORKSPACE_ID="$1"
DOCUMENT_ID="$2"
ACCESS_TOKEN="$3"

echo "🔍 Testing Flashcards API with Access Token"
echo "==========================================="
echo ""
echo "📋 Parameters:"
echo "   - Workspace ID: ${WORKSPACE_ID}"
echo "   - Document ID: ${DOCUMENT_ID}"
echo "   - Token: ${ACCESS_TOKEN:0:50}..."
echo ""

# Decode token to show user info
echo "🔐 Decoding token..."
TOKEN_PAYLOAD=$(echo "$ACCESS_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -m json.tool 2>/dev/null)
if [ -n "$TOKEN_PAYLOAD" ]; then
  echo "$TOKEN_PAYLOAD" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'   - User ID: {data.get(\"sub\", \"N/A\")}'); print(f'   - Expires: {data.get(\"exp\", \"N/A\")}')" 2>/dev/null
else
  echo "   ⚠️  Could not decode token (may be expired or invalid)"
fi
echo ""

# Test flashcards endpoint
echo "📚 Testing flashcards endpoint..."
FLASHCARDS_RESPONSE=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${BASE_URL}/api/v1/flashcards?workspace_id=${WORKSPACE_ID}&document_id=${DOCUMENT_ID}")

FLASHCARD_COUNT=$(echo "$FLASHCARDS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data) if isinstance(data, list) else 0)" 2>/dev/null)

if [ "$FLASHCARD_COUNT" -gt 0 ]; then
  echo "✅ Found ${FLASHCARD_COUNT} flashcard(s)"
  echo ""
  echo "📝 Flashcard details:"
  echo "$FLASHCARDS_RESPONSE" | python3 -m json.tool 2>/dev/null | head -100
else
  echo "⚠️  No flashcards found (count: ${FLASHCARD_COUNT})"
  echo ""
  echo "Response:"
  echo "$FLASHCARDS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$FLASHCARDS_RESPONSE"
fi
echo ""

# Test with workspace_id only
echo "📚 Testing flashcards endpoint (workspace only)..."
FLASHCARDS_WORKSPACE_RESPONSE=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${BASE_URL}/api/v1/flashcards?workspace_id=${WORKSPACE_ID}")

FLASHCARD_WORKSPACE_COUNT=$(echo "$FLASHCARDS_WORKSPACE_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data) if isinstance(data, list) else 0)" 2>/dev/null)

echo "✅ Found ${FLASHCARD_WORKSPACE_COUNT} flashcard(s) in workspace"
echo ""

# Summary
echo "📊 Summary:"
echo "   - Flashcards in workspace: ${FLASHCARD_WORKSPACE_COUNT}"
echo "   - Flashcards for document: ${FLASHCARD_COUNT}"
echo "   - Workspace ID: ${WORKSPACE_ID}"
echo "   - Document ID: ${DOCUMENT_ID}"
echo ""

