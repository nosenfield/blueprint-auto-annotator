#!/bin/bash
# Deploy YOLO Lambda Function
# This script builds, pushes, and deploys the Lambda container

set -e  # Exit on error

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"  # Allow override via environment variable
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

# Validate AWS credentials
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}Error: AWS credentials not configured or invalid${NC}"
    echo "Please run: aws configure"
    exit 1
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Validate Docker is running
echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker daemon is not running${NC}"
    echo ""
    echo "Please start Docker Desktop:"
    echo "  1. Open Docker Desktop application"
    echo "  2. Wait for it to fully start (whale icon in menu bar)"
    echo "  3. Run this script again"
    echo ""
    echo "Or start Docker Desktop from command line:"
    echo "  open -a Docker"
    exit 1
fi
echo "  ✓ Docker is running"

# Validate Docker command works
if ! docker --version > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker command not found${NC}"
    echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi
echo "  ✓ Docker command available"
echo ""

ECR_REPO_NAME="yolo-room-detection"
LAMBDA_FUNCTION_NAME="yolo-room-detection"
LAMBDA_ROLE_NAME="yolo-lambda-execution-role"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}YOLO Lambda Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Create ECR repository if it doesn't exist
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

# Step 2: Build Docker image for Linux x86_64 (Lambda requirement)
echo -e "${YELLOW}Step 2: Building Docker image for Linux x86_64...${NC}"
echo "  This may take 5-10 minutes..."
echo "  Building for platform: linux/amd64 (Lambda requirement)"
docker buildx build --platform linux/amd64 -t $ECR_REPO_NAME:latest . --load

if [ $? -eq 0 ]; then
    echo "  ✓ Docker image built successfully"
else
    echo -e "${RED}  ✗ Docker build failed${NC}"
    exit 1
fi
echo ""

# Step 3: Tag image for ECR
echo -e "${YELLOW}Step 3: Tagging image...${NC}"
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest
echo "  ✓ Image tagged"
echo ""

# Step 4: Login to ECR
echo -e "${YELLOW}Step 4: Logging in to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URI
echo "  ✓ Logged in to ECR"
echo ""

# Step 5: Push image to ECR
echo -e "${YELLOW}Step 5: Pushing image to ECR...${NC}"
echo "  This may take 5-10 minutes..."
docker push $ECR_URI:latest
echo "  ✓ Image pushed to ECR"
echo ""

# Step 6: Create Lambda execution role if it doesn't exist
echo -e "${YELLOW}Step 6: Creating Lambda execution role...${NC}"
ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
    # Create role
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
    
    # Attach policies
    aws iam attach-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    aws iam attach-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
    
    # Wait for role to be available
    echo "  Waiting for role to propagate..."
    sleep 10
    
    ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text)
    echo "  ✓ Role created: $ROLE_ARN"
else
    echo "  ✓ Role already exists: $ROLE_ARN"
fi
echo ""

# Step 7: Create or update Lambda function
echo -e "${YELLOW}Step 7: Deploying Lambda function...${NC}"

# Check if function exists
if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION 2>/dev/null; then
    # Update existing function
    echo "  Updating existing function..."
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --image-uri $ECR_URI:latest \
        --region $AWS_REGION
    
    # Wait for update to complete
    echo "  Waiting for function update..."
    aws lambda wait function-updated \
        --function-name $LAMBDA_FUNCTION_NAME \
        --region $AWS_REGION
    
    echo "  ✓ Function updated"
else
    # Create new function
    echo "  Creating new function..."
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$ECR_URI:latest \
        --role $ROLE_ARN \
        --timeout 300 \
        --memory-size 3008 \
        --region $AWS_REGION \
        --environment Variables="{
            MODEL_S3_BUCKET=sagemaker-us-east-1-971422717446,
            MODEL_S3_KEY=room-detection-yolo-1762559721/output/model.tar.gz,
            CONFIDENCE_THRESHOLD=0.5,
            IOU_THRESHOLD=0.4,
            IMAGE_SIZE=640
        }"
    
    echo "  ✓ Function created"
fi
echo ""

# Step 8: Test the function
echo -e "${YELLOW}Step 8: Testing Lambda function...${NC}"
echo "  You can test with: ./test_lambda.sh"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Function Name: $LAMBDA_FUNCTION_NAME"
echo "Function ARN: $(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $AWS_REGION)"
echo "Memory: 3008 MB"
echo "Timeout: 300 seconds (5 minutes)"
echo ""
echo "Next steps:"
echo "  1. Test: ./test_lambda.sh"
echo "  2. Set up API Gateway (optional): ./setup_api_gateway.sh"
echo "  3. Monitor logs: aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --follow"
echo ""
echo -e "${YELLOW}Cost estimate:${NC}"
echo "  Cold start: ~10-15 seconds (first request)"
echo "  Warm invocation: ~0.5-2 seconds"
echo "  Cost per 1000 requests: ~\$0.50-2.00 (depending on duration)"
echo "  No charges when idle"
echo ""
