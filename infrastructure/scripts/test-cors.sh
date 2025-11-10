#!/bin/bash

# CORS Validation Script
# Tests CORS configuration for API Gateway endpoints

set -e

API_URL="${API_URL:-https://0zem13mmcb.execute-api.us-east-1.amazonaws.com/prod}"
ORIGIN="${ORIGIN:-http://localhost:4000}"

echo "🧪 CORS Validation Tests"
echo "========================"
echo "API URL: ${API_URL}"
echo "Origin: ${ORIGIN}"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: OPTIONS preflight request
echo "1️⃣  Testing OPTIONS preflight request..."
echo "----------------------------------------"
OPTIONS_RESPONSE=$(curl -s -i -X OPTIONS "${API_URL}/api/detect-walls" \
  -H "Origin: ${ORIGIN}" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" 2>&1)

if echo "$OPTIONS_RESPONSE" | grep -qi "access-control-allow-origin"; then
    echo -e "${GREEN}✅ OPTIONS request includes CORS headers${NC}"
    echo "$OPTIONS_RESPONSE" | grep -i "access-control" | head -5
else
    echo -e "${RED}❌ OPTIONS request missing CORS headers${NC}"
    echo "$OPTIONS_RESPONSE" | head -10
fi
echo ""

# Test 2: POST request with CORS headers
echo "2️⃣  Testing POST request with CORS headers..."
echo "----------------------------------------------"
POST_RESPONSE=$(echo '{"image":"test"}' | curl -s -i -X POST "${API_URL}/api/detect-walls" \
  -H "Origin: ${ORIGIN}" \
  -H "Content-Type: application/json" \
  -d @- 2>&1)

if echo "$POST_RESPONSE" | grep -qi "access-control-allow-origin"; then
    echo -e "${GREEN}✅ POST request includes CORS headers${NC}"
    echo "$POST_RESPONSE" | grep -i "access-control" | head -5
else
    echo -e "${RED}❌ POST request missing CORS headers${NC}"
    echo "$POST_RESPONSE" | head -10
fi
echo ""

# Test 3: Check status code
echo "3️⃣  Checking response status..."
echo "--------------------------------"
STATUS_CODE=$(echo "$POST_RESPONSE" | head -1 | grep -oE "HTTP/[0-9.]+ [0-9]+" | awk '{print $2}')
echo "Status Code: ${STATUS_CODE}"

if [ "$STATUS_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Request succeeded${NC}"
elif [ "$STATUS_CODE" = "500" ]; then
    echo -e "${YELLOW}⚠️  Request returned 500 (Lambda error - check logs)${NC}"
    echo "Response body:"
    echo "$POST_RESPONSE" | tail -5
else
    echo -e "${YELLOW}⚠️  Unexpected status code: ${STATUS_CODE}${NC}"
fi
echo ""

# Test 4: Test from browser perspective
echo "4️⃣  Browser console test instructions..."
echo "----------------------------------------"
echo "Open browser console and run:"
echo ""
echo "fetch('${API_URL}/api/detect-walls', {"
echo "  method: 'POST',"
echo "  headers: { 'Content-Type': 'application/json' },"
echo "  body: JSON.stringify({ image: 'test' })"
echo "})"
echo ".then(r => {"
echo "  console.log('Status:', r.status);"
echo "  console.log('CORS headers:', r.headers.get('access-control-allow-origin'));"
echo "  return r.json();"
echo "})"
echo ".then(d => console.log('Response:', d))"
echo ".catch(e => console.error('Error:', e));"
echo ""

echo "✅ CORS validation complete!"
echo ""
echo "Expected results:"
echo "  - OPTIONS request: 200 with CORS headers"
echo "  - POST request: 200/500 with CORS headers (even on error)"
echo "  - Browser: No CORS errors in console"

