# Next Steps to Fix Lambda Container Runtime Error

## Current Issue
- ✅ JSON encoding fixed
- ✅ Lambda invocation working
- ❌ Container runtime error: `Runtime.InvalidEntrypoint` with `ProcessSpawnFailed`

## Recommended Steps

### Step 1: Test Container Locally (5 min)
Test the container locally before redeploying:

```bash
# Build the image
docker build -t yolo-room-detection:test .

# Run the container locally
docker run -p 9000:8080 \
  -e MODEL_S3_BUCKET=sagemaker-us-east-1-971422717446 \
  -e MODEL_S3_KEY=room-detection-yolo-1762559721/output/model.tar.gz \
  -e CONFIDENCE_THRESHOLD=0.5 \
  -e IOU_THRESHOLD=0.4 \
  -e IMAGE_SIZE=640 \
  yolo-room-detection:test

# In another terminal, test it:
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"image": "test"}'
```

**If this works locally**, the issue is with the deployed image. If it fails, we need to fix the Dockerfile.

### Step 2: Rebuild and Redeploy (15-20 min)

If local test works, rebuild and redeploy:

```bash
# Rebuild image
docker build -t yolo-room-detection:latest .

# Tag for ECR
docker tag yolo-room-detection:latest \
  971422717446.dkr.ecr.us-east-1.amazonaws.com/yolo-room-detection:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  971422717446.dkr.ecr.us-east-1.amazonaws.com

docker push 971422717446.dkr.ecr.us-east-1.amazonaws.com/yolo-room-detection:latest

# Update Lambda function
aws lambda update-function-code \
  --function-name yolo-room-detection \
  --image-uri 971422717446.dkr.ecr.us-east-1.amazonaws.com/yolo-room-detection:latest \
  --region us-east-1

# Wait for update
aws lambda wait function-updated \
  --function-name yolo-room-detection \
  --region us-east-1
```

### Step 3: Test Again

```bash
./test_lambda.sh generated_blueprint.png
```

## Alternative: Quick Fix Script

I can create a script to do all of this automatically. Would you like me to:

1. **Create a fix script** that rebuilds and redeploys?
2. **Test locally first** to diagnose the issue?
3. **Check CloudWatch logs** for more detailed error messages?

## Most Likely Issue

The `ProcessSpawnFailed` error usually means:
- Handler path is incorrect
- Python dependencies missing
- File permissions issue
- Architecture mismatch (ARM64 vs x86_64)

Since we're using the Lambda Python base image, the CMD format should be correct. The issue might be:
1. The image architecture (we built ARM64, Lambda might need x86_64)
2. Missing dependencies
3. File location issues

**Recommendation:** Test locally first to isolate the issue, then fix and redeploy.

