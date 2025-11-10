#!/bin/bash
# Deploy Wall Detection Lambda v1
# Builds Docker image, pushes to ECR, and creates/updates Lambda function

set -e  # Exit on error

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
ECR_REPO_NAME="wall-detection-v1"
LAMBDA_FUNCTION_NAME="wall-detection-v1"
LAMBDA_ROLE_NAME="room-reader-lambda-execution-role"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Validate AWS credentials
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}Error: AWS credentials not configured or invalid${NC}"
    echo "Please run: aws configure"
    exit 1
fi

# Validate Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker daemon is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Wall Detection Lambda v1 Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
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
echo ""

# Step 2: Get IAM role ARN
echo -e "${YELLOW}Step 2: Getting IAM role...${NC}"
ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")
if [ -z "$ROLE_ARN" ]; then
    echo -e "${RED}Error: IAM role '$LAMBDA_ROLE_NAME' not found${NC}"
    echo "Please run: ./infrastructure/scripts/setup-iam-role.sh"
    exit 1
fi
echo "  ✓ Role found: $ROLE_ARN"
echo ""

# Step 3: Login to ECR
echo -e "${YELLOW}Step 3: Logging in to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URI
echo "  ✓ Logged in to ECR"
echo ""

# Step 4: Build Docker image
echo -e "${YELLOW}Step 4: Building Docker image...${NC}"
echo "  This may take 5-10 minutes..."
echo "  Building for platform: linux/amd64 (Lambda requirement)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../../backend"
cd "$BACKEND_DIR"
docker buildx build --platform linux/amd64 -f lambda-wall-detection-v1/Dockerfile -t $ECR_REPO_NAME:latest --load .
echo "  ✓ Docker image built"
echo ""

# Step 5: Tag image
echo -e "${YELLOW}Step 5: Tagging image...${NC}"
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest
echo "  ✓ Image tagged"
echo ""

# Step 6: Push image to ECR
echo -e "${YELLOW}Step 6: Pushing image to ECR...${NC}"
echo "  This may take 5-10 minutes..."
docker push $ECR_URI:latest
echo "  ✓ Image pushed to ECR"
echo ""

# Step 7: Create or update Lambda function
echo -e "${YELLOW}Step 7: Creating/updating Lambda function...${NC}"
if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION 2>/dev/null; then
    echo "  Updating existing function..."
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --image-uri $ECR_URI:latest \
        --region $AWS_REGION
    
    echo "  Waiting for function update..."
    aws lambda wait function-updated \
        --function-name $LAMBDA_FUNCTION_NAME \
        --region $AWS_REGION
    
    echo "  ✓ Function updated"
else
    echo "  Creating new function..."
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$ECR_URI:latest \
        --role $ROLE_ARN \
        --timeout 30 \
        --memory-size 3008 \
        --region $AWS_REGION \
        --description "Wall detection Lambda v1 - YOLO-based wall detection from blueprints"
    
    echo "  ✓ Function created"
fi
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Function Name: $LAMBDA_FUNCTION_NAME"
echo "Function ARN: $(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $AWS_REGION)"
echo "Memory: 3008 MB"
echo "Timeout: 30 seconds"
echo "ECR Repository: $ECR_URI"
echo ""

