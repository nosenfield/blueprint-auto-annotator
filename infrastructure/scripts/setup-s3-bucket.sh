#!/bin/bash
# Setup S3 Bucket for Frontend Hosting
# Creates S3 bucket, enables static website hosting, and applies bucket policy

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
BUCKET_POLICY_FILE="$SCRIPT_DIR/../config/bucket-policy.json"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}S3 Bucket Setup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Bucket Name: $BUCKET_NAME"
echo "Region: $AWS_REGION"
echo ""

# Step 1: Create S3 bucket
echo -e "${YELLOW}Step 1: Creating S3 bucket...${NC}"
if aws s3 ls "s3://${BUCKET_NAME}" 2>/dev/null; then
    echo "  ✓ Bucket already exists"
else
    if [ "$AWS_REGION" = "us-east-1" ]; then
        # us-east-1 doesn't require LocationConstraint
        aws s3 mb "s3://${BUCKET_NAME}" --region $AWS_REGION
    else
        aws s3 mb "s3://${BUCKET_NAME}" --region $AWS_REGION --create-bucket-configuration LocationConstraint=$AWS_REGION
    fi
    echo "  ✓ Bucket created"
fi
echo ""

# Step 2: Enable static website hosting
echo -e "${YELLOW}Step 2: Enabling static website hosting...${NC}"
aws s3 website "s3://${BUCKET_NAME}" \
    --index-document index.html \
    --error-document index.html \
    --region $AWS_REGION

echo "  ✓ Static website hosting enabled"
echo ""

# Step 3: Apply bucket policy for public read access
echo -e "${YELLOW}Step 3: Applying bucket policy...${NC}"
if [ ! -f "$BUCKET_POLICY_FILE" ]; then
    echo -e "${RED}Error: Bucket policy file not found: $BUCKET_POLICY_FILE${NC}"
    exit 1
fi

# Update bucket name in policy file (temporary)
TEMP_POLICY=$(mktemp)
sed "s/room-reader-frontend/${BUCKET_NAME}/g" "$BUCKET_POLICY_FILE" > "$TEMP_POLICY"

aws s3api put-bucket-policy \
    --bucket "$BUCKET_NAME" \
    --policy "file://${TEMP_POLICY}" \
    --region $AWS_REGION

rm "$TEMP_POLICY"

echo "  ✓ Bucket policy applied"
echo ""

# Step 4: Block public access settings (allow public read)
echo -e "${YELLOW}Step 4: Configuring public access settings...${NC}"
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false" \
    --region $AWS_REGION

echo "  ✓ Public access configured"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}S3 Bucket Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Bucket Name: $BUCKET_NAME"
echo "Website URL: http://${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com"
echo ""
echo "Next steps:"
echo "  1. Deploy frontend: ./infrastructure/scripts/deploy-frontend.sh"
echo "  2. Set up CloudFront: ./infrastructure/scripts/setup-cloudfront.sh"
echo ""

