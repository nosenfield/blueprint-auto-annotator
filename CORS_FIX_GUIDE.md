# CORS Error Fix Guide

## Problem

You're seeing this error:
```
Access to fetch at 'https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls'
from origin 'http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## Root Cause

When using **AWS_PROXY integration** in API Gateway with Lambda:
1. The Lambda function must return ALL HTTP headers, including CORS headers
2. API Gateway passes the Lambda response directly to the client
3. If the Lambda fails or doesn't return proper CORS headers, the browser blocks the request

**Your Lambda handlers already have CORS handling code**, but there might be edge cases where CORS headers aren't being returned.

---

## Solution 1: Fix API Gateway Configuration (Recommended)

### Quick Fix Script

Run the automated fix script:

```bash
chmod +x infrastructure/scripts/fix-cors.sh
./infrastructure/scripts/fix-cors.sh
```

This script will:
- Add proper method responses with CORS parameters
- Redeploy the API Gateway
- Test CORS is working

### Manual API Gateway Fix (if script fails)

1. **Go to API Gateway Console**
   - Navigate to: https://console.aws.amazon.com/apigateway
   - Select API: `room-reader-api`

2. **For each endpoint** (`/api/detect-walls`, `/api/convert-to-rooms`):

   **a. Configure OPTIONS Method (Preflight)**
   - Click on the endpoint resource
   - Click "Create Method" → Select "OPTIONS"
   - Integration type: **Mock**
   - Save

   **b. Add OPTIONS Method Response**
   - Click "Method Response"
   - Add Response: Status 200
   - Add Headers:
     - `Access-Control-Allow-Origin`
     - `Access-Control-Allow-Headers`
     - `Access-Control-Allow-Methods`

   **c. Add OPTIONS Integration Response**
   - Click "Integration Response"
   - Expand the 200 response
   - Add Header Mappings:
     - `Access-Control-Allow-Origin` = `'*'`
     - `Access-Control-Allow-Headers` = `'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'`
     - `Access-Control-Allow-Methods` = `'POST,OPTIONS,GET'`

3. **Deploy Changes**
   - Click "Actions" → "Deploy API"
   - Stage: `prod`
   - Click "Deploy"

4. **Wait 30-60 seconds** for changes to propagate

---

## Solution 2: Verify Lambda CORS Headers

Your Lambda handlers already have CORS wrapper code. Verify it's working:

### Test Lambda Directly

```bash
# Test wall-detection-v1 Lambda
aws lambda invoke \
  --function-name wall-detection-v1 \
  --payload '{"httpMethod":"GET","path":"/","headers":{}}' \
  --region us-east-1 \
  response.json

cat response.json | jq .
```

**Expected output should include:**
```json
{
  "statusCode": 200,
  "headers": {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "POST,OPTIONS,GET"
  },
  "body": "{...}"
}
```

If CORS headers are **missing**, the Lambda handler isn't working correctly.

### Fix Lambda Handler (if needed)

The Lambda handlers in your code already have proper CORS handling:
- `backend/lambda-wall-detection-v1/app/main.py` → Lines 160-207
- `backend/lambda-geometric-conversion-v1/app/main.py` → Lines 170-217

If you need to redeploy:

```bash
# Rebuild and redeploy Lambda
cd backend/lambda-wall-detection-v1
./build-and-deploy.sh

cd ../lambda-geometric-conversion-v1
./build-and-deploy.sh
```

---

## Solution 3: Update API Gateway to use Lambda Proxy Integration

Ensure you're using **AWS_PROXY** integration (not AWS or HTTP):

```bash
# Get API ID
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='room-reader-api'].id" --output text)

# Get resource ID for /api/detect-walls
RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --query "items[?path=='/api/detect-walls'].id" \
  --output text)

# Update integration to AWS_PROXY
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:971422717446:function:wall-detection-v1/invocations"

# Deploy
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod
```

---

## Solution 4: Test CORS from Command Line

### Test OPTIONS (Preflight) Request

```bash
curl -X OPTIONS \
  -H "Origin: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i \
  https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls
```

**Expected Response:**
```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: POST,OPTIONS,GET
Access-Control-Allow-Headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token
```

### Test POST Request

```bash
curl -X POST \
  -H "Origin: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com" \
  -H "Content-Type: application/json" \
  -d '{"image":"","confidence_threshold":0.1}' \
  -i \
  https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls
```

**Look for these headers in response:**
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token
Access-Control-Allow-Methods: POST,OPTIONS,GET
```

---

## Solution 5: Temporary Workaround - Use API Gateway Test Console

While fixing CORS, you can test via API Gateway console:

