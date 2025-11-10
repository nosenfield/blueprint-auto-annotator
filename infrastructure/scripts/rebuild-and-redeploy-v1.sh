#!/bin/bash
# Rebuild and redeploy v1 Lambda functions with OpenCV fix
# This script rebuilds Docker images and updates Lambda functions

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Rebuild & Redeploy v1 Lambdas${NC}"
echo -e "${GREEN}OpenCV libGL.so.1 Fix${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Navigate to backend directory
cd "$(dirname "$0")/../../backend"

echo -e "${YELLOW}Step 1: Login to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo "  ✓ Logged in to ECR"
echo ""

# Rebuild Wall Detection Lambda
echo -e "${YELLOW}Step 2: Building wall-detection-v1...${NC}"
docker build --platform linux/amd64 --provenance=false -t wall-detection-v1:latest -f lambda-wall-detection-v1/Dockerfile .

echo "  ✓ Built wall-detection-v1"
echo ""

# Tag and push
echo -e "${YELLOW}Step 3: Pushing wall-detection-v1 to ECR...${NC}"
docker tag wall-detection-v1:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/wall-detection-v1:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/wall-detection-v1:latest

echo "  ✓ Pushed wall-detection-v1"
echo ""

# Update Lambda function
echo -e "${YELLOW}Step 4: Updating wall-detection-v1 Lambda...${NC}"
aws lambda update-function-code \
    --function-name wall-detection-v1 \
    --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/wall-detection-v1:latest \
    --region $AWS_REGION > /dev/null

echo "  ✓ Lambda function updated"
echo "  ⏳ Waiting for function to be ready..."
aws lambda wait function-updated --function-name wall-detection-v1 --region $AWS_REGION
echo "  ✓ Function ready"
echo ""

# Rebuild Geometric Conversion Lambda
echo -e "${YELLOW}Step 5: Building geometric-conversion-v1...${NC}"
docker build --platform linux/amd64 --provenance=false -t geometric-conversion-v1:latest -f lambda-geometric-conversion-v1/Dockerfile .

echo "  ✓ Built geometric-conversion-v1"
echo ""

# Tag and push
echo -e "${YELLOW}Step 6: Pushing geometric-conversion-v1 to ECR...${NC}"
docker tag geometric-conversion-v1:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/geometric-conversion-v1:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/geometric-conversion-v1:latest

echo "  ✓ Pushed geometric-conversion-v1"
echo ""

# Update Lambda function
echo -e "${YELLOW}Step 7: Updating geometric-conversion-v1 Lambda...${NC}"
aws lambda update-function-code \
    --function-name geometric-conversion-v1 \
    --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/geometric-conversion-v1:latest \
    --region $AWS_REGION > /dev/null

echo "  ✓ Lambda function updated"
echo "  ⏳ Waiting for function to be ready..."
aws lambda wait function-updated --function-name geometric-conversion-v1 --region $AWS_REGION
echo "  ✓ Function ready"
echo ""

# Test Lambda functions
echo -e "${YELLOW}Step 8: Testing Lambda functions...${NC}"

# Test wall-detection-v1
echo "Testing wall-detection-v1..."
TEST_PAYLOAD='{"httpMethod":"GET","path":"/","headers":{},"body":null}'
aws lambda invoke \
    --function-name wall-detection-v1 \
    --payload "$TEST_PAYLOAD" \
    --region $AWS_REGION \
    /tmp/wall-detection-response.json > /dev/null 2>&1

if grep -q '"statusCode": 200' /tmp/wall-detection-response.json; then
    echo "  ✓ wall-detection-v1 working (health check passed)"
else
    echo -e "  ${RED}✗ wall-detection-v1 health check failed${NC}"
    echo "Response:"
    cat /tmp/wall-detection-response.json | jq .
fi

# Test geometric-conversion-v1
echo "Testing geometric-conversion-v1..."
aws lambda invoke \
    --function-name geometric-conversion-v1 \
    --payload "$TEST_PAYLOAD" \
    --region $AWS_REGION \
    /tmp/geometric-conversion-response.json > /dev/null 2>&1

if grep -q '"statusCode": 200' /tmp/geometric-conversion-response.json; then
    echo "  ✓ geometric-conversion-v1 working (health check passed)"
else
    echo -e "  ${RED}✗ geometric-conversion-v1 health check failed${NC}"
    echo "Response:"
    cat /tmp/geometric-conversion-response.json | jq .
fi
echo ""

# Get API Gateway URL
API_ID=$(aws apigateway get-rest-apis --region $AWS_REGION --query "items[?name=='room-reader-api'].id" --output text)
API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Rebuild Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Lambda Functions:"
echo "  ✓ wall-detection-v1: Updated"
echo "  ✓ geometric-conversion-v1: Updated"
echo ""
echo "API Endpoints:"
echo "  POST ${API_URL}/api/detect-walls"
echo "  POST ${API_URL}/api/convert-to-rooms"
echo ""
echo "Next Steps:"
echo "  1. Test API endpoints with curl or Postman"
echo "  2. Run CORS fix: ./infrastructure/scripts/fix-cors.sh"
echo "  3. Test from frontend: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com"
echo ""
echo "Check CloudWatch Logs:"
echo "  aws logs tail /aws/lambda/wall-detection-v1 --follow"
echo "  aws logs tail /aws/lambda/geometric-conversion-v1 --follow"
echo ""
