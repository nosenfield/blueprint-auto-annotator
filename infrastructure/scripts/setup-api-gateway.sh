#!/bin/bash
# Setup API Gateway for v1 and v2 Lambda Functions
# Creates REST API with endpoints for wall detection, geometric conversion, and room detection

set -e  # Exit on error

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
API_NAME="room-reader-api"
STAGE_NAME="prod"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Validate AWS credentials
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}Error: AWS credentials not configured or invalid${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}API Gateway Setup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get Lambda function ARNs
WALL_DETECTION_ARN=$(aws lambda get-function --function-name wall-detection-v1 --query 'Configuration.FunctionArn' --output text --region $AWS_REGION 2>/dev/null || echo "")
GEOMETRIC_CONVERSION_ARN=$(aws lambda get-function --function-name geometric-conversion-v1 --query 'Configuration.FunctionArn' --output text --region $AWS_REGION 2>/dev/null || echo "")
ROOM_DETECTION_ARN=$(aws lambda get-function --function-name room-detection-v2 --query 'Configuration.FunctionArn' --output text --region $AWS_REGION 2>/dev/null || echo "")

if [ -z "$WALL_DETECTION_ARN" ] || [ -z "$GEOMETRIC_CONVERSION_ARN" ]; then
    echo -e "${RED}Error: v1 Lambda functions not found${NC}"
    echo "Please deploy Lambda functions first: ./infrastructure/scripts/deploy-all-v1.sh"
    exit 1
fi

echo "Lambda Functions:"
echo "  Wall Detection (v1): $WALL_DETECTION_ARN"
echo "  Geometric Conversion (v1): $GEOMETRIC_CONVERSION_ARN"
if [ -n "$ROOM_DETECTION_ARN" ]; then
    echo "  Room Detection (v2): $ROOM_DETECTION_ARN"
fi
echo ""

# Step 1: Create REST API
echo -e "${YELLOW}Step 1: Creating REST API...${NC}"
API_ID=$(aws apigateway create-rest-api \
    --name "$API_NAME" \
    --description "Room Reader API - Wall and Room Detection" \
    --endpoint-configuration types=REGIONAL \
    --region $AWS_REGION \
    --query 'id' \
    --output text 2>/dev/null || echo "")

if [ -z "$API_ID" ]; then
    # API might already exist, try to get it
    API_ID=$(aws apigateway get-rest-apis \
        --region $AWS_REGION \
        --query "items[?name=='$API_NAME'].id" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$API_ID" ]; then
        echo -e "${RED}Error: Failed to create or find REST API${NC}"
        exit 1
    fi
    echo "  ✓ API already exists: $API_ID"
else
    echo "  ✓ API created: $API_ID"
fi
echo ""

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region $AWS_REGION \
    --query 'items[?path==`/`].id' \
    --output text)

echo "Root Resource ID: $ROOT_RESOURCE_ID"
echo ""

# Step 2: Create /api resource
echo -e "${YELLOW}Step 2: Creating /api resource...${NC}"
API_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$ROOT_RESOURCE_ID" \
    --path-part "api" \
    --region $AWS_REGION \
    --query 'id' \
    --output text 2>/dev/null || echo "")

