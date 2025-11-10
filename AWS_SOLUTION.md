# AWS Lambda Deployment Solution

## Executive Summary

This document details the complete solution for deploying the Room Detection application's computer vision Lambdas to AWS. The deployment faced two critical issues that were successfully resolved:

1. **Docker Multi-Platform Manifest Error** - AWS Lambda rejecting container images
2. **Frontend Integration Error** - OpenCV receiving empty images due to incorrect data access

**Status**: ✅ **FULLY RESOLVED** - All systems operational in production

---

## Problem 1: Docker Image Manifest Compatibility

### The Error
```
The image manifest or layer media type for the source image is not supported
```

### Root Cause Analysis

**Why it happened:**
- Docker Desktop v4.30.0+ automatically creates **provenance attestations** during builds
- These attestations convert single-platform images into **multi-platform image indexes**
- AWS Lambda **does not support** multi-platform container images
- Lambda requires single-platform images with standard Docker v2 manifest format

**Technical Details:**
- Modern `docker buildx` (v0.10+) enables BuildKit by default
- BuildKit adds provenance/SBOM attestations for supply chain security
- These attestations create an "image index" instead of a simple "image"
- ECR shows these as type "image index" rather than "image"
- Lambda's container runtime rejects image indexes

### The Solution

Add `--provenance=false` flag to all Docker build commands:

```bash
docker build \
  --platform linux/amd64 \
  --provenance=false \
  -t wall-detection-v1:latest \
  -f lambda-wall-detection-v1/Dockerfile .
```

**Why this works:**
- `--platform linux/amd64` - Specifies single target platform (required for Lambda)
- `--provenance=false` - Disables attestation generation
- Result: Standard Docker v2 manifest that Lambda accepts

### Files Modified

1. **[infrastructure/scripts/rebuild-and-redeploy-v1.sh](infrastructure/scripts/rebuild-and-redeploy-v1.sh)**
   - Line 35: Added `--provenance=false` to wall-detection-v1 build
   - Line 63: Added `--provenance=false` to geometric-conversion-v1 build

2. **[infrastructure/scripts/rebuild-legacy-format.sh](infrastructure/scripts/rebuild-legacy-format.sh)**
   - Line 14: Replaced `DOCKER_BUILDKIT=0 docker buildx build` with standard `docker build --provenance=false`
   - Modernized approach while maintaining Lambda compatibility

### Alternative Solutions Considered

| Solution | Pros | Cons | Chosen? |
|----------|------|------|---------|
| `--provenance=false` | Clean, modern, explicit | Requires Docker 23.0+ | ✅ Yes |
| `BUILDX_NO_DEFAULT_ATTESTATIONS=1` | Environment variable | Global side effects | ❌ No |
| `DOCKER_BUILDKIT=0` | Disables BuildKit entirely | Loses performance benefits | ❌ No |
| Downgrade Docker Desktop | No code changes | Blocks updates, temporary | ❌ No |

---

## Problem 2: Frontend Integration - Image Dimensions Mismatch

### The Error
```
OpenCV(4.8.1) /io/opencv/modules/imgproc/src/morph.dispatch.cpp:1163:
error: (-215:Assertion failed) !_src.empty() in function 'morphologyEx'
```

### Root Cause Analysis

**The Bug:**
Frontend was sending `image_dimensions: [0, 0]` to the geometric conversion Lambda, causing OpenCV to receive an empty canvas.

**Why it happened:**
```typescript
// INCORRECT - api.ts line 55 (before fix)
const [width, height] = wallResponse.metadata?.image_dimensions || [0, 0];
```

The frontend was looking for `image_dimensions` inside the `metadata` object, but the backend returns it at the top level:

```python
# Backend response structure - lambda-wall-detection-v1/app/main.py:122-128
return WallDetectionResponse(
    success=True,
    walls=walls,
    total_walls=len(walls),
    image_dimensions=(width, height),  # ← TOP LEVEL, not in metadata
    processing_time_ms=total_time
)
```

