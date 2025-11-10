#!/bin/bash
# Deploy Frontend to S3
# Builds frontend and uploads to S3 bucket

set -e  # Exit on error

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
BUCKET_NAME="${S3_BUCKET_NAME:-room-reader-frontend-${AWS_ACCOUNT_ID}}"

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../../frontend"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Frontend Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Bucket Name: $BUCKET_NAME"
echo "Region: $AWS_REGION"
echo ""

# Step 1: Build frontend
echo -e "${YELLOW}Step 1: Building frontend...${NC}"
"$SCRIPT_DIR/build-frontend.sh"
echo ""

# Step 2: Verify S3 bucket exists
echo -e "${YELLOW}Step 2: Verifying S3 bucket...${NC}"
if ! aws s3 ls "s3://${BUCKET_NAME}" 2>/dev/null; then
    echo -e "${RED}Error: S3 bucket '$BUCKET_NAME' not found${NC}"
    echo "Please run: ./infrastructure/scripts/setup-s3-bucket.sh"
    exit 1
fi
echo "  ✓ Bucket found"
echo ""

# Step 3: Upload files to S3
echo -e "${YELLOW}Step 3: Uploading files to S3...${NC}"
cd "$FRONTEND_DIR"

if [ ! -d "dist" ]; then
    echo -e "${RED}Error: Build output directory 'dist' not found${NC}"
    echo "Please run: ./infrastructure/scripts/build-frontend.sh"
    exit 1
fi

aws s3 sync dist/ "s3://${BUCKET_NAME}/" \
    --delete \
    --region $AWS_REGION \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "*.html" \
    --exclude "*.json"

# Upload HTML files with shorter cache
aws s3 sync dist/ "s3://${BUCKET_NAME}/" \
    --delete \
    --region $AWS_REGION \
    --cache-control "public, max-age=0, must-revalidate" \
    --include "*.html" \
    --include "*.json"

echo "  ✓ Files uploaded to S3"
echo ""

# Step 4: Set content types
echo -e "${YELLOW}Step 4: Setting content types...${NC}"
aws s3 cp "s3://${BUCKET_NAME}/index.html" "s3://${BUCKET_NAME}/index.html" \
    --content-type "text/html" \
    --metadata-directive REPLACE \
    --region $AWS_REGION

echo "  ✓ Content types set"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Bucket Name: $BUCKET_NAME"
echo "Website URL: http://${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com"
echo ""
echo "Next steps:"
echo "  1. Set up CloudFront: ./infrastructure/scripts/setup-cloudfront.sh"
echo "  2. Update frontend API URL in production environment"
echo ""

