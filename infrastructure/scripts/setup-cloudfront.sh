#!/bin/bash
# Setup CloudFront Distribution for Frontend
# Creates CloudFront distribution pointing to S3 bucket

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

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CloudFront Setup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Note: CloudFront setup requires manual configuration via AWS Console or Terraform.${NC}"
echo ""
echo "Recommended Configuration:"
echo "  Origin: S3 bucket ($BUCKET_NAME)"
echo "  Origin Domain: ${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com"
echo "  Origin Type: S3 Website Endpoint"
echo "  Default Root Object: index.html"
echo "  Viewer Protocol Policy: Redirect HTTP to HTTPS"
echo "  Allowed HTTP Methods: GET, HEAD, OPTIONS"
echo "  Price Class: Use Only North America and Europe (PriceClass_100)"
echo ""
echo "Cache Behaviors:"
echo "  Default (*):"
echo "    - Cache Policy: CachingOptimized"
echo "    - Origin Request Policy: None"
echo "    - Response Headers Policy: None"
echo ""
echo "  /index.html:"
echo "    - Cache Policy: CachingDisabled"
echo "    - Origin Request Policy: None"
echo ""
echo "Error Pages:"
echo "  404 → /index.html (200 status code) - For SPA routing"
echo "  403 → /index.html (200 status code)"
echo ""
echo "To create via AWS CLI (advanced):"
echo "  See: https://docs.aws.amazon.com/cloudfront/latest/DeveloperGuide/GettingStarted.html"
echo ""
echo "Or use Terraform:"
echo "  cd infrastructure/terraform"
echo "  terraform init"
echo "  terraform plan"
echo "  terraform apply"
echo ""

