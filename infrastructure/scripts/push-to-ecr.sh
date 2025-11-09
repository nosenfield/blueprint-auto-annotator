#!/bin/bash
set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-YOUR_ACCOUNT_ID}"  # Replace with your account ID
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "🚀 Pushing Docker images to ECR..."
echo "Registry: ${ECR_REGISTRY}"
echo ""

# Login to ECR
echo "📝 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Build and push room detection
echo ""
echo "🔨 Building room-detection image..."
cd "$(dirname "$0")/../../backend/lambda-room-detection"
docker build -t room-detection:latest .
docker tag room-detection:latest ${ECR_REGISTRY}/room-detection:latest
echo "📤 Pushing room-detection to ECR..."
docker push ${ECR_REGISTRY}/room-detection:latest

# Build and push wall detection
echo ""
echo "🔨 Building wall-detection image..."
cd ../lambda-wall-detection
docker build -t wall-detection:latest .
docker tag wall-detection:latest ${ECR_REGISTRY}/wall-detection:latest
echo "📤 Pushing wall-detection to ECR..."
docker push ${ECR_REGISTRY}/wall-detection:latest

echo ""
echo "✅ Images pushed to ECR successfully!"
echo ""
echo "Room Detection: ${ECR_REGISTRY}/room-detection:latest"
echo "Wall Detection: ${ECR_REGISTRY}/wall-detection:latest"
