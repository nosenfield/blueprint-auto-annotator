#!/bin/bash
# Deploy All v1 Lambda Functions
# Master script to deploy both wall detection and geometric conversion Lambdas

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploy All v1 Lambda Functions${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Setup IAM role
echo -e "${YELLOW}Step 1: Setting up IAM role...${NC}"
"$SCRIPT_DIR/setup-iam-role.sh"
echo ""

# Step 2: Deploy wall detection Lambda
echo -e "${YELLOW}Step 2: Deploying wall detection Lambda v1...${NC}"
"$SCRIPT_DIR/deploy-wall-detection-v1.sh"
echo ""

# Step 3: Deploy geometric conversion Lambda
echo -e "${YELLOW}Step 3: Deploying geometric conversion Lambda v1...${NC}"
"$SCRIPT_DIR/deploy-geometric-conversion-v1.sh"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All v1 Lambda Functions Deployed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Set up API Gateway: ./infrastructure/scripts/setup-api-gateway.sh"
echo "  2. Test Lambda functions: aws lambda invoke --function-name wall-detection-v1 ..."
echo "  3. Monitor logs: aws logs tail /aws/lambda/wall-detection-v1 --follow"
echo ""

