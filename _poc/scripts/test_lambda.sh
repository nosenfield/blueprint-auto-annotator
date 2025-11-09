#!/bin/bash
# Test YOLO Lambda Function
# Sends a test image to the deployed Lambda function

set -e

# Configuration
LAMBDA_FUNCTION_NAME="yolo-room-detection"
AWS_REGION="${AWS_REGION:-us-east-1}"  # Allow override via environment variable
TEST_IMAGE="${1:-generated_blueprint.png}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Testing YOLO Lambda Function${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if test image exists
if [ ! -f "$TEST_IMAGE" ]; then
    echo -e "${YELLOW}Error: Test image not found: $TEST_IMAGE${NC}"
    echo "Usage: ./test_lambda.sh [image_path]"
    echo "Example: ./test_lambda.sh generated_blueprint.png"
    exit 1
fi

echo "Test image: $TEST_IMAGE"
echo "Function: $LAMBDA_FUNCTION_NAME"
echo ""

# Encode image to base64 and create JSON payload using Python (handles all edge cases)
echo -e "${YELLOW}Encoding image to base64 and creating JSON payload...${NC}"
python3 << PYEOF
import json
import base64
import sys

try:
    # Read image file
    with open("$TEST_IMAGE", "rb") as f:
        image_data = f.read()
    
    # Encode to base64
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # Create payload
    payload = {
        "image": image_base64
    }
    
    # Write JSON to file in binary mode to avoid encoding issues
    with open("/tmp/lambda_payload.json", "wb") as f:
        json_str = json.dumps(payload)
        f.write(json_str.encode('utf-8'))
    
    # Print size info to stderr
    print(f"  ✓ Image encoded ({len(image_base64)} characters)", file=sys.stderr)
    print(f"  ✓ Payload created", file=sys.stderr)
    
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to encode image or create JSON payload${NC}"
    exit 1
fi
echo ""
echo -e "${YELLOW}Invoking Lambda function...${NC}"
echo "  This may take 10-15 seconds on cold start..."
echo ""

# Invoke Lambda using Python boto3 to avoid AWS CLI encoding issues
START_TIME=$(date +%s)

python3 << PYEOF
import json
import boto3
import sys

try:
    # Read the payload
    with open("/tmp/lambda_payload.json", "rb") as f:
        payload_data = f.read()
    
    # Parse JSON to ensure it's valid
    payload = json.loads(payload_data.decode('utf-8'))
    
    # Create Lambda client
    lambda_client = boto3.client('lambda', region_name='$AWS_REGION')
    
    # Invoke Lambda
    response = lambda_client.invoke(
        FunctionName='$LAMBDA_FUNCTION_NAME',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    # Read response
    response_payload = response['Payload'].read()
    
    # Write response to file
    with open("/tmp/lambda_response.json", "wb") as f:
        f.write(response_payload)
    
    print("  ✓ Lambda invoked successfully", file=sys.stderr)
    
except Exception as e:
    print(f"Error invoking Lambda: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to invoke Lambda function${NC}"
    exit 1
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}Response received in ${DURATION}s${NC}"
echo ""

# Parse and display results
echo -e "${YELLOW}Results:${NC}"
cat /tmp/lambda_response.json | python3 -m json.tool

# Extract key metrics
echo ""
echo -e "${YELLOW}Summary:${NC}"
SUCCESS=$(cat /tmp/lambda_response.json | python3 -c "import sys, json; data=json.load(sys.stdin); body=json.loads(data.get('body', '{}')); print(body.get('success', False))")
ROOMS=$(cat /tmp/lambda_response.json | python3 -c "import sys, json; data=json.load(sys.stdin); body=json.loads(data.get('body', '{}')); print(body.get('total_rooms_detected', 0))" 2>/dev/null || echo "0")
INFERENCE_TIME=$(cat /tmp/lambda_response.json | python3 -c "import sys, json; data=json.load(sys.stdin); body=json.loads(data.get('body', '{}')); print(body.get('inference_time', 'N/A'))" 2>/dev/null || echo "N/A")

echo "  Success: $SUCCESS"
echo "  Rooms detected: $ROOMS"
echo "  Inference time: ${INFERENCE_TIME}s"
echo "  Total time (including cold start): ${DURATION}s"
echo ""

# Cost estimate (using Python for cross-platform compatibility)
echo -e "${YELLOW}Cost estimate:${NC}"
GB_SECONDS=$(python3 -c "print($DURATION * 3.008)")
COST=$(python3 -c "print($GB_SECONDS * 0.0000166667)")
echo "  GB-seconds: $GB_SECONDS"
echo "  Estimated cost: \$$(python3 -c "print(f'{${COST}:.6f}')")"
echo ""

# Save results
RESULTS_FILE="lambda_test_results_$(date +%Y%m%d_%H%M%S).json"
cp /tmp/lambda_response.json "$RESULTS_FILE"
echo "  Full results saved to: $RESULTS_FILE"
echo ""

# Cleanup
rm /tmp/lambda_payload.json
rm /tmp/lambda_response.json

echo -e "${GREEN}Test complete!${NC}"
echo ""
