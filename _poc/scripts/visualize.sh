#!/bin/bash
# Quick visualization script for Lambda detection results

IMAGE="${1:-../poc/generated_blueprint.png}"
RESULTS="${2:-$(ls -t lambda_test_results_*.json 2>/dev/null | head -1)}"

if [ -z "$RESULTS" ]; then
    echo "Error: No Lambda test results found. Run test_lambda.sh first."
    exit 1
fi

echo "Visualizing Lambda detection results..."
echo "  Image: $IMAGE"
echo "  Results: $RESULTS"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/visualize_lambda_results.py" --image "$IMAGE" --results "$RESULTS"

