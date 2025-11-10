# Deployment Recovery Guide

## Current Status

**Issue:** Lambda functions failing during initialization with OpenCV import error
**Impact:** Cannot test API endpoints, CORS configuration, or frontend integration
**Root Cause:** `ultralytics` library pulling in regular `opencv-python` instead of headless version

---

## Quick Recovery Steps

### Step 1: Rebuild Lambda Functions with OpenCV Fix

```bash
cd /Users/nosenfield/Desktop/GauntletAI/Week-4-Innergy/room-reader

# Run automated rebuild script
./infrastructure/scripts/rebuild-and-redeploy-v1.sh
```

**What this does:**
- Rebuilds Docker images with fixed Dockerfiles
- Ensures opencv-python-headless is installed first (prevents GUI dependency issues)
- Pushes new images to ECR
- Updates Lambda functions
- Tests Lambda health checks
- Takes ~5-10 minutes

**Expected Output:**
```
✓ Built wall-detection-v1
✓ Pushed wall-detection-v1
✓ Lambda function updated
✓ Function ready
✓ wall-detection-v1 working (health check passed)
✓ Built geometric-conversion-v1
✓ Pushed geometric-conversion-v1
✓ Lambda function updated
✓ Function ready
✓ geometric-conversion-v1 working (health check passed)
```

---

### Step 2: Fix CORS Configuration

```bash
# Run CORS fix script
./infrastructure/scripts/fix-cors.sh
```

**What this does:**
- Adds proper OPTIONS method responses for preflight requests
- Ensures CORS headers are present in all responses
- Redeploys API Gateway
- Tests CORS is working

**Expected Output:**
```
✓ Method responses configured
✓ Changes deployed
✓ CORS headers present
```

---

### Step 3: Test End-to-End

```bash
# Test API directly
API_URL="https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod"

curl -X OPTIONS \
  -H "Origin: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com" \
  -i \
  "${API_URL}/api/detect-walls"

# Should return: Access-Control-Allow-Origin: *
```

**Then test from browser:**
1. Open: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com
2. Upload a blueprint image
3. Verify detection works
4. Check browser console for errors

---

## What Was Fixed

### Problem 1: OpenCV Import Error

**Error Message:**
```
Runtime.ImportModuleError: Unable to import module 'app.main':
libGL.so.1: cannot open shared object file: No such file or directory
```

**Root Cause:**
- `ultralytics` (YOLO library) has OpenCV as a dependency
- When pip installs ultralytics, it may pull in regular `opencv-python`
- Regular `opencv-python` requires GUI libraries (`libGL.so.1`)
- Lambda containers don't have GUI libraries
- Import fails before Lambda handler runs

**Solution:**
- Install `opencv-python-headless` **first** in separate pip command
- This satisfies ultralytics' OpenCV dependency without GUI libraries
- Remove GUI library installations from Dockerfile (not needed)
- Verify OpenCV loads during Docker build

**Files Changed:**
- `backend/lambda-wall-detection-v1/Dockerfile` - Fixed build order
- `backend/lambda-wall-detection-v1/requirements.txt` - Added comments
- `backend/lambda-geometric-conversion-v1/Dockerfile` - Fixed build order
- `backend/lambda-geometric-conversion-v1/requirements.txt` - No changes needed

### Problem 2: CORS Headers Missing

**Error Message:**
```
Access to fetch at 'https://...amazonaws.com/prod/api/detect-walls'
from origin 'http://...s3-website...amazonaws.com'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header
```

**Root Cause:**
- Browser sends OPTIONS preflight request before POST
- API Gateway needs proper OPTIONS method configuration
- Lambda handlers have CORS code, but OPTIONS must be configured at API Gateway level
- With AWS_PROXY integration, both Lambda and API Gateway need CORS setup

**Solution:**
- Configure OPTIONS methods with MOCK integration
- Add CORS headers to OPTIONS integration responses
- Lambda handlers already have CORS wrapper (no changes needed)
- Redeploy API Gateway for changes to take effect

**Files Changed:**
- `infrastructure/scripts/fix-cors.sh` - New script to fix CORS
- `CORS_FIX_GUIDE.md` - Comprehensive troubleshooting guide

---

## File Summary

### New Files Created

