#!/bin/bash

# Flashcards Test Script
# Tests flashcards API and debugs database contents
# Run this AFTER test_document_upload.sh has completed and processing is done

BASE_URL="http://localhost:8000"
# Note: Use the email of the user who owns the document/workspace
# Default is shree6791@gmail.com (Google sign-in user, UUID: 9906b957-62cf-4c53-90d1-56a5c955ce37)
# Override with environment variables: TEST_EMAIL and TEST_PASSWORD
# IMPORTANT: If the user signed in via Google, password login won't work!
# You'll need to use Google sign-in endpoint instead with GOOGLE_ID_TOKEN
EMAIL="${TEST_EMAIL:-shree6791@gmail.com}"
PASSWORD="${TEST_PASSWORD:-SecurePass123!}"
GOOGLE_TOKEN="${GOOGLE_ID_TOKEN:-}"  # Optional: Google ID token for Google sign-in users
ACCESS_TOKEN="${ACCESS_TOKEN:-}"  # Optional: Direct access token (skips login)

echo "🔍 Testing Flashcards API"
echo "========================"
echo ""

# Check if workspace_id and document_id are provided
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: ./test_flashcards.sh <workspace_id> <document_id>"
  echo ""
  echo "Example:"
  echo "  ./test_flashcards.sh 878d0e2f-a621-472f-b3e5-cb1fa4eb21c0 45ef0649-c7b9-499a-9a86-4730b7d2a421"
  echo ""
  echo "Note: If you see 0 flashcards, check which document_id the flashcards actually have:"
  echo "  python3 debug_flashcards.py <workspace_id> <document_id>"
  echo ""
  echo "Or run test_document_upload.sh first and copy the IDs from the summary."
  exit 1
fi

WORKSPACE_ID="$1"
DOCUMENT_ID="$2"

# Note: If testing shows 0 flashcards, the flashcards might be for a different document
# The debug script will show which document_id the flashcards actually have

echo "📋 Parameters:"
echo "   - Workspace ID: ${WORKSPACE_ID}"
echo "   - Document ID: ${DOCUMENT_ID}"
echo ""

# Step 1: Login to get access token
echo "Step 1: Logging in..."
echo "Testing with user: ${EMAIL} (UUID: 9906b957-62cf-4c53-90d1-56a5c955ce37)"
echo ""

# If Google token is provided, use Google sign-in
if [ -n "$GOOGLE_TOKEN" ]; then
  echo "Using Google sign-in with provided token..."
  LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/google" \
    -H "Content-Type: application/json" \
    -d "{
      \"id_token\": \"${GOOGLE_TOKEN}\"
    }")
  ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
else
  # Try password login first
  echo "Trying password login..."
  LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"${EMAIL}\",
      \"password\": \"${PASSWORD}\"
    }")
  
  ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
  
  # Check if login failed due to Google sign-in
  if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "None" ]; then
    echo ""
    echo "⚠️  Password login failed for '${EMAIL}'"
    if [ -n "$LOGIN_RESPONSE" ]; then
      echo "   Response: $LOGIN_RESPONSE"
      ERROR_MSG=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('detail', ''))" 2>/dev/null)
      if [ -n "$ERROR_MSG" ]; then
        echo "   Error: $ERROR_MSG"
      fi
    fi
    echo ""
    echo "   This user likely signed in via Google (no password set)."
    echo ""
    echo "   Options:"
    echo "   1. Use Google ID token:"
    echo "      GOOGLE_ID_TOKEN='your_token' ./test_flashcards.sh ${WORKSPACE_ID} ${DOCUMENT_ID}"
    echo ""
    echo "   2. Test with password-based user (will show different user's flashcards):"
    echo "      TEST_EMAIL='test@example.com' TEST_PASSWORD='SecurePass123!' ./test_flashcards.sh ${WORKSPACE_ID} ${DOCUMENT_ID}"
    echo ""
    echo "   3. Continue anyway to see debug info (will fail API calls but show database state):"
    read -p "      Continue with debug only? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
    # Set empty token to continue with debug
    ACCESS_TOKEN=""
  fi
fi

if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "None" ]; then
  echo "✅ Access token obtained"