**The TypeScript Problem:**
The `WallDetectionResponse` interface was missing the `image_dimensions` field entirely, so TypeScript didn't catch this bug.

### The Solution

**Step 1: Fix Data Access** - [frontend/src/services/api.ts:55](frontend/src/services/api.ts#L55)
```typescript
// BEFORE
const [width, height] = wallResponse.metadata?.image_dimensions || [0, 0];

// AFTER
const [width, height] = wallResponse.image_dimensions || [0, 0];
```

**Step 2: Fix TypeScript Interface** - [frontend/src/types/index.ts:47-56](frontend/src/types/index.ts#L47-L56)
```typescript
export interface WallDetectionResponse {
  success: boolean;
  walls: Wall[];
  total_walls: number;
  image_dimensions: [number, number];  // ← ADDED
  processing_time_ms: number;
  model_version?: ModelVersion;        // ← Made optional
  visualization?: string;
  metadata?: Record<string, any>;      // ← Made optional
}
```

### Impact

**Before Fix:**
1. Frontend calls wall detection → gets back `image_dimensions: [640, 480]`
2. Frontend reads `wallResponse.metadata?.image_dimensions` → gets `undefined`
3. Defaults to `[0, 0]`
4. Sends geometric conversion request with `image_dimensions: [0, 0]`
5. Backend creates empty 0×0 canvas
6. OpenCV throws "empty image" assertion error

**After Fix:**
1. Frontend calls wall detection → gets back `image_dimensions: [640, 480]`
2. Frontend reads `wallResponse.image_dimensions` → gets `[640, 480]` ✅
3. Sends geometric conversion request with correct dimensions
4. Backend creates proper canvas and successfully converts walls to rooms

---

## Architecture Overview

### Application Stack

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│  S3 Static Website: room-reader-frontend-971422717446      │
│  http://room-reader-frontend-971422717446.s3-website...    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTPS/CORS
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    API Gateway                              │
│  https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com   │
│  Endpoints:                                                 │
│    POST /prod/api/detect-walls                             │
│    POST /prod/api/convert-to-rooms                         │
└────────┬───────────────────────────┬────────────────────────┘
         │                           │
         │                           │
┌────────▼──────────┐    ┌──────────▼──────────┐
│ wall-detection-v1 │    │ geometric-conversion│
│ Lambda Function   │    │ Lambda Function     │
│                   │    │                     │
│ • YOLOv8 Model   │    │ • OpenCV Morphology│
│ • 1.1GB Model    │    │ • Polygon Extraction│
│ • 5GB Ephemeral  │    │ • Room Detection   │
│ • 120s Timeout   │    │                     │
└───────────────────┘    └─────────────────────┘
```

### Lambda Configuration

#### wall-detection-v1
```json
{
  "FunctionName": "wall-detection-v1",
  "Runtime": "Container (Python 3.11)",
  "MemorySize": 3008,
  "Timeout": 120,
  "EphemeralStorage": {
    "Size": 5120
  },
  "PackageType": "Image",
  "Architectures": ["x86_64"],
  "ImageUri": "971422717446.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1:latest"
}
```

**Key Settings:**
- **5GB Ephemeral Storage** - Required for 1.1GB model.tar.gz extraction
- **3GB Memory** - Needed for YOLO inference
- **120s Timeout** - Accommodates model download + inference on cold start
- **x86_64 Architecture** - Built with `--platform linux/amd64`

#### geometric-conversion-v1
```json
{
  "FunctionName": "geometric-conversion-v1",
  "Runtime": "Container (Python 3.11)",
  "MemorySize": 2048,
  "Timeout": 60,
  "PackageType": "Image",
  "Architectures": ["x86_64"]
}
```

---

## Deployment Workflow

### Complete Deployment Process

```bash
# 1. Build and deploy both Lambdas
./infrastructure/scripts/rebuild-and-redeploy-v1.sh

# 2. Build and deploy frontend
cd frontend
npm run build
aws s3 sync dist/ s3://room-reader-frontend-971422717446 --delete --region us-east-1

# 3. Warm up Lambdas (optional but recommended)
./infrastructure/scripts/warmup-lambdas.sh
```

### Deployment Script Breakdown

**[rebuild-and-redeploy-v1.sh](infrastructure/scripts/rebuild-and-redeploy-v1.sh)** performs:

1. **ECR Login** (lines 27-28)
   ```bash
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com
   ```

2. **Build wall-detection-v1** (line 35)
   ```bash
   docker build --platform linux/amd64 --provenance=false \
     -t wall-detection-v1:latest \
     -f lambda-wall-detection-v1/Dockerfile .
   ```

3. **Push to ECR** (lines 42-43)
   ```bash
   docker tag wall-detection-v1:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1:latest
   docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1:latest
   ```

4. **Update Lambda** (lines 50-58)
   ```bash
   aws lambda update-function-code \
     --function-name wall-detection-v1 \
     --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1:latest \
     --region us-east-1

   aws lambda wait function-updated --function-name wall-detection-v1 --region us-east-1
   ```

5. **Repeat for geometric-conversion-v1** (lines 61-87)

6. **Health Check Tests** (lines 90-124)

---

## Cold Start Optimization

### The Challenge

**Problem:** Lambda cold start (~32s) exceeds API Gateway timeout (29s)

**Cold Start Breakdown:**
- Download 1.1GB model from S3: ~15 seconds
- Extract tar.gz: ~5 seconds
- Load YOLO model into memory: ~12 seconds
- **Total: ~32 seconds** > 29s API Gateway limit

### Current Solution: Warmup Script

**[infrastructure/scripts/warmup-lambdas.sh](infrastructure/scripts/warmup-lambdas.sh)**
```bash
#!/bin/bash
# Warm up Lambdas by triggering model download

echo "Warming up wall-detection-v1..."
curl -X POST https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls \
  -H "Content-Type: application/json" \
  -d '{"image":"","confidence_threshold":0.1}' \
  -w "\nHTTP Status: %{http_code}\n" \
  --max-time 60 || echo "Expected timeout on first request"

echo "Waiting 60s for model to finish loading..."
sleep 60

echo "Testing warm Lambda..."
curl -X POST https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls \
  -H "Content-Type: application/json" \
  -d '{"image":"","confidence_threshold":0.1}' \
  -w "\nHTTP Status: %{http_code}\n"
```

**How it works:**
1. First request triggers model download (will timeout after 29s)
2. Lambda continues downloading in background
3. Wait 60s for completion
4. Second request succeeds with warm Lambda (<10s response)

### Production Recommendations

For production deployment, implement one or more of these strategies:

#### 1. Provisioned Concurrency (Recommended)
```bash
aws lambda put-provisioned-concurrency-config \
  --function-name wall-detection-v1 \
  --provisioned-concurrent-executions 1
```

**Benefits:**
- Keeps Lambda warm 24/7
- Eliminates cold starts
- Predictable performance

**Cost:**
- ~$40/month per concurrent instance
- Worth it for production reliability

#### 2. Bake Model into Docker Image
```dockerfile
# In lambda-wall-detection-v1/Dockerfile
COPY yolov8m.pt /app/models/best_wall_model.pt
```

**Benefits:**
- Eliminates S3 download (saves ~15s)
- Reduces cold start to ~17s (still over 29s but better)
- No runtime dependency on S3

**Tradeoffs:**
- Docker image becomes ~1.1GB larger
- ECR push/pull takes longer
- Model updates require image rebuild

#### 3. CloudFront + Lambda Function URL
```bash
# Create Lambda Function URL (bypasses API Gateway)
aws lambda create-function-url-config \
  --function-name wall-detection-v1 \
  --auth-type NONE \
  --cors '{"AllowOrigins":["*"],"AllowMethods":["POST"],"MaxAge":300}'

# Put CloudFront in front for longer timeout support
```

**Benefits:**
- Function URLs support longer timeouts
- CloudFront adds caching layer
- Better global performance

#### 4. EventBridge Scheduled Warmup
```bash
# Keep Lambda warm with scheduled pings every 10 minutes
aws events put-rule \
  --name warmup-wall-detection \
  --schedule-expression "rate(10 minutes)"
```

---

## Testing & Verification

### Manual Testing

**1. Test wall detection endpoint:**
```bash
curl -X POST https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_encoded_image_here",
    "confidence_threshold": 0.1
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "walls": [
    {
      "id": "wall_001",
      "bounding_box": [440, 177, 451, 279],
      "confidence": 0.8139
    }
  ],
  "total_walls": 34,
  "image_dimensions": [640, 480],
  "processing_time_ms": 8532.5
}
```

**2. Test room conversion endpoint:**
```bash
curl -X POST https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/convert-to-rooms \
  -H "Content-Type: application/json" \
  -d '{
    "walls": [...],
    "image_dimensions": [640, 480],
    "min_room_area": 2000,
    "return_visualization": true
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "rooms": [
    {
      "id": "room_001",
      "polygon_vertices": [[100, 100], [200, 100], ...],
      "area_pixels": 5000,
      "confidence": 0.85
    }
  ],
  "total_rooms": 3,
  "processing_time_ms": 503.35,
  "visualization": "base64_encoded_image"
}
```

### CloudWatch Logs

**Monitor wall-detection-v1:**
```bash
aws logs tail /aws/lambda/wall-detection-v1 --follow
```

**Monitor geometric-conversion-v1:**
```bash
aws logs tail /aws/lambda/geometric-conversion-v1 --follow
```

**Successful model load logs:**
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

---

## CORS Configuration

### Current Setup

Both Lambda functions use FastAPI's `CORSMiddleware`:

```python
# lambda-wall-detection-v1/app/main.py:34-41
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Important:** Manual CORS header addition in Lambda handler was removed to prevent duplicate headers.

