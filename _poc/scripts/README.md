# Scripts Directory

This directory contains utility scripts for deployment, testing, processing, and visualization.

## Scripts

### Deployment
- **deploy.sh** - Full deployment script for Lambda function
- **quick_fix.sh** - Quick rebuild and redeploy script

### Testing
- **test_lambda.sh** - Test Lambda function with a blueprint image

### Processing
- **process_blueprint.sh** - Process a blueprint image through Lambda and create visualization
  - Usage: `./process_blueprint.sh <directory>`
  - Finds `blueprint.jpg` or `blueprint.png` in the directory
  - Saves results as `blueprint_processed_<threshold>.json` and `blueprint_processed_<threshold>.png/jpg`

### Visualization
- **visualize_lambda_results.py** - Visualize Lambda detection results on blueprint images
- **visualize.sh** - Quick visualization wrapper script
- **compare_results.py** - Compare detection results

## Usage

All scripts should be run from the project root directory:

```bash
# From project root
./scripts/test_lambda.sh generated_blueprint.png
./scripts/process_blueprint.sh office-floor-plan-1/
./scripts/quick_fix.sh
```

