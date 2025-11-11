#!/bin/bash

# Lambda Auto-Warmup Script
# Creates EventBridge rules to invoke Lambda functions every 5 minutes to prevent cold starts

set -e

REGION="us-east-1"
ACCOUNT_ID="971422717446"

# Lambda functions to keep warm
FUNCTIONS=("wall-detection-v1" "room-detection-v2")

echo "Setting up automated Lambda warmup for: ${FUNCTIONS[@]}"

for FUNCTION_NAME in "${FUNCTIONS[@]}"; do
    echo ""
    echo "=== Configuring warmup for $FUNCTION_NAME ==="

    RULE_NAME="warmup-${FUNCTION_NAME}"
    LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"

    # Create EventBridge rule (5 minute interval)
    echo "Creating EventBridge rule: $RULE_NAME"
    aws events put-rule \
        --name "$RULE_NAME" \
        --schedule-expression "rate(5 minutes)" \
        --state ENABLED \
        --description "Warmup rule for $FUNCTION_NAME to prevent cold starts" \
        --region "$REGION" > /dev/null

    RULE_ARN=$(aws events describe-rule --name "$RULE_NAME" --region "$REGION" --query 'Arn' --output text)
    echo "Rule ARN: $RULE_ARN"

    # Create targets JSON file
    cat > /tmp/targets.json << TARGETS_EOF
[
  {
    "Id": "1",
    "Arn": "${LAMBDA_ARN}",
    "Input": "{\"warmup\": true}"
  }
]
TARGETS_EOF

    # Add Lambda as target with warmup event payload
    echo "Adding Lambda as target"
    aws events put-targets \
        --rule "$RULE_NAME" \
        --targets file:///tmp/targets.json \
        --region "$REGION" > /dev/null

    # Grant EventBridge permission to invoke Lambda
    echo "Granting EventBridge permission to invoke Lambda"
    aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id "AllowEventBridge-${RULE_NAME}" \
        --action 'lambda:InvokeFunction' \
        --principal events.amazonaws.com \
        --source-arn "$RULE_ARN" \
        --region "$REGION" \
        > /dev/null 2>&1 || echo "  (Permission already exists)"

    echo "✓ Warmup configured for $FUNCTION_NAME"
done

# Cleanup
rm -f /tmp/targets.json

echo ""
echo "=== Lambda Auto-Warmup Setup Complete ==="
echo ""
echo "✓ All functions will be invoked every 5 minutes to stay warm"
echo "✓ Cost estimate: ~$0.05-0.10/month per Lambda (minimal)"
echo ""
echo "Verify setup:"
echo "  aws events list-rules --name-prefix warmup- --region $REGION"
echo ""
echo "To disable warmup:"
for FUNCTION_NAME in "${FUNCTIONS[@]}"; do
    echo "  aws events disable-rule --name warmup-${FUNCTION_NAME} --region $REGION"
done
echo ""
echo "To delete warmup rules:"
for FUNCTION_NAME in "${FUNCTIONS[@]}"; do
    echo "  aws events remove-targets --rule warmup-${FUNCTION_NAME} --ids 1 --region $REGION && aws events delete-rule --name warmup-${FUNCTION_NAME} --region $REGION"
done
echo ""