### API Gateway CORS

If issues arise, use the CORS fix script:
```bash
./infrastructure/scripts/fix-cors.sh
```

---

## Known Issues & Limitations

### 1. Cold Start Timeout
**Issue:** First request after Lambda goes cold (15+ min idle) will timeout

**Workaround:** Run warmup script before demos/critical usage

**Permanent Fix:** Implement Provisioned Concurrency (see Production Recommendations)

### 2. Model Download on Every Cold Start
**Issue:** 1.1GB model downloads from S3 on each cold start, consuming ephemeral storage and time

**Workaround:** Keep Lambda warm

**Permanent Fix:** Bake model into Docker image

### 3. API Gateway 29-Second Timeout
**Issue:** Hard limit cannot be increased

**Workaround:** Warmup script ensures Lambda is ready

**Permanent Fix:** Switch to Lambda Function URLs + CloudFront

---

## Security Considerations

### Current State (Development)
- CORS: `allow_origins=["*"]` - Accepts requests from any origin
- API Gateway: No authentication
- S3 Frontend: Public read access

### Production Recommendations

1. **Restrict CORS Origins:**
   ```python
   allow_origins=[
       "https://yourdomain.com",
       "https://www.yourdomain.com"
   ]
   ```

2. **Add API Gateway Authorization:**
   - API Keys for rate limiting
   - AWS IAM for service-to-service
   - Cognito for user authentication

