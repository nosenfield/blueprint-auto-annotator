#!/bin/bash
# Test Room Model Lambda Function

set -e

LAMBDA_FUNCTION_NAME="room-detection-v2"
AWS_REGION="${AWS_REGION:-us-east-1}"
IMAGE_FILE="${1:-test_image.png}"

if [ ! -f "$IMAGE_FILE" ]; then
    echo "Error: Image file not found: $IMAGE_FILE"
    echo "Usage: ./test_lambda.sh <image.png>"
    exit 1
fi

# Extract directory and filename from image path
IMAGE_DIR=$(dirname "$IMAGE_FILE")
IMAGE_BASENAME=$(basename "$IMAGE_FILE" | sed 's/\.[^.]*$//')
OUTPUT_DIR="$IMAGE_DIR"
RESULTS_FILE="$OUTPUT_DIR/${IMAGE_BASENAME}_lambda_results.json"

echo "=========================================="
echo "Testing Room Model Lambda Function"
echo "=========================================="
echo ""
echo "Function: $LAMBDA_FUNCTION_NAME"
echo "Image: $IMAGE_FILE"
echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Encode image to base64 and create JSON payload using Python (handles all edge cases)
echo "Encoding image to base64 and creating JSON payload..."
python3 << PYEOF
import json
import base64
import sys

try:
    # Read image file
    with open("$IMAGE_FILE", "rb") as f:
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
    
    print(f"  ✓ Image encoded ({len(image_base64)} characters)")
    print(f"  ✓ Payload created")
    
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "Error: Failed to encode image or create JSON payload"
    exit 1
fi

echo ""
echo "Invoking Lambda function..."
echo "  (This may take 10-15 seconds on cold start)"
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
    
    # Write response to file in the same directory as the input image
    output_path = "$RESULTS_FILE"
    with open(output_path, "wb") as f:
        f.write(response_payload)
    
    print(f"  ✓ Lambda invoked successfully")
    print(f"  ✓ Response saved to: {output_path}")
    
except Exception as e:
    print(f"Error invoking Lambda: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "Error: Failed to invoke Lambda function"
    exit 1
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "Response received in ${DURATION}s"
echo ""

# Parse and display results
echo "Results:"
cat "$RESULTS_FILE" | python3 -m json.tool

echo ""
echo "Response saved to: $RESULTS_FILE"

# Create visualization
echo ""
echo "Creating visualization..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VISUALIZER_SCRIPT="$SCRIPT_DIR/visualize_results.py"

if [ -f "$VISUALIZER_SCRIPT" ]; then
    # Extract base name and extension for output image
    IMAGE_EXT=$(echo "$IMAGE_FILE" | sed 's/.*\.//')
    VISUALIZATION_FILE="$OUTPUT_DIR/${IMAGE_BASENAME}_processed.${IMAGE_EXT}"
    
    python3 "$VISUALIZER_SCRIPT" \
        --image "$IMAGE_FILE" \
        --results "$RESULTS_FILE" \
        --output "$VISUALIZATION_FILE"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✓ Visualization saved to: $VISUALIZATION_FILE"
    else
        echo "⚠ Warning: Visualization failed, but results JSON was saved"
    fi
else
    echo "⚠ Warning: Visualization script not found at $VISUALIZER_SCRIPT"
fi

echo ""
echo "Files saved:"
echo "  Results JSON: $RESULTS_FILE"
if [ -f "$VISUALIZATION_FILE" ]; then
    echo "  Visualization: $VISUALIZATION_FILE"
fi

# Cleanup
rm /tmp/lambda_payload.json