if [ -z "$API_RESOURCE_ID" ]; then
    # Resource might already exist
    API_RESOURCE_ID=$(aws apigateway get-resources \
        --rest-api-id "$API_ID" \
        --region $AWS_REGION \
        --query "items[?path=='/api'].id" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$API_RESOURCE_ID" ]; then
        echo -e "${RED}Error: Failed to create /api resource${NC}"
        exit 1
    fi
    echo "  ✓ /api resource already exists"
else
    echo "  ✓ /api resource created"
fi
echo ""

# Step 3: Create /api/detect-walls resource
echo -e "${YELLOW}Step 3: Creating /api/detect-walls resource...${NC}"
DETECT_WALLS_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$API_RESOURCE_ID" \
    --path-part "detect-walls" \
    --region $AWS_REGION \
    --query 'id' \
    --output text 2>/dev/null || echo "")

if [ -z "$DETECT_WALLS_RESOURCE_ID" ]; then
    DETECT_WALLS_RESOURCE_ID=$(aws apigateway get-resources \
        --rest-api-id "$API_ID" \
        --region $AWS_REGION \
        --query "items[?path=='/api/detect-walls'].id" \
        --output text 2>/dev/null || echo "")
    echo "  ✓ /api/detect-walls resource already exists"
else
    echo "  ✓ /api/detect-walls resource created"
fi
echo ""

# Step 4: Create POST method for /api/detect-walls
echo -e "${YELLOW}Step 4: Creating POST method for /api/detect-walls...${NC}"
aws apigateway put-method \
    --rest-api-id "$API_ID" \
    --resource-id "$DETECT_WALLS_RESOURCE_ID" \
    --http-method POST \
    --authorization-type NONE \
    --region $AWS_REGION \
    --no-api-key-required > /dev/null 2>&1 || echo "  Method might already exist"

# Set up Lambda integration
aws apigateway put-integration \
    --rest-api-id "$API_ID" \
    --resource-id "$DETECT_WALLS_RESOURCE_ID" \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${WALL_DETECTION_ARN}/invocations" \
    --region $AWS_REGION > /dev/null 2>&1 || echo "  Integration might already exist"

echo "  ✓ POST method created for /api/detect-walls"
echo ""

# Step 5: Create /api/convert-to-rooms resource
echo -e "${YELLOW}Step 5: Creating /api/convert-to-rooms resource...${NC}"
CONVERT_ROOMS_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$API_RESOURCE_ID" \
    --path-part "convert-to-rooms" \
    --region $AWS_REGION \
    --query 'id' \
    --output text 2>/dev/null || echo "")

if [ -z "$CONVERT_ROOMS_RESOURCE_ID" ]; then
    CONVERT_ROOMS_RESOURCE_ID=$(aws apigateway get-resources \
        --rest-api-id "$API_ID" \
        --region $AWS_REGION \
        --query "items[?path=='/api/convert-to-rooms'].id" \
        --output text 2>/dev/null || echo "")
    echo "  ✓ /api/convert-to-rooms resource already exists"
else
    echo "  ✓ /api/convert-to-rooms resource created"
fi
echo ""

# Step 6: Create POST method for /api/convert-to-rooms
echo -e "${YELLOW}Step 6: Creating POST method for /api/convert-to-rooms...${NC}"
aws apigateway put-method \
    --rest-api-id "$API_ID" \
    --resource-id "$CONVERT_ROOMS_RESOURCE_ID" \
    --http-method POST \
    --authorization-type NONE \
    --region $AWS_REGION \
    --no-api-key-required > /dev/null 2>&1 || echo "  Method might already exist"

aws apigateway put-integration \
    --rest-api-id "$API_ID" \
    --resource-id "$CONVERT_ROOMS_RESOURCE_ID" \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${GEOMETRIC_CONVERSION_ARN}/invocations" \
    --region $AWS_REGION > /dev/null 2>&1 || echo "  Integration might already exist"

echo "  ✓ POST method created for /api/convert-to-rooms"
echo ""

# Step 7: Create /api/v2 resource (if v2 Lambda exists)
if [ -n "$ROOM_DETECTION_ARN" ]; then
    echo -e "${YELLOW}Step 7: Creating /api/v2 resource...${NC}"
    V2_RESOURCE_ID=$(aws apigateway create-resource \
        --rest-api-id "$API_ID" \
        --parent-id "$API_RESOURCE_ID" \
        --path-part "v2" \
        --region $AWS_REGION \
        --query 'id' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$V2_RESOURCE_ID" ]; then
        V2_RESOURCE_ID=$(aws apigateway get-resources \
            --rest-api-id "$API_ID" \
            --region $AWS_REGION \
            --query "items[?path=='/api/v2'].id" \
            --output text 2>/dev/null || echo "")
        echo "  ✓ /api/v2 resource already exists"
    else
        echo "  ✓ /api/v2 resource created"
    fi
    echo ""
    
    # Create /api/v2/detect-rooms resource
    echo -e "${YELLOW}Step 8: Creating /api/v2/detect-rooms resource...${NC}"
    DETECT_ROOMS_V2_RESOURCE_ID=$(aws apigateway create-resource \
        --rest-api-id "$API_ID" \
        --parent-id "$V2_RESOURCE_ID" \
        --path-part "detect-rooms" \
        --region $AWS_REGION \
        --query 'id' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$DETECT_ROOMS_V2_RESOURCE_ID" ]; then
        DETECT_ROOMS_V2_RESOURCE_ID=$(aws apigateway get-resources \
            --rest-api-id "$API_ID" \
            --region $AWS_REGION \
            --query "items[?path=='/api/v2/detect-rooms'].id" \
            --output text 2>/dev/null || echo "")
        echo "  ✓ /api/v2/detect-rooms resource already exists"
    else
        echo "  ✓ /api/v2/detect-rooms resource created"
    fi
    echo ""
    
    # Create POST method for /api/v2/detect-rooms
    echo -e "${YELLOW}Step 9: Creating POST method for /api/v2/detect-rooms...${NC}"
    aws apigateway put-method \
        --rest-api-id "$API_ID" \
        --resource-id "$DETECT_ROOMS_V2_RESOURCE_ID" \
        --http-method POST \
        --authorization-type NONE \
        --region $AWS_REGION \
        --no-api-key-required > /dev/null 2>&1 || echo "  Method might already exist"
    
    aws apigateway put-integration \
        --rest-api-id "$API_ID" \
        --resource-id "$DETECT_ROOMS_V2_RESOURCE_ID" \
        --http-method POST \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${ROOM_DETECTION_ARN}/invocations" \
        --region $AWS_REGION > /dev/null 2>&1 || echo "  Integration might already exist"
    
    echo "  ✓ POST method created for /api/v2/detect-rooms"
    echo ""
fi

# Step 8: Grant API Gateway permission to invoke Lambda functions
echo -e "${YELLOW}Step 10: Granting API Gateway permission to invoke Lambda functions...${NC}"

# Grant permission for wall-detection-v1
aws lambda add-permission \
    --function-name wall-detection-v1 \
    --statement-id apigateway-invoke-wall-detection \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*/*" \
    --region $AWS_REGION > /dev/null 2>&1 || echo "  Permission might already exist"

# Grant permission for geometric-conversion-v1
aws lambda add-permission \
    --function-name geometric-conversion-v1 \
    --statement-id apigateway-invoke-geometric-conversion \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*/*" \
    --region $AWS_REGION > /dev/null 2>&1 || echo "  Permission might already exist"

# Grant permission for room-detection-v2 (if exists)
if [ -n "$ROOM_DETECTION_ARN" ]; then
    aws lambda add-permission \
        --function-name room-detection-v2 \
        --statement-id apigateway-invoke-room-detection \
        --action lambda:InvokeFunction \
        --principal apigateway.amazonaws.com \
        --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*/*" \
        --region $AWS_REGION > /dev/null 2>&1 || echo "  Permission might already exist"
fi

echo "  ✓ Permissions granted"
echo ""

# Step 9: Deploy API to production stage
echo -e "${YELLOW}Step 11: Deploying API to production stage...${NC}"
DEPLOYMENT_ID=$(aws apigateway create-deployment \
    --rest-api-id "$API_ID" \
    --stage-name "$STAGE_NAME" \
    --description "Production deployment" \
    --region $AWS_REGION \
    --query 'id' \
    --output text 2>/dev/null || echo "")

if [ -z "$DEPLOYMENT_ID" ]; then
    echo -e "${YELLOW}  Warning: Deployment might already exist. Updating...${NC}"
    # Try to update existing deployment
    DEPLOYMENT_ID=$(aws apigateway create-deployment \
        --rest-api-id "$API_ID" \
        --stage-name "$STAGE_NAME" \
        --description "Updated deployment" \
        --region $AWS_REGION \
        --query 'id' \
        --output text 2>/dev/null || echo "")
fi

if [ -n "$DEPLOYMENT_ID" ]; then
    echo "  ✓ API deployed to $STAGE_NAME stage"
else
    echo -e "${YELLOW}  Warning: Deployment might need manual update${NC}"
fi
echo ""

# Get API Gateway URL
API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}"

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}API Gateway Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "API ID: $API_ID"
echo "API URL: $API_URL"
echo ""
echo "Endpoints:"
echo "  POST $API_URL/api/detect-walls → wall-detection-v1"
echo "  POST $API_URL/api/convert-to-rooms → geometric-conversion-v1"
if [ -n "$ROOM_DETECTION_ARN" ]; then
    echo "  POST $API_URL/api/v2/detect-rooms → room-detection-v2"
fi
echo ""
echo "Next steps:"
echo "  1. Update frontend .env.production with API URL: $API_URL"
echo "  2. Test endpoints: curl -X POST $API_URL/api/detect-walls ..."
echo "  3. Deploy frontend: ./infrastructure/scripts/deploy-frontend.sh"
echo ""