3. **Enable CloudTrail:**
   ```bash
   aws cloudtrail create-trail --name lambda-audit --s3-bucket-name audit-logs
   ```

4. **Lambda Function Permissions:**
   - Review IAM role permissions
   - Apply principle of least privilege
   - Enable VPC if accessing private resources

5. **Container Image Scanning:**
   ```bash
   aws ecr put-image-scanning-configuration \
     --repository-name wall-detection-v1 \
     --image-scanning-configuration scanOnPush=true
   ```

---

## Cost Analysis

### Current Monthly Costs (Estimated)

**Lambda Execution:**
- wall-detection-v1: ~$5-10/month (low usage)
- geometric-conversion-v1: ~$2-5/month (low usage)
- Data transfer: ~$1/month

**Storage:**
- ECR: ~$0.50/month (2GB images)
- S3 Frontend: ~$0.10/month
- CloudWatch Logs: ~$1/month

**API Gateway:**
- REST API: ~$3.50/million requests
- First 1M requests free tier

**Total (Development/Low Usage):** ~$10-20/month

**Production with Provisioned Concurrency:**
- Add ~$40/month per instance kept warm
- Recommended: 1 instance = $50-60/month total

---

## Troubleshooting Guide

### Issue: "Image manifest media type not supported"

**Symptom:** Lambda deployment fails with manifest error