1. Go to: https://console.aws.amazon.com/apigateway
2. Select `room-reader-api` → Resources → `/api/detect-walls` → POST
3. Click "Test" tab
4. Add request body and test

This bypasses CORS completely since it's server-side testing.

---

## Solution 6: Nuclear Option - Recreate API Gateway

If nothing else works, recreate the API Gateway with proper CORS:

```bash
# Delete existing API
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='room-reader-api'].id" --output text)
aws apigateway delete-rest-api --rest-api-id $API_ID

# Recreate with fixed script
./infrastructure/scripts/setup-api-gateway.sh

# Update frontend with new API URL
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='room-reader-api'].id" --output text)
echo "New API URL: https://${API_ID}.execute-api.us-east-1.amazonaws.com/prod"
```

Then update `frontend/.env.production`:
```
VITE_API_URL=https://NEW_API_ID.execute-api.us-east-1.amazonaws.com/prod
```

And redeploy frontend:
```bash
cd frontend
npm run build
aws s3 sync dist/ s3://room-reader-frontend-971422717446/ --delete
```

---

## Debugging Checklist

Use this checklist to debug systematically:

- [ ] **Step 1:** Test OPTIONS request works (returns 200 with CORS headers)
- [ ] **Step 2:** Test POST request works (returns CORS headers)
- [ ] **Step 3:** Verify Lambda returns CORS headers (test Lambda directly)
- [ ] **Step 4:** Check API Gateway integration type is AWS_PROXY
- [ ] **Step 5:** Verify API Gateway deployment is latest (create new deployment)
- [ ] **Step 6:** Clear browser cache / test in incognito mode
- [ ] **Step 7:** Test from different origin (e.g., localhost:5173)

---

## Common Mistakes

### ❌ Mistake 1: CORS Middleware Without Lambda Handler Wrapper

**Problem:** FastAPI CORS middleware only works when FastAPI handles the request. When Lambda errors occur before FastAPI processes the request, no CORS headers are added.

**Solution:** Your code already has the wrapper (lines 160-207 in main.py). This ensures CORS headers are ALWAYS present.

### ❌ Mistake 2: OPTIONS Method Not Configured

**Problem:** Browser sends OPTIONS preflight request, but API Gateway returns 403 or doesn't have OPTIONS method configured.

**Solution:** Run `fix-cors.sh` script to ensure OPTIONS is properly configured.

### ❌ Mistake 3: API Gateway Caching

**Problem:** API Gateway might cache old responses without CORS headers.

**Solution:** Create a new deployment or clear cache:
```bash
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --description "Cache busting deployment"
```

### ❌ Mistake 4: Browser Cache

**Problem:** Browser cached the CORS error response.

**Solution:**
- Open DevTools → Network tab → Disable cache
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
- Test in incognito mode

---

## Quick Fix Summary

**Run these commands in order:**

```bash
# 1. Fix API Gateway CORS configuration
chmod +x infrastructure/scripts/fix-cors.sh
./infrastructure/scripts/fix-cors.sh

# 2. Wait for propagation
sleep 30

# 3. Test CORS
curl -X OPTIONS \
  -H "Origin: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com" \
  -H "Access-Control-Request-Method: POST" \
  -i \
  https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls

# 4. If CORS headers present, test from browser
# Open: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com
# Upload an image

# 5. If still failing, check browser console for detailed error
```

---

## Success Criteria

CORS is fixed when:

1. ✅ OPTIONS request returns 200 with `Access-Control-Allow-Origin: *`
2. ✅ POST request returns `Access-Control-Allow-Origin: *` header
3. ✅ Browser console shows no CORS errors
4. ✅ Frontend can upload images and get responses

---

## Next Steps

Once CORS is fixed:

1. **Test end-to-end flow:**
   - Upload a blueprint image
   - Verify wall detection works
   - Verify geometric conversion works
   - Check visualization renders

2. **Update documentation:**
   - Document API URLs in README
   - Add API examples
   - Document CORS configuration

3. **Move to Phase 2:**
   - Deploy room detection model (v2)
   - Add v2 endpoint to API Gateway
   - Enable v2 in frontend

---

## Support

If issues persist:

1. **Check CloudWatch Logs:**
   ```bash
   aws logs tail /aws/lambda/wall-detection-v1 --follow
   ```

2. **Enable API Gateway Logging:**
   - Go to API Gateway Console
   - Settings → CloudWatch log role ARN
   - Enable detailed logs

3. **Test Lambda Directly:**
   ```bash
   aws lambda invoke \
     --function-name wall-detection-v1 \
     --payload file://test-payload.json \
     response.json
   ```

---

## References

- [AWS API Gateway CORS](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [Mangum Lambda Handler](https://github.com/jordaneremieff/mangum)
