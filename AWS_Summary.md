# AWS Lambda Deployment Summary

## Overview
This document summarizes the AWS deployment challenges encountered and solutions implemented for the Room Detection application Lambda functions.

## Application Architecture
- **Frontend**: React app hosted on S3 (http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com)
- **API Gateway**: REST API endpoint (https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod)
- **Lambda Functions**:
  - `wall-detection-v1`: YOLO-based wall detection (1.1GB model)
  - `geometric-conversion-v1`: Wall-to-room polygon conversion

## Key Challenges & Solutions

### 1. Lambda Ephemeral Storage Limitation
**Problem**: Default Lambda ephemeral storage (512MB) was insufficient for the 1.1GB compressed model file.

**Error**: `[Errno 28] No space left on device`

**Solution**: Increased ephemeral storage in multiple iterations:
- Initially: 512MB (default)
- First attempt: 2GB (failed during extraction)
- Final: 5GB (successful)

```bash
aws lambda update-function-configuration \
  --function-name wall-detection-v1 \
  --region us-east-1 \
  --ephemeral-storage '{"Size": 5120}'
```

### 2. Model File Naming Mismatch
**Problem**: Code expected `model.pt` but SageMaker output archive contained `final_model.pt`.

**Error**: "model.pt not found in tar.gz archive"

**Solution**:
1. Downloaded and inspected the 1.1GB model archive locally
2. Discovered actual filename: `final_model.pt`
3. Updated `detection.py` line 65:
```python
# Changed from:
model_path = "/tmp/model.pt"
# To:
model_path = "/tmp/final_model.pt"
```

### 3. API Gateway Timeout vs Lambda Cold Start
**Problem**: Lambda cold start (~32 seconds) exceeds API Gateway hard limit (29 seconds).

**Cold Start Breakdown**:
- Download 1.1GB model from S3: ~15 seconds
- Extract tar.gz: ~5 seconds
- Load YOLO model into memory: ~12 seconds
- **Total**: ~32 seconds

**Limitations**:
- API Gateway maximum timeout: 29 seconds (cannot be increased)
- First request will always timeout on cold start

**Solution**: Created warmup script that:
1. Makes initial request (triggers model download, will timeout)
2. Waits 60 seconds for model to finish loading
3. Makes second request (succeeds with warm Lambda)

Script: `infrastructure/scripts/warmup-lambdas.sh`

**For Production**: Would use:
- Provisioned concurrency (keeps Lambda warm)
- CloudFront in front of API Gateway (longer timeout support)
- Pre-baked Docker image with model included

### 4. Duplicate CORS Headers
**Problem**: Browser error: "The 'Access-Control-Allow-Origin' header contains multiple values '*, *'"

**Root Cause**: CORS headers being added in three places:
1. FastAPI CORSMiddleware (lines 35-41 in main.py)
2. Lambda handler function (lines 176-195 in main.py)
3. API Gateway configuration

**Solution**: Removed manual CORS header addition from Lambda handler, relying solely on FastAPI's CORSMiddleware:

Before:
```python
def handler(event, context):
    # CORS headers to add to all responses
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        ...
    }
    response['headers'].update(cors_headers)  # Duplicate!
```

After:
```python
def handler(event, context):
    # FastAPI CORSMiddleware handles CORS automatically
    response = mangum_handler(event, context)
    return response
```

Applied fix to both:
- `lambda-wall-detection-v1/app/main.py`
- `lambda-geometric-conversion-v1/app/main.py`

### 5. Frontend API Endpoint Mismatch
**Problem**: Frontend `.env.production` had outdated API Gateway URL.

**Error**: CORS error when trying to access old endpoint `0zem13mmcb.execute-api.us-east-1.amazonaws.com`

**Solution**: Updated `frontend/.env.production`:
```bash
# Changed from:
VITE_API_URL=https://0zem13mmcb.execute-api.us-east-1.amazonaws.com/prod
# To:
VITE_API_URL=https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod
```

Redeployed frontend to S3.

### 6. Docker Multi-Platform Manifest Issue
**Problem**: AWS Lambda rejecting Docker image with error: "The image manifest, config or layer media type... is not supported"

**Root Cause**: Docker buildx creating multi-platform manifest (linux/amd64 + linux/arm64)

**Status**: Currently being investigated

**Attempted Solutions**:
- Legacy format build script (in progress)
- Single-platform build specification

## Model Details

### Wall Detection Model (November 7, 2025)
- **Location**: `s3://sagemaker-us-east-1-971422717446/room-detection-yolo-1762559721/output/model.tar.gz`
- **Size**: 1.1GB compressed
- **Architecture**: YOLOv8 for wall detection
- **Filename in archive**: `final_model.pt`

### Configuration
```python
MODEL_S3_BUCKET = 'sagemaker-us-east-1-971422717446'
MODEL_S3_KEY = 'room-detection-yolo-1762559721/output/model.tar.gz'
```

## Lambda Configuration

### wall-detection-v1
```json
{
  "FunctionName": "wall-detection-v1",
  "Runtime": "python3.11",
  "MemorySize": 3008,
  "Timeout": 120,
  "EphemeralStorage": {"Size": 5120},
  "PackageType": "Image",
  "Architectures": ["arm64"]
}
```

### Deployment Workflow
1. Build Docker image with dependencies
2. Push to ECR: `971422717446.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1`
3. Update Lambda function code
4. Wait for function to be active
5. Run warmup script before demo

## Testing Workflow

### Warmup Sequence (Before Demo)
```bash
./infrastructure/scripts/warmup-lambdas.sh
```

This takes ~90 seconds and ensures Lambda is warm for the demo.

### Expected Behavior
- **Cold Start**: First request times out after 29 seconds (expected)
- **Warm Lambda**: Subsequent requests complete in <10 seconds
- **Lambda stays warm**: ~10-15 minutes of inactivity

## CloudWatch Logs - Successful Model Load
```
Custom model not found at /app/models/best_wall_model.pt
Downloading trained model from S3...
  S3 Bucket: sagemaker-us-east-1-971422717446
  S3 Key: room-detection-yolo-1762559721/output/model.tar.gz
  Downloading from s3://sagemaker-us-east-1-971422717446/room-detection-yolo-1762559721/output/model.tar.gz
  ✓ Downloaded to /tmp/model.tar.gz
  Extracting model...
  ✓ Model extracted to /tmp/final_model.pt
Loading wall detection model from /tmp/final_model.pt
Model loaded successfully
Wall detector ready
```

## Pending Issues

### Docker Manifest Format
Current deployment is failing due to multi-platform Docker manifest issue. Working on solution to force single-platform build compatible with AWS Lambda.

## Recommendations for Production

1. **Use Provisioned Concurrency**: Keep Lambda warm to eliminate cold start issues
2. **Bake Model into Docker Image**: Avoid S3 download on cold start
3. **CloudFront + API Gateway**: Support longer timeouts for cold starts
4. **Monitoring**: Set up CloudWatch alarms for:
   - Lambda errors
   - Timeout rate
   - Memory usage
   - Cold start frequency

## Current Status
- ✅ Lambda ephemeral storage configured (5GB)
- ✅ Model path fixed (final_model.pt)
- ✅ Warmup script created
- ✅ CORS headers fixed (removed duplicates)
- ✅ Frontend API endpoint updated
- ⏳ Docker manifest issue being resolved
- ⏳ Full pipeline test pending deployment success

## Next Steps
1. Resolve Docker manifest format issue
2. Complete Lambda deployment
3. Test full pipeline (wall detection → room conversion)
4. Verify CORS headers work correctly
5. Document demo workflow