else
  echo "⚠️  No access token - will skip API tests but show debug info"
fi
echo ""

# Decode JWT to show which user is logged in (for debugging)
echo "Step 1.5: Verifying logged-in user..."
# Extract the payload from JWT (second part, base64 decoded)
JWT_PAYLOAD=$(echo "$ACCESS_TOKEN" | cut -d'.' -f2)
# Add padding if needed and decode
USER_INFO=$(echo "$JWT_PAYLOAD" | python3 -c "
import sys, json, base64
payload = sys.stdin.read().strip()
# Add padding
payload += '=' * (4 - len(payload) % 4)
try:
    decoded = base64.urlsafe_b64decode(payload)
    data = json.loads(decoded)
    print(f\"User ID: {data.get('sub', 'N/A')}\")
    print(f\"Email: {data.get('email', 'N/A')}\")
except:
    print('Could not decode JWT')
" 2>/dev/null)
if [ -n "$USER_INFO" ]; then
  echo "$USER_INFO"
fi
echo ""

# Step 2: Debug Flashcards (check what's in database)
echo "Step 2: Debugging flashcards in database..."
if [ -f "debug_flashcards.py" ]; then
  python3 debug_flashcards.py "${WORKSPACE_ID}" "${DOCUMENT_ID}" 2>&1
  echo ""
else
  echo "⚠️  debug_flashcards.py not found, skipping debug step"
  echo ""
fi

# Step 3: Test Flashcards API
echo "Step 3: Testing flashcards API..."
if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "None" ]; then
  echo "⚠️  Skipping API test (no access token)"
  FLASHCARDS_RESPONSE="[]"
  FLASHCARD_COUNT=0
else
  echo "Request: GET ${BASE_URL}/api/v1/flashcards?workspace_id=${WORKSPACE_ID}&document_id=${DOCUMENT_ID}"
  echo ""
  
  FLASHCARDS_RESPONSE=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "${BASE_URL}/api/v1/flashcards?workspace_id=${WORKSPACE_ID}&document_id=${DOCUMENT_ID}")
  
  FLASHCARD_COUNT=$(echo "$FLASHCARDS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data) if isinstance(data, list) else 0)" 2>/dev/null)
  
  if [ "$FLASHCARD_COUNT" -gt 0 ]; then
    echo "✅ Found ${FLASHCARD_COUNT} flashcard(s)"
    echo ""
    echo "📝 Flashcard details:"
    echo "$FLASHCARDS_RESPONSE" | python3 -m json.tool 2>/dev/null | head -50
  else
    echo "⚠️  No flashcards found (count: ${FLASHCARD_COUNT})"
    echo ""
    echo "Response:"
    echo "$FLASHCARDS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$FLASHCARDS_RESPONSE"
    echo ""
    echo "💡 Troubleshooting:"
    echo "   1. Check if flashcards were generated (wait a few seconds and try again)"
    echo "   2. Check server logs for any errors"
    echo "   3. Verify the user_id in your JWT token matches the document owner"
    echo "   4. Run debug_flashcards.py manually to see what's in the database"
  fi
fi
echo ""

# Step 4: Test with workspace_id only
echo "Step 4: Testing flashcards API with workspace_id only..."
if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "None" ]; then
  echo "⚠️  Skipping API test (no access token)"
  FLASHCARD_WORKSPACE_COUNT=0
else
  FLASHCARDS_WORKSPACE_RESPONSE=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "${BASE_URL}/api/v1/flashcards?workspace_id=${WORKSPACE_ID}")
  
  FLASHCARD_WORKSPACE_COUNT=$(echo "$FLASHCARDS_WORKSPACE_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data) if isinstance(data, list) else 0)" 2>/dev/null)
  
  echo "✅ Found ${FLASHCARD_WORKSPACE_COUNT} flashcard(s) in workspace"
fi
echo ""

# Summary
echo "📊 Summary:"
echo "   - Flashcards in workspace: ${FLASHCARD_WORKSPACE_COUNT}"
echo "   - Flashcards for document: ${FLASHCARD_COUNT}"
echo "   - Workspace ID: ${WORKSPACE_ID}"
echo "   - Document ID: ${DOCUMENT_ID}"
echo ""

