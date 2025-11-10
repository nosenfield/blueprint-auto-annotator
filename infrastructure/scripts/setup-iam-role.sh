#!/bin/bash
# Setup IAM Role for Lambda Functions
# Creates IAM role with necessary permissions for Lambda execution

set -e  # Exit on error

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
LAMBDA_ROLE_NAME="room-reader-lambda-execution-role"

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
echo -e "${GREEN}IAM Role Setup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if role exists
echo -e "${YELLOW}Checking for existing IAM role...${NC}"
ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -n "$ROLE_ARN" ]; then
    echo "  ✓ Role already exists: $ROLE_ARN"
    echo ""
    echo "Role is ready to use!"
    exit 0
fi

# Create role
echo -e "${YELLOW}Creating IAM role...${NC}"

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
    --assume-role-policy-document "$TRUST_POLICY" \
    --description "Execution role for Room Reader Lambda functions"

# Attach basic execution policy
echo "  Attaching basic execution policy..."
aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Attach S3 read access (if models are in S3)
echo "  Attaching S3 read access policy..."
aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Wait for role to be available
echo "  Waiting for role to propagate..."
sleep 10

ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text)
echo "  ✓ Role created: $ROLE_ARN"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}IAM Role Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Role Name: $LAMBDA_ROLE_NAME"
echo "Role ARN: $ROLE_ARN"
echo ""

