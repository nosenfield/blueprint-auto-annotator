#!/bin/bash
# Setup API Gateway for v1 Lambda Functions
# Creates REST API with endpoints for wall detection and geometric conversion

set -e  # Exit on error

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
API_NAME="room-reader-api-v1"
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
echo -e "${YELLOW}Note: This script provides basic API Gateway setup.${NC}"
echo -e "${YELLOW}For production, consider using Terraform or AWS Console for more control.${NC}"
echo ""

# Get Lambda function ARNs
WALL_DETECTION_ARN=$(aws lambda get-function --function-name wall-detection-v1 --query 'Configuration.FunctionArn' --output text --region $AWS_REGION 2>/dev/null || echo "")
GEOMETRIC_CONVERSION_ARN=$(aws lambda get-function --function-name geometric-conversion-v1 --query 'Configuration.FunctionArn' --output text --region $AWS_REGION 2>/dev/null || echo "")

if [ -z "$WALL_DETECTION_ARN" ] || [ -z "$GEOMETRIC_CONVERSION_ARN" ]; then
    echo -e "${RED}Error: Lambda functions not found${NC}"
    echo "Please deploy Lambda functions first: ./infrastructure/scripts/deploy-all-v1.sh"
    exit 1
fi

echo "Lambda Functions:"
echo "  Wall Detection: $WALL_DETECTION_ARN"
echo "  Geometric Conversion: $GEOMETRIC_CONVERSION_ARN"
echo ""

echo -e "${YELLOW}API Gateway setup requires manual configuration via AWS Console or Terraform.${NC}"
echo ""
echo "Recommended steps:"
echo "  1. Create REST API in API Gateway Console"
echo "  2. Create resources: /api/detect-walls, /api/convert-to-rooms"
echo "  3. Create POST methods for each resource"
echo "  4. Integrate with Lambda functions (Lambda proxy integration)"
echo "  5. Enable CORS for all methods"
echo "  6. Deploy to '$STAGE_NAME' stage"
echo ""
echo "Or use Terraform:"
echo "  cd infrastructure/terraform"
echo "  terraform init"
echo "  terraform plan"
echo "  terraform apply"
echo ""

