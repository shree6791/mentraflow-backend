#!/bin/bash
# Quick health check test script

echo "Testing Health Endpoints..."
echo "=========================="
echo ""

# Test /health
echo "1. Testing GET /health"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" http://localhost:8000/health)
HTTP_STATUS=$(echo "$HEALTH_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$HEALTH_RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "200" ]; then
    echo "   ✅ Status: $HTTP_STATUS"
    echo "   Response: $BODY"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo "   ❌ Status: $HTTP_STATUS"
    echo "   Response: $BODY"
fi

echo ""
echo "2. Testing GET /api/v1/version"
VERSION_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" http://localhost:8000/api/v1/version)
HTTP_STATUS=$(echo "$VERSION_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$VERSION_RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "200" ]; then
    echo "   ✅ Status: $HTTP_STATUS"
    echo "   Response: $BODY"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo "   ❌ Status: $HTTP_STATUS"
    echo "   Response: $BODY"
fi

echo ""
echo "=========================="
echo "Test complete!"