**Solution:**
1. Verify `--provenance=false` flag is in build command
2. Check Docker version: `docker --version` (need 23.0+)
3. Rebuild and push: `./infrastructure/scripts/rebuild-and-redeploy-v1.sh`

### Issue: "OpenCV empty image error"

**Symptom:** Geometric conversion returns 500 error with OpenCV assertion

**Solution:**
1. Check frontend is sending `image_dimensions` correctly
2. Verify wall detection response includes `image_dimensions` at top level
3. Rebuild frontend: `cd frontend && npm run build && aws s3 sync dist/ s3://...`

### Issue: First request always times out

**Symptom:** 504 Gateway Timeout on first request, subsequent requests work

**Solution:**
1. This is expected behavior due to model download
2. Run warmup script: `./infrastructure/scripts/warmup-lambdas.sh`
3. For production, enable Provisioned Concurrency

### Issue: Lambda out of memory

**Symptom:** Function error with memory exceeded

**Solution:**
```bash
aws lambda update-function-configuration \
  --function-name wall-detection-v1 \
  --memory-size 4096
```

### Issue: "[Errno 28] No space left on device"

**Symptom:** Lambda fails during model extraction

**Solution:**
```bash
aws lambda update-function-configuration \
  --function-name wall-detection-v1 \
  --ephemeral-storage '{"Size": 5120}'
```

---

## References

### AWS Documentation
- [Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [Lambda Container Image Support](https://aws.amazon.com/blogs/aws/new-for-aws-lambda-container-image-support/)
- [API Gateway Timeouts](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html)

### Docker & BuildKit
- [Docker Buildx Provenance](https://docs.docker.com/build/attestations/slsa-provenance/)
- [BuildKit Multi-Platform Issue](https://github.com/docker/buildx/issues/1533)
- [AWS Lambda Multi-Arch Discussion](https://repost.aws/questions/QUIZjd2sL_TtCuoqtg5Q30LA/does-lambda-not-support-multi-architecture-container-images-manifests)

### Internal Documentation
- [AWS_Summary.md](AWS_Summary.md) - Deployment challenges and history
- [CORS_FIX_GUIDE.md](CORS_FIX_GUIDE.md) - CORS troubleshooting
- [LAMBDA_OPENCV_FIX.md](LAMBDA_OPENCV_FIX.md) - OpenCV dependency fixes

---

## Changelog

### 2025-11-10 - Initial Solution Implementation
- ✅ Added `--provenance=false` to all Docker builds
- ✅ Fixed frontend `image_dimensions` access path
- ✅ Updated TypeScript interfaces for type safety
- ✅ Created deployment scripts with proper flags
- ✅ Tested and verified in production
- ✅ Documented complete solution

---

## Conclusion

The AWS Lambda deployment is now **fully operational** with all critical issues resolved:

1. **Docker Compatibility** - Resolved by adding `--provenance=false` flag
2. **Frontend Integration** - Fixed by correcting image_dimensions access path
3. **Type Safety** - Enhanced with proper TypeScript interfaces

**Production Checklist:**
- [ ] Enable Provisioned Concurrency (eliminates cold starts)
- [ ] Bake model into Docker image (faster cold starts)
- [ ] Restrict CORS origins (security)
- [ ] Add API Gateway authentication (security)
- [ ] Set up CloudWatch alarms (monitoring)
- [ ] Enable ECR image scanning (security)
- [ ] Document incident response procedures

**Application URL:**
http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com

**Status:** ✅ Ready for production use with recommended optimizations
