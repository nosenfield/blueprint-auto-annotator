#!/bin/bash
# Rebuild and push Docker images with Docker V2 manifest (Lambda-compatible)
# Modern Docker buildx creates OCI manifests which Lambda doesn't support

set -e

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1

echo "Building wall-detection-v1 with Lambda-compatible manifest..."
cd /Users/nosenfield/Desktop/GauntletAI/Week-4-Innergy/room-reader/backend

# Build with --provenance=false to prevent multi-platform manifest
docker build --platform linux/amd64 --provenance=false -t wall-detection-v1:latest -f lambda-wall-detection-v1/Dockerfile .

# Tag and push
docker tag wall-detection-v1:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/wall-detection-v1:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/wall-detection-v1:latest

echo "Updating Lambda function..."
aws lambda update-function-code \
  --function-name wall-detection-v1 \
  --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/wall-detection-v1:latest \
  --region $AWS_REGION

aws lambda wait function-updated --function-name wall-detection-v1 --region $AWS_REGION

echo "Testing Lambda..."
aws lambda invoke \
  --function-name wall-detection-v1 \
  --payload '{"httpMethod":"GET","path":"/"}' \
  --region $AWS_REGION \
  /tmp/test-response.json

cat /tmp/test-response.json | jq .

echo "Done!"
