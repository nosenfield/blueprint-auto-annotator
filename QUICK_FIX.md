# Quick Fix - Lambda OpenCV Error

## Problem
```
Runtime.ImportModuleError: Unable to import module 'app.main':
libGL.so.1: cannot open shared object file
```

## Solution (3 Steps)

### 1. Rebuild Lambdas (5-10 min)
```bash
cd /Users/nosenfield/Desktop/GauntletAI/Week-4-Innergy/room-reader
./infrastructure/scripts/rebuild-and-redeploy-v1.sh
```

### 2. Fix CORS (1 min)
```bash
./infrastructure/scripts/fix-cors.sh
```

### 3. Test (2 min)
```bash
# Test Lambda health
aws lambda invoke \
  --function-name wall-detection-v1 \
  --payload '{"httpMethod":"GET","path":"/"}' \
  response.json && cat response.json | jq .

# Test CORS
curl -X OPTIONS \
  -H "Origin: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com" \
  -i \
  https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod/api/detect-walls
```

## What Was Fixed

**Dockerfile changes:**
- Remove GUI libraries (mesa-libGL, libglvnd-glx)
- Install opencv-python-headless FIRST (before other packages)
- Verify imports during build

**Why it works:**
- ultralytics requires opencv
- Installing opencv-python-headless first satisfies this dependency
- Prevents ultralytics from pulling in regular opencv-python (which needs GUI)
- No GUI libraries needed = no libGL.so.1 error

## Success Indicators

✅ Lambda health check returns 200
✅ CloudWatch logs show "Model loaded successfully"
✅ OPTIONS request returns Access-Control-Allow-Origin header
✅ Frontend can upload images

## Need Help?

- Full guide: `DEPLOYMENT_RECOVERY_GUIDE.md`
- OpenCV details: `LAMBDA_OPENCV_FIX.md`
- CORS troubleshooting: `CORS_FIX_GUIDE.md`
