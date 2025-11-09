#!/bin/bash
# Quick fix: Rebuild and redeploy Lambda function

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_URI="971422717446.dkr.ecr.us-east-1.amazonaws.com/yolo-room-detection"
LAMBDA_FUNCTION_NAME="yolo-room-detection"

# Helper function to print timestamped messages
log_step() {
    local step_num=$1
    local step_name=$2
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Step ${step_num}: ${step_name}${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Started at: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
}

log_complete() {
    local duration=$1
    echo -e "${GREEN}✓ Completed in ${duration}s${NC}"
}

# Track start time
SCRIPT_START=$(date +%s)

# Step 1: Build Docker image
log_step "1" "Rebuilding Docker image for Linux x86_64"
STEP_START=$(date +%s)
echo -e "${YELLOW}Building image (this may take 5-10 minutes)...${NC}"
echo ""

docker buildx build --platform linux/amd64 -t yolo-room-detection:latest . --load --progress=plain

STEP_DURATION=$(($(date +%s) - STEP_START))
log_complete $STEP_DURATION

# Show image size
IMAGE_SIZE=$(docker images yolo-room-detection:latest --format '{{.Size}}' 2>/dev/null || echo "unknown")
echo -e "${GREEN}Image size: ${IMAGE_SIZE}${NC}"

# Step 2: Tag image
log_step "2" "Tagging image"
STEP_START=$(date +%s)

docker tag yolo-room-detection:latest $ECR_URI:latest

STEP_DURATION=$(($(date +%s) - STEP_START))
log_complete $STEP_DURATION

# Step 3: Login to ECR
log_step "3" "Logging in to ECR"
STEP_START=$(date +%s)

echo -e "${YELLOW}Authenticating with ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_URI 2>&1 | grep -v "WARNING" || true

STEP_DURATION=$(($(date +%s) - STEP_START))
log_complete $STEP_DURATION

# Step 4: Push to ECR
log_step "4" "Pushing image to ECR"
STEP_START=$(date +%s)

echo -e "${YELLOW}Image size: ${IMAGE_SIZE}${NC}"
echo -e "${YELLOW}Pushing to: ${ECR_URI}${NC}"
echo -e "${YELLOW}This may take 3-8 minutes depending on upload speed...${NC}"
echo ""
echo -e "${CYAN}Progress:${NC}"

docker push --progress=plain $ECR_URI:latest

STEP_DURATION=$(($(date +%s) - STEP_START))
log_complete $STEP_DURATION

# Step 5: Update Lambda function
log_step "5" "Updating Lambda function"
STEP_START=$(date +%s)

echo -e "${YELLOW}Updating function code...${NC}"
aws lambda update-function-code \
  --function-name $LAMBDA_FUNCTION_NAME \
  --image-uri $ECR_URI:latest \
  --region $AWS_REGION \
  --query 'Configuration.[FunctionName,LastModified,State]' \
  --output table

STEP_DURATION=$(($(date +%s) - STEP_START))
log_complete $STEP_DURATION

# Step 6: Wait for update
log_step "6" "Waiting for Lambda update to complete"
STEP_START=$(date +%s)

echo -e "${YELLOW}Waiting for function to be ready (usually 30-60 seconds)...${NC}"
aws lambda wait function-updated \
  --function-name $LAMBDA_FUNCTION_NAME \
  --region $AWS_REGION

STEP_DURATION=$(($(date +%s) - STEP_START))
log_complete $STEP_DURATION

# Final summary
TOTAL_DURATION=$(($(date +%s) - SCRIPT_START))
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Lambda function updated successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Total deployment time: ${TOTAL_DURATION}s ($(($TOTAL_DURATION / 60))m $(($TOTAL_DURATION % 60))s)${NC}"
echo ""
echo -e "${YELLOW}Test with:${NC} ./test_lambda.sh generated_blueprint.png"
echo ""