1. **`infrastructure/scripts/rebuild-and-redeploy-v1.sh`**
   - Automated rebuild and redeploy script
   - Rebuilds Docker images with OpenCV fix
   - Updates Lambda functions
   - Tests health checks

2. **`infrastructure/scripts/fix-cors.sh`**
   - Automated CORS fix script
   - Configures OPTIONS methods
   - Adds CORS headers to all responses
   - Tests CORS is working

3. **`LAMBDA_OPENCV_FIX.md`**
   - Detailed explanation of OpenCV issue
   - Why fix works
   - How to prevent in future
   - Troubleshooting guide

4. **`CORS_FIX_GUIDE.md`**
   - 6 different CORS solutions
   - Debugging checklist
   - Common mistakes to avoid
   - Testing procedures

5. **`DEPLOYMENT_RECOVERY_GUIDE.md`** (this file)
   - Quick recovery steps
   - What was fixed
   - Verification procedures

### Modified Files

1. **`backend/lambda-wall-detection-v1/Dockerfile`**
   - Removed GUI library installations
   - Install opencv-python-headless first
   - Verify imports during build

2. **`backend/lambda-wall-detection-v1/requirements.txt`**
   - Reordered packages
   - Added explanatory comments

3. **`backend/lambda-geometric-conversion-v1/Dockerfile`**
   - Removed GUI library installations
   - Install opencv-python-headless first
   - Verify imports during build

---

## Verification Checklist

After running recovery steps, verify:

### Lambda Functions
- [ ] wall-detection-v1 health check returns 200
- [ ] geometric-conversion-v1 health check returns 200
- [ ] CloudWatch logs show "Model loaded successfully"
- [ ] No "ImportModuleError" in logs
- [ ] Lambda can be invoked directly via AWS CLI

### API Gateway
- [ ] OPTIONS request returns Access-Control-Allow-Origin header
- [ ] POST request returns Access-Control-Allow-Origin header
- [ ] No 403 or 502 errors
- [ ] API Gateway logs show successful Lambda invocations

### Frontend Integration
- [ ] Frontend can reach API Gateway
- [ ] No CORS errors in browser console
- [ ] Can upload images
- [ ] Receives detection results
- [ ] Visualization renders (if implemented)

---

## Testing Commands

### Test Lambda Directly

```bash
# Test wall-detection-v1
aws lambda invoke \
  --function-name wall-detection-v1 \
  --payload '{"httpMethod":"GET","path":"/"}' \
  --region us-east-1 \
  response.json && cat response.json | jq .

# Test geometric-conversion-v1
aws lambda invoke \
  --function-name geometric-conversion-v1 \
  --payload '{"httpMethod":"GET","path":"/"}' \
  --region us-east-1 \
  response.json && cat response.json | jq .
```

### Test API Gateway

```bash
API_URL="https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod"

# Test OPTIONS (preflight)
curl -X OPTIONS \
  -H "Origin: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com" \
  -H "Access-Control-Request-Method: POST" \
  -i \
  "${API_URL}/api/detect-walls"

# Test POST (should fail with invalid image, but proves Lambda runs)
curl -X POST \
  -H "Origin: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com" \
  -H "Content-Type: application/json" \
  -d '{"image":"","confidence_threshold":0.1}' \
  "${API_URL}/api/detect-walls"
```

### Monitor CloudWatch Logs

```bash
# Watch Lambda logs in real-time
aws logs tail /aws/lambda/wall-detection-v1 --follow --region us-east-1

# In another terminal
aws logs tail /aws/lambda/geometric-conversion-v1 --follow --region us-east-1
```

---

## Troubleshooting

### Issue: Docker Build Fails

**Error:** Cannot find model files

**Solution:**
```bash
# Ensure you're building from backend/ directory
cd backend
ls lambda-wall-detection-v1/models/best_wall_model.pt  # Should exist

# Build with explicit context
docker build -t wall-detection-v1:latest -f lambda-wall-detection-v1/Dockerfile .
```

### Issue: ECR Push Fails

**Error:** Authentication required

**Solution:**
```bash
# Re-login to ECR
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
```

### Issue: Lambda Still Has Import Error

**Possible Causes:**
1. Docker cache used old image
2. Lambda not updated to new image
3. Wrong OpenCV version installed

