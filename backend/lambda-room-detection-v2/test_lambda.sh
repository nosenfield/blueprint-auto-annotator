#!/bin/bash
# Test Room Model Lambda Function

set -e

LAMBDA_FUNCTION_NAME="room-detection-v2"
IMAGE_FILE="${1:-test_image.png}"

if [ ! -f "$IMAGE_FILE" ]; then
    echo "Error: Image file not found: $IMAGE_FILE"
    echo "Usage: ./test_lambda.sh <image.png>"
    exit 1
fi

echo "=========================================="
echo "Testing Room Model Lambda Function"
echo "=========================================="
echo ""
echo "Function: $LAMBDA_FUNCTION_NAME"
echo "Image: $IMAGE_FILE"
echo ""

# Convert image to base64
echo "Encoding image to base64..."
IMAGE_BASE64=$(base64 -i "$IMAGE_FILE")

# Create test event
TEST_EVENT=$(cat <<EOF
{
  "image": "$IMAGE_BASE64"
}
EOF
)

# Save to file
echo "$TEST_EVENT" > /tmp/test_event.json

# Invoke Lambda
echo "Invoking Lambda function..."
echo "  (This may take 10-15 seconds on cold start)"
echo ""

RESPONSE=$(aws lambda invoke \
    --function-name $LAMBDA_FUNCTION_NAME \
    --payload file:///tmp/test_event.json \
    --region us-east-1 \
    /tmp/lambda_response.json)

# Check response
if [ $? -eq 0 ]; then
    echo "✓ Lambda invocation successful"
    echo ""
    echo "Response:"
    cat /tmp/lambda_response.json | python3 -m json.tool
    echo ""
    echo "Response saved to: /tmp/lambda_response.json"
else
    echo "✗ Lambda invocation failed"
    exit 1
fi

