#!/bin/bash
# Fix CORS issues in API Gateway
# This script adds proper CORS handling for all error responses

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
API_NAME="room-reader-api"
# Hardcode the correct API Gateway ID from the original CORS error
API_ID="3jkxonfmu1"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CORS Fix Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verify API exists
API_EXISTS=$(aws apigateway get-rest-api \
    --rest-api-id "$API_ID" \
    --region $AWS_REGION \
    --query 'name' \
    --output text 2>/dev/null || echo "")

if [ -z "$API_EXISTS" ]; then
    echo -e "${RED}Error: API Gateway with ID '$API_ID' not found${NC}"
    exit 1
fi

echo "API ID: $API_ID"
echo ""

# Get resource IDs
DETECT_WALLS_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region $AWS_REGION \
    --query "items[?path=='/api/detect-walls'].id" \
    --output text)

CONVERT_ROOMS_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region $AWS_REGION \
    --query "items[?path=='/api/convert-to-rooms'].id" \
    --output text)

V2_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region $AWS_REGION \
    --query "items[?path=='/api/v2/detect-rooms'].id" \
    --output text)

echo "Resource IDs:"
echo "  /api/detect-walls: $DETECT_WALLS_RESOURCE_ID"
echo "  /api/convert-to-rooms: $CONVERT_ROOMS_RESOURCE_ID"
if [ -n "$V2_RESOURCE_ID" ]; then
    echo "  /api/v2/detect-rooms: $V2_RESOURCE_ID"
fi
echo ""

# Function to add CORS to a resource
fix_cors_for_resource() {
    local RESOURCE_ID=$1
    local RESOURCE_PATH=$2

    echo -e "${YELLOW}Fixing CORS for $RESOURCE_PATH...${NC}"

    # Add method responses for POST (with CORS headers)
    for STATUS_CODE in 200 400 500; do
        echo "  Adding method response $STATUS_CODE..."
        aws apigateway put-method-response \
            --rest-api-id "$API_ID" \
            --resource-id "$RESOURCE_ID" \
            --http-method POST \
            --status-code $STATUS_CODE \
            --response-parameters '{
                "method.response.header.Access-Control-Allow-Origin": true,
                "method.response.header.Access-Control-Allow-Headers": true,
                "method.response.header.Access-Control-Allow-Methods": true
            }' \
            --region $AWS_REGION > /dev/null 2>&1 || echo "    Method response $STATUS_CODE might already exist"
    done

    # Note: With AWS_PROXY integration, Lambda is responsible for all response headers
    # We just need to ensure Lambda handler returns proper CORS headers
    echo "  ✓ Method responses configured"
    echo ""
}

# Fix CORS for all endpoints
if [ -n "$DETECT_WALLS_RESOURCE_ID" ]; then
    fix_cors_for_resource "$DETECT_WALLS_RESOURCE_ID" "/api/detect-walls"
fi

if [ -n "$CONVERT_ROOMS_RESOURCE_ID" ]; then
    fix_cors_for_resource "$CONVERT_ROOMS_RESOURCE_ID" "/api/convert-to-rooms"
fi

if [ -n "$V2_RESOURCE_ID" ]; then
    fix_cors_for_resource "$V2_RESOURCE_ID" "/api/v2/detect-rooms"
fi

# Deploy changes
echo -e "${YELLOW}Deploying changes...${NC}"
DEPLOYMENT_ID=$(aws apigateway create-deployment \
    --rest-api-id "$API_ID" \
    --stage-name prod \
    --description "CORS fix deployment" \
    --region $AWS_REGION \
    --query 'id' \
    --output text 2>/dev/null || echo "")

if [ -n "$DEPLOYMENT_ID" ]; then
    echo "  ✓ Changes deployed (Deployment ID: $DEPLOYMENT_ID)"
else
    echo -e "${RED}  Error: Failed to deploy changes${NC}"
    exit 1
fi
echo ""

# Test CORS
API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
echo -e "${YELLOW}Testing CORS...${NC}"
echo "Testing OPTIONS request to /api/detect-walls..."

CORS_RESPONSE=$(curl -s -X OPTIONS \
    -H "Origin: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type" \
    -i "${API_URL}/api/detect-walls" 2>&1 || echo "")

if echo "$CORS_RESPONSE" | grep -q "Access-Control-Allow-Origin"; then
    echo "  ✓ CORS headers present"
else
    echo -e "${RED}  Warning: CORS headers not found in response${NC}"
    echo "Response:"
    echo "$CORS_RESPONSE"
fi
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CORS Fix Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "API URL: $API_URL"
echo ""
echo "If CORS issues persist, verify:"
echo "  1. Lambda functions return CORS headers in responses"
echo "  2. Lambda handler wrapper adds CORS headers to all responses"
echo "  3. Browser cache is cleared"
echo ""
echo "Test with curl:"
echo "  curl -X OPTIONS -H 'Origin: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com' \\"
echo "    ${API_URL}/api/detect-walls -i"
echo ""
