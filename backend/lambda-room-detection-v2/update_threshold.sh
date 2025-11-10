#!/bin/bash
# Update confidence threshold for Room Model Lambda function
# Usage: ./update_threshold.sh <threshold_value>
# Example: ./update_threshold.sh 0.5

set -e

# Configuration
LAMBDA_FUNCTION_NAME="room-detection-v2"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if threshold argument is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Confidence threshold value required${NC}"
    echo ""
    echo "Usage: $0 <threshold_value>"
    echo "Example: $0 0.5"
    echo "Example: $0 0.3"
    echo ""
    echo "Threshold should be a float between 0.0 and 1.0"
    exit 1
fi

THRESHOLD="$1"

# Validate threshold is a valid float
if ! python3 -c "float('$THRESHOLD')" 2>/dev/null; then
    echo -e "${RED}Error: Invalid threshold value: $THRESHOLD${NC}"
    echo "Threshold must be a valid float (e.g., 0.5, 0.3, 0.7)"
    exit 1
fi

# Validate threshold is between 0 and 1
if ! python3 << PYEOF
threshold = float('$THRESHOLD')
if not (0.0 <= threshold <= 1.0):
    print("Error: Threshold must be between 0.0 and 1.0")
    exit(1)
PYEOF
then
    echo -e "${RED}Error: Threshold must be between 0.0 and 1.0${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Updating Confidence Threshold${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Function: ${LAMBDA_FUNCTION_NAME}${NC}"
echo -e "${CYAN}Region: ${AWS_REGION}${NC}"
echo -e "${CYAN}New threshold: ${THRESHOLD}${NC}"
echo ""

# Get current environment variables
echo -e "${YELLOW}Step 1: Retrieving current configuration...${NC}"
CURRENT_ENV=$(aws lambda get-function-configuration \
    --function-name $LAMBDA_FUNCTION_NAME \
    --region $AWS_REGION \
    --query 'Environment.Variables' \
    --output json 2>/dev/null || echo "{}")

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to retrieve current Lambda configuration${NC}"
    echo "Make sure the Lambda function exists and you have proper AWS credentials."
    exit 1
fi

# Update environment variables, preserving existing ones
echo -e "${YELLOW}Step 2: Updating confidence threshold...${NC}"

# Use Python to merge current env vars with new threshold and create config file
TEMP_ENV_FILE=$(mktemp /tmp/lambda-env-XXXXXX.json)

python3 << PYEOF
import json
import sys

try:
    # Parse current environment variables
    current_env = json.loads('''$CURRENT_ENV''')
    
    # Update confidence threshold
    current_env['CONFIDENCE_THRESHOLD'] = '$THRESHOLD'
    
    # Convert all values to strings (AWS Lambda requires string values)
    env_vars = {k: str(v) for k, v in current_env.items()}
    
    # Create environment configuration
    config = {
        "Variables": env_vars
    }
    
    # Write to temporary file
    with open('$TEMP_ENV_FILE', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("  ✓ Configuration file created", file=sys.stderr)
    
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to create configuration file${NC}"
    rm -f "$TEMP_ENV_FILE"
    exit 1
fi

# Apply configuration using file:// syntax
echo -e "${YELLOW}  Applying configuration...${NC}"
aws lambda update-function-configuration \
    --function-name $LAMBDA_FUNCTION_NAME \
    --region $AWS_REGION \
    --environment file://$TEMP_ENV_FILE \
    > /tmp/lambda_update_response.json 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to update Lambda configuration${NC}"
    cat /tmp/lambda_update_response.json
    rm -f "$TEMP_ENV_FILE" /tmp/lambda_update_response.json
    exit 1
fi

echo -e "${GREEN}  ✓ Configuration updated successfully${NC}"

# Parse and display updated config
UPDATED_THRESHOLD=$(cat /tmp/lambda_update_response.json | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    env_vars = data.get('Environment', {}).get('Variables', {})
    print(env_vars.get('CONFIDENCE_THRESHOLD', 'N/A'))
except:
    print('N/A')
" 2>/dev/null || echo "N/A")

echo -e "${GREEN}  ✓ Confidence threshold: ${UPDATED_THRESHOLD}${NC}"

# Cleanup
rm -f "$TEMP_ENV_FILE" /tmp/lambda_update_response.json

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Threshold updated successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Summary:${NC}"
echo "  Function: $LAMBDA_FUNCTION_NAME"
echo "  New threshold: $THRESHOLD"
echo ""
echo -e "${YELLOW}Note:${NC} Changes take effect on the next Lambda invocation."
echo "  Test with: ./test_lambda.sh <blueprint.png>"
echo ""


