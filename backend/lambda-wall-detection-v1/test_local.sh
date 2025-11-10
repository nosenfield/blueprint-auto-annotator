#!/bin/bash
# Test Wall Model Locally (FastAPI)

set -e

API_URL="${API_URL:-http://localhost:8000}"
IMAGE_FILE="${1:-test_image.png}"
CONFIDENCE_THRESHOLD="${2:-0.10}"

if [ ! -f "$IMAGE_FILE" ]; then
    echo "Error: Image file not found: $IMAGE_FILE"
    echo "Usage: ./test_local.sh <image.png> [confidence_threshold]"
    echo "Example: ./test_local.sh blueprint.png 0.10"
    exit 1
fi

# Extract directory and filename from image path
IMAGE_DIR=$(dirname "$IMAGE_FILE")
IMAGE_BASENAME=$(basename "$IMAGE_FILE" | sed 's/\.[^.]*$//')
OUTPUT_DIR="$IMAGE_DIR"
RESULTS_FILE="$OUTPUT_DIR/${IMAGE_BASENAME}_wall_results.json"

echo "=========================================="
echo "Testing Wall Model Locally"
echo "=========================================="
echo ""
echo "API URL: $API_URL"
echo "Image: $IMAGE_FILE"
echo "Confidence Threshold: $CONFIDENCE_THRESHOLD"
echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Encode image to base64 and create JSON payload using Python
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
        "image": image_base64,
        "confidence_threshold": float("$CONFIDENCE_THRESHOLD")
    }
    
    # Write JSON to file
    with open("/tmp/wall_payload.json", "wb") as f:
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
echo "Sending request to FastAPI server..."
echo "  (Make sure the server is running: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000)"
echo ""

# Send request using Python requests
START_TIME=$(date +%s)

python3 << PYEOF
import json
import requests
import sys

try:
    # Read the payload
    with open("/tmp/wall_payload.json", "rb") as f:
        payload_data = f.read()

    # Parse JSON to ensure it's valid
    payload = json.loads(payload_data.decode('utf-8'))

    # Send POST request
    response = requests.post(
        "$API_URL/api/detect-walls",
        json=payload,
        timeout=60
    )

    # Check response status
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}", file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
        sys.exit(1)

    # Write response to file
    output_path = "$RESULTS_FILE"
    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"  ✓ Request successful")
    print(f"  ✓ Response saved to: {output_path}")

except requests.exceptions.ConnectionError:
    print(f"Error: Could not connect to $API_URL", file=sys.stderr)
    print(f"Make sure FastAPI server is running:", file=sys.stderr)
    print(f"  cd backend/lambda-wall-detection-v1", file=sys.stderr)
    print(f"  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "Error: Failed to send request"
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

# Cleanup
rm /tmp/wall_payload.json