**Solution:**
```bash
# Rebuild without cache
cd backend
docker build --no-cache -t wall-detection-v1:latest -f lambda-wall-detection-v1/Dockerfile .

# Verify opencv-python-headless is installed
docker run --rm wall-detection-v1:latest pip list | grep opencv
# Should show: opencv-python-headless  4.8.1.78

# Push and update Lambda
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
docker tag wall-detection-v1:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1:latest

aws lambda update-function-code \
  --function-name wall-detection-v1 \
  --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1:latest \
  --region us-east-1

# Wait for update
aws lambda wait function-updated --function-name wall-detection-v1 --region us-east-1
```

### Issue: CORS Still Failing

**Check:**
1. Browser cache cleared?
2. API Gateway deployed?
3. Lambda returns CORS headers?

**Solutions:**

```bash
# Redeploy API Gateway
API_ID=$(aws apigateway get-rest-apis --region us-east-1 --query "items[?name=='room-reader-api'].id" --output text)
aws apigateway create-deployment --rest-api-id $API_ID --stage-name prod --region us-east-1

# Wait 30 seconds for propagation
sleep 30

# Test again
curl -X OPTIONS \
  -H "Origin: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com" \
  -i \
  https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls
```

---

## Expected Timeline

- **Step 1 (Rebuild Lambdas):** 5-10 minutes
- **Step 2 (Fix CORS):** 1-2 minutes
- **Step 3 (Test):** 2-3 minutes
- **Total:** ~15 minutes

---

## Success Criteria

Deployment is successful when:

1. ✅ Lambda health checks return 200
2. ✅ CloudWatch logs show "Model loaded successfully"
3. ✅ No import errors in logs
4. ✅ OPTIONS request returns CORS headers
5. ✅ POST request returns CORS headers
6. ✅ Frontend can upload images
7. ✅ Frontend receives detection results
8. ✅ No CORS errors in browser console

---

## Next Steps After Recovery

Once deployment is working:

1. **Complete Phase 1 Testing:**
   - Upload various blueprint images
   - Verify wall detection accuracy
   - Test geometric conversion
   - Check visualization rendering

2. **Monitor Production:**
   - Set up CloudWatch alarms
   - Monitor Lambda execution times
   - Track detection success rates
   - Review error logs daily

3. **Deploy Phase 2 (Room Model v2):**
   - Follow same process for room detection Lambda
   - Apply same OpenCV fixes
   - Configure v2 API endpoints
   - Enable v2 in frontend

4. **Documentation:**
   - Update README with API endpoints
   - Document deployment process
   - Add API examples
   - Document CORS configuration

---

## Support Resources

- **Lambda OpenCV Fix:** See `LAMBDA_OPENCV_FIX.md`
- **CORS Troubleshooting:** See `CORS_FIX_GUIDE.md`
- **Architecture Overview:** See `_docs/architecture-v2.md`
- **Task List:** See `_docs/task-list-v2.md`

---

## Contact

If issues persist after following this guide:

1. Check CloudWatch Logs for detailed error messages
2. Review Docker build logs for compilation errors
3. Test Lambda functions in AWS Console (Test tab)
4. Verify IAM permissions for Lambda execution role
5. Check API Gateway integration configuration

---

## Appendix: What We Learned

### Key Takeaways

1. **Lambda container imports happen at cold start, before handler runs**
   - Import errors block Lambda completely
   - Can't catch import errors in handler code
   - Must fix at Docker build level

2. **Python package installation order matters**
   - Installing opencv-python-headless first prevents conflicts
   - Later packages use already-satisfied dependencies
   - Dockerfile RUN order is critical

3. **CORS requires both API Gateway and Lambda configuration**
   - OPTIONS must be configured at API Gateway
   - POST/GET headers must come from Lambda
   - Both are necessary with AWS_PROXY integration

4. **Docker caching can hide problems**
   - Always rebuild without cache when debugging
   - Verify dependencies in running container
   - Test imports during Docker build

### Prevention Strategies

1. **Always test Docker images locally before deploying**
2. **Use opencv-python-headless in all Lambda functions**
3. **Install critical dependencies first in Dockerfile**
4. **Verify imports during Docker build**
5. **Test Lambda health checks after every deployment**
6. **Configure CORS at initial API Gateway setup**
7. **Document all OpenCV/GUI library workarounds**

---

**Last Updated:** $(date)
**Version:** 1.0
**Status:** Ready for Recovery
