#!/bin/bash
# Deploy Room Model Lambda Function
# Based on validated wall model POC pattern

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

# Validate AWS credentials
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "Error: AWS credentials not configured"
    echo "Please run: aws configure"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Validate Docker
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker daemon is not running${NC}"
    exit 1
fi

ECR_REPO_NAME="room-detection-v2"
LAMBDA_FUNCTION_NAME="room-detection-v2"
LAMBDA_ROLE_NAME="yolo-lambda-execution-role"  # Reuse from POC

# Room model S3 path - Your model location
ROOM_MODEL_BUCKET="${ROOM_MODEL_BUCKET:-sagemaker-us-east-1-971422717446}"
ROOM_MODEL_KEY="${ROOM_MODEL_KEY:-room-detect-1class-yolol-800px-20ep-1762719498/output/model.tar.gz}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Room Model Lambda Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
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

# Step 2: Build Docker image
echo -e "${YELLOW}Step 2: Building Docker image...${NC}"
echo "  This may take 5-10 minutes..."
docker buildx build --platform linux/amd64 -t $ECR_REPO_NAME:latest . --load

if [ $? -eq 0 ]; then
    echo "  ✓ Docker image built successfully"
else
    echo -e "${RED}  ✗ Docker build failed${NC}"
    exit 1
fi
echo ""

# Step 3: Tag image
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

# Step 5: Push image
echo -e "${YELLOW}Step 5: Pushing image to ECR...${NC}"
echo "  This may take 5-10 minutes..."
docker push $ECR_URI:latest
echo "  ✓ Image pushed to ECR"
echo ""

# Step 6: Get or create Lambda role
echo -e "${YELLOW}Step 6: Setting up Lambda execution role...${NC}"
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

# Step 7: Deploy Lambda function
echo -e "${YELLOW}Step 7: Deploying Lambda function...${NC}"

if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION 2>/dev/null; then
    echo "  Updating existing function..."
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --image-uri $ECR_URI:latest \
        --region $AWS_REGION
    
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
        --region $AWS_REGION
    
    echo "  ✓ Function updated"
else
    echo "  Creating new function..."
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$ECR_URI:latest \
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
echo "Room Model S3 Path:"
echo "  s3://$ROOM_MODEL_BUCKET/$ROOM_MODEL_KEY"
echo ""
echo "Next steps:"
echo "  1. Test: ./test_lambda.sh <image.png>"
echo "  2. Monitor logs: aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --follow"
echo ""

