#!/bin/bash
# Process blueprint image through Lambda and visualize results
# Accepts a directory as argument, finds blueprint.jpg or blueprint.png, processes it, and saves results

set -e

# Configuration
LAMBDA_FUNCTION_NAME="yolo-room-detection"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if directory argument is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Directory argument required${NC}"
    echo "Usage: $0 <directory>"
    echo "Example: $0 /path/to/directory"
    exit 1
fi

TARGET_DIR="$1"

# Check if directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${RED}Error: Directory not found: $TARGET_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Processing Blueprint Image${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Target directory: $TARGET_DIR${NC}"
echo ""

# Find blueprint image (jpg or png)
BLUEPRINT_IMAGE=""
if [ -f "$TARGET_DIR/blueprint.jpg" ]; then
    BLUEPRINT_IMAGE="$TARGET_DIR/blueprint.jpg"
    echo -e "${GREEN}✓ Found blueprint image: blueprint.jpg${NC}"
elif [ -f "$TARGET_DIR/blueprint.png" ]; then
    BLUEPRINT_IMAGE="$TARGET_DIR/blueprint.png"
    echo -e "${GREEN}✓ Found blueprint image: blueprint.png${NC}"
else
    echo -e "${RED}Error: No blueprint image found (blueprint.jpg or blueprint.png) in $TARGET_DIR${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 1: Encoding image and preparing payload...${NC}"

# Encode image to base64 and create JSON payload
python3 << PYEOF
import json
import base64
import sys

try:
    # Read image file
    with open("$BLUEPRINT_IMAGE", "rb") as f:
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
echo -e "${YELLOW}Step 2: Invoking Lambda function...${NC}"
echo "  This may take 10-15 seconds on cold start..."
echo ""

# Invoke Lambda using Python boto3
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
echo -e "${GREEN}✓ Lambda processing completed in ${DURATION}s${NC}"
echo ""

# Step 3: Extract confidence threshold and save results
echo -e "${YELLOW}Step 3: Extracting confidence threshold and saving results...${NC}"

# Extract confidence threshold from the response
CONFIDENCE_THRESHOLD=$(cat /tmp/lambda_response.json | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    body = json.loads(data.get('body', '{}'))
    threshold = body.get('confidence_threshold', 0.5)
    # Format threshold with 2 decimal places
    print(f'{threshold:.2f}')
except:
    print('0.50')
" 2>/dev/null || echo "0.50")

# Replace dots with underscores for filename compatibility
# Format: 0.05 -> 0_05, 0.5 -> 0_50
THRESHOLD_FILENAME=$(echo "$CONFIDENCE_THRESHOLD" | sed 's/\./_/g')

# Save results with threshold in filename
RESULTS_JSON="$TARGET_DIR/blueprint_processed_${THRESHOLD_FILENAME}.json"
cp /tmp/lambda_response.json "$RESULTS_JSON"
echo -e "${GREEN}✓ Results saved to: $RESULTS_JSON${NC}"
echo -e "${CYAN}  Confidence threshold: ${CONFIDENCE_THRESHOLD}${NC}"
echo ""

# Step 4: Run visualizer
echo -e "${YELLOW}Step 4: Creating visualization...${NC}"

# Determine output extension based on input and include threshold
if [[ "$BLUEPRINT_IMAGE" == *.jpg ]]; then
    OUTPUT_IMAGE="$TARGET_DIR/blueprint_processed_${THRESHOLD_FILENAME}.jpg"
else
    OUTPUT_IMAGE="$TARGET_DIR/blueprint_processed_${THRESHOLD_FILENAME}.png"
fi

# Get the script directory to find visualize_lambda_results.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VISUALIZER_SCRIPT="$SCRIPT_DIR/visualize_lambda_results.py"

if [ ! -f "$VISUALIZER_SCRIPT" ]; then
    echo -e "${RED}Error: Visualizer script not found: $VISUALIZER_SCRIPT${NC}"
    exit 1
fi

# Run the visualizer
python3 "$VISUALIZER_SCRIPT" \
    --image "$BLUEPRINT_IMAGE" \
    --results "$RESULTS_JSON" \
    --output "$OUTPUT_IMAGE"

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to create visualization${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Visualization saved to: $OUTPUT_IMAGE${NC}"
echo ""

# Extract and display summary
echo -e "${YELLOW}Summary:${NC}"
SUCCESS=$(cat "$RESULTS_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); body=json.loads(data.get('body', '{}')); print(body.get('success', False))" 2>/dev/null || echo "False")
ROOMS=$(cat "$RESULTS_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); body=json.loads(data.get('body', '{}')); print(body.get('total_rooms_detected', 0))" 2>/dev/null || echo "0")
INFERENCE_TIME=$(cat "$RESULTS_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); body=json.loads(data.get('body', '{}')); print(body.get('inference_time', 'N/A'))" 2>/dev/null || echo "N/A")

echo "  Success: $SUCCESS"
echo "  Rooms detected: $ROOMS"
echo "  Inference time: ${INFERENCE_TIME}s"
echo "  Total processing time: ${DURATION}s"
echo ""

# Cleanup
rm -f /tmp/lambda_payload.json
rm -f /tmp/lambda_response.json

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Processing complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Output files:${NC}"
echo "  Results JSON: $RESULTS_JSON"
echo "  Visualization: $OUTPUT_IMAGE"
echo ""

