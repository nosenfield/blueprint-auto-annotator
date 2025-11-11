#!/bin/bash
# Deploy Room Detection v2 Lambda Function
# Based on validated v1 deployment pattern with --provenance=false flag

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
echo -e "${GREEN}Deploy Room Detection v2 Lambda${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Navigate to backend directory
cd "$(dirname "$0")/../../backend"

# Room model S3 configuration
ROOM_MODEL_BUCKET="sagemaker-us-east-1-971422717446"
ROOM_MODEL_KEY="room-detect-1class-yolol-800px-20ep-1762719498/output/model.tar.gz"

ECR_REPO_NAME="room-detection-v2"
LAMBDA_FUNCTION_NAME="room-detection-v2"
LAMBDA_ROLE_NAME="yolo-lambda-execution-role"  # Reuse from v1

echo "Room Model S3 Path:"
echo "  Bucket: $ROOM_MODEL_BUCKET"
echo "  Key: $ROOM_MODEL_KEY"
echo ""

# Step 1: Create ECR repository
echo -e "${YELLOW}Step 1: Creating ECR repository...${NC}"
if aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null; then
    echo "  ✓ ECR repository already exists"
else
    aws ecr create-repository \
        --repository-name $ECR_REPO_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true
    echo "  ✓ ECR repository created"
fi

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
echo "  Repository URI: $ECR_URI"
echo ""

# Step 2: Login to ECR
echo -e "${YELLOW}Step 2: Logging in to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
echo "  ✓ Logged in to ECR"
echo ""

# Step 3: Build Docker image (with --provenance=false for Lambda compatibility)
echo -e "${YELLOW}Step 3: Building Docker image...${NC}"
echo "  This may take 5-10 minutes..."
docker build \
    --platform linux/amd64 \
    --provenance=false \
    -t room-detection-v2:latest \
    -f lambda-room-detection-v2/Dockerfile .

if [ $? -eq 0 ]; then
    echo "  ✓ Docker image built successfully"
else
    echo -e "${RED}  ✗ Docker build failed${NC}"
    exit 1
fi
echo ""

# Step 4: Tag and push image
echo -e "${YELLOW}Step 4: Tagging and pushing image to ECR...${NC}"
docker tag room-detection-v2:latest ${ECR_URI}:latest
docker push ${ECR_URI}:latest
echo "  ✓ Image pushed to ECR"
echo ""

# Step 5: Get or create Lambda role
echo -e "${YELLOW}Step 5: Setting up Lambda execution role...${NC}"
ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
    echo "  Creating new role..."
    TRUST_POLICY='{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "lambda.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }'
    
    aws iam create-role \
        --role-name $LAMBDA_ROLE_NAME \
        --assume-role-policy-document "$TRUST_POLICY"
    
    aws iam attach-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    aws iam attach-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
    
    sleep 10
    ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text)
    echo "  ✓ Role created: $ROLE_ARN"
else
    echo "  ✓ Role already exists: $ROLE_ARN"
fi
echo ""

# Step 6: Deploy Lambda function
echo -e "${YELLOW}Step 6: Deploying Lambda function...${NC}"

if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION 2>/dev/null; then
    echo "  Updating existing function..."
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --image-uri ${ECR_URI}:latest \
        --region $AWS_REGION > /dev/null
    
    echo "  ⏳ Waiting for function to be ready..."
    aws lambda wait function-updated \
        --function-name $LAMBDA_FUNCTION_NAME \
        --region $AWS_REGION
    
    # Update environment variables and ephemeral storage
    aws lambda update-function-configuration \
        --function-name $LAMBDA_FUNCTION_NAME \
        --environment Variables="{
            MODEL_S3_BUCKET=$ROOM_MODEL_BUCKET,
            MODEL_S3_KEY=$ROOM_MODEL_KEY,
            CONFIDENCE_THRESHOLD=0.5,
            IOU_THRESHOLD=0.4,
            IMAGE_SIZE=640
        }" \
        --ephemeral-storage Size=3072 \
        --region $AWS_REGION > /dev/null
    
    echo "  ✓ Function updated"
else
    echo "  Creating new function..."
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=${ECR_URI}:latest \
        --role $ROLE_ARN \
        --timeout 300 \
        --memory-size 3008 \
        --ephemeral-storage Size=3072 \
        --region $AWS_REGION \
        --environment Variables="{
            MODEL_S3_BUCKET=$ROOM_MODEL_BUCKET,
            MODEL_S3_KEY=$ROOM_MODEL_KEY,
            CONFIDENCE_THRESHOLD=0.5,
            IOU_THRESHOLD=0.4,
            IMAGE_SIZE=640
        }"
    
    echo "  ✓ Function created"
fi
echo ""

# Step 7: Test Lambda function
echo -e "${YELLOW}Step 7: Testing Lambda function...${NC}"
TEST_PAYLOAD='{"httpMethod":"GET","path":"/","headers":{},"body":null}'
aws lambda invoke \
    --function-name $LAMBDA_FUNCTION_NAME \
    --payload "$TEST_PAYLOAD" \
    --region $AWS_REGION \
    /tmp/room-detection-v2-response.json > /dev/null 2>&1

if grep -q '"statusCode": 200' /tmp/room-detection-v2-response.json; then
    echo "  ✓ room-detection-v2 working (health check passed)"
else
    echo -e "  ${RED}✗ room-detection-v2 health check failed${NC}"
    echo "Response:"
    cat /tmp/room-detection-v2-response.json | jq . 2>/dev/null || cat /tmp/room-detection-v2-response.json
fi
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Function Name: $LAMBDA_FUNCTION_NAME"
FUNCTION_ARN=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $AWS_REGION)
echo "Function ARN: $FUNCTION_ARN"
echo "Memory: 3008 MB"
echo "Timeout: 300 seconds (5 minutes)"
echo "Ephemeral Storage: 3072 MB (3 GB)"
echo ""
echo "Room Model S3 Path:"
echo "  s3://$ROOM_MODEL_BUCKET/$ROOM_MODEL_KEY"
echo ""
echo "Next Steps:"
echo "  1. Add Lambda to API Gateway: ./infrastructure/scripts/setup-api-gateway.sh"
echo "  2. Test Lambda: cd backend/lambda-room-detection-v2 && ./test_lambda.sh <image.png>"
echo "  3. Monitor logs: aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --follow"
echo ""

