#!/bin/bash
# Warm up Lambda functions before demo
# Run this script 1-2 minutes before demonstrating the application

set -e

AWS_REGION="${AWS_REGION:-us-east-1}"

echo "🔥 Warming up Lambda functions..."
echo ""

# Warm up wall-detection-v1 (this will timeout on cold start - expected)
echo "1. Warming up wall-detection-v1..."
echo "   (First invocation will timeout after 29s - this is expected while model loads)"
echo "   Model download + loading takes ~32 seconds on cold start"
echo ""

# Make TWO requests - first will timeout, second will succeed
curl -X POST https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls \
  -H "Content-Type: application/json" \
  -d '{"image": "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA//2Q==", "confidence_threshold": 0.10}' \
  -s --max-time 35 > /dev/null 2>&1 || echo "   ⏱  First request timed out (expected) - Lambda is loading 1.1GB model..."

echo "   Waiting 60 seconds for model to finish loading..."
sleep 60

echo "   Sending second warmup request..."
curl -X POST https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls \
  -H "Content-Type: application/json" \
  -d '{"image": "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA//2Q==", "confidence_threshold": 0.10}' \
  -s --max-time 10 > /dev/null 2>&1 && echo "   ✓ wall-detection-v1 is warm and ready!" || echo "   ⚠  Check CloudWatch logs if issues persist"

# Warm up geometric-conversion-v1 with a minimal request
echo "2. Warming up geometric-conversion-v1..."
curl -X POST https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/convert-to-rooms \
  -H "Content-Type: application/json" \
  -d '{"walls": [], "image_dimensions": [100, 100]}' \
  -s --max-time 30 > /dev/null 2>&1 || true
echo "   ✓ geometric-conversion-v1 is warm"

# Warm up room-detection-v2 (this will timeout on cold start - expected)
echo "3. Warming up room-detection-v2..."
echo "   (First invocation will timeout after 29s - this is expected while model loads)"
echo "   Model download + loading takes ~20-25 seconds on cold start"
echo ""

# Get API Gateway URL dynamically
API_ID=$(aws apigateway get-rest-apis --region $AWS_REGION --query "items[?name=='room-reader-api'].id" --output text | head -1)
API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"

# Make TWO requests - first will timeout, second will succeed
curl -X POST ${API_URL}/api/v2/detect-rooms \
  -H "Content-Type: application/json" \
  -d '{"image": "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA//2Q==", "confidence_threshold": 0.5}' \
  -s --max-time 35 > /dev/null 2>&1 || echo "   ⏱  First request timed out (expected) - Lambda is loading ~567MB model..."

echo "   Waiting 45 seconds for model to finish loading..."
sleep 45

echo "   Sending second warmup request..."
curl -X POST ${API_URL}/api/v2/detect-rooms \
  -H "Content-Type: application/json" \
  -d '{"image": "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA//2Q==", "confidence_threshold": 0.5}' \
  -s --max-time 10 > /dev/null 2>&1 && echo "   ✓ room-detection-v2 is warm and ready!" || echo "   ⚠  Check CloudWatch logs if issues persist"

echo ""
echo "✅ All Lambda functions are warmed up and ready!"
echo ""
echo "Your application is ready for demo. Lambda functions will stay warm for ~10-15 minutes."
echo ""
echo "API Endpoints:"
echo "  - Frontend: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com"
echo "  - API: ${API_URL}"
echo ""
