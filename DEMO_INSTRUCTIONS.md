# Room Reader Demo Instructions

## Quick Start

**Before each demo, run the warmup script:**

```bash
./infrastructure/scripts/warmup-lambdas.sh
```

This takes ~30-60 seconds and keeps the Lambda functions warm for 10-15 minutes.

## Application URLs

- **Frontend**: http://room-reader-frontend-971422717446.s3-website-us-east-1.amazonaws.com
- **API Gateway**: https://3jkxonfmu1.execute-api.us-east-1.amazonaws.com/prod

## Demo Flow

1. **Warm up Lambdas** (1 minute before demo):
   ```bash
   ./infrastructure/scripts/warmup-lambdas.sh
   ```

2. **Open Frontend** in browser

3. **Upload a Blueprint Image**:
   - Use test images from `_poc/input-output/blueprint.png`
   - Or any architectural blueprint image

4. **Select Model**:
   - **Wall Model (v1)**: 2-step pipeline (wall detection → geometric conversion)
   - **Room Model (v2)**: Direct room detection

5. **Adjust Confidence Threshold**:
   - v1: Default 0.10 (lower = more detections)
   - v2: Default 0.50

6. **Click "Detect Rooms"**

## Known Limitations (Demo Only)

### Cold Start Timeout
- **Issue**: First API call after 15+ minutes will timeout (API Gateway 29s limit < Lambda cold start ~30-40s)
- **Solution**: Run warmup script before demos
- **Production Fix**: Would use Lambda Provisioned Concurrency (~$20/month)

### Why This Works for Demo
- Lambda stays warm for 10-15 minutes after first invocation
- Once warm, responses are fast (~2-5 seconds)
- Perfect for demonstrations and testing

## Troubleshooting

### "Endpoint request timed out"
**Cause**: Lambda cold start exceeded 29s API Gateway timeout

**Fix**: Run warmup script:
```bash
./infrastructure/scripts/warmup-lambdas.sh
```

### "CORS Error" in Browser
**Cause**: Lambda permissions or CORS headers missing

**Fix**: CORS is already configured. If issues persist:
```bash
./infrastructure/scripts/fix-cors.sh
```

### "Internal Server Error"
**Cause**: Lambda crashed or timeout

**Check logs**:
```bash
aws logs tail /aws/lambda/wall-detection-v1 --region us-east-1 --since 10m
```

## Architecture

### V1 Pipeline (Wall Model)
```
Blueprint Image → Wall Detection Lambda → Geometric Conversion Lambda → Room Polygons
```

### V2 Pipeline (Room Model)
```
Blueprint Image → Room Detection Lambda → Room Bounding Boxes
```

## Deployment

All Lambdas are deployed and configured with:
- ✅ OpenCV headless (no GUI dependencies)
- ✅ CORS headers
- ✅ x86_64 architecture
- ✅ 120s Lambda timeout
- ✅ 3GB memory
- ✅ API Gateway integration

## API Endpoints

### POST /api/detect-walls
Detect walls in blueprint image (v1 model)

**Request**:
```json
{
  "image": "base64_encoded_image",
  "confidence_threshold": 0.10
}
```

**Response**:
```json
{
  "success": true,
  "walls": [...],
  "total_walls": 42,
  "processing_time_ms": 1234,
  "metadata": {
    "model": "YOLOv8-Medium",
    "image_dimensions": [1920, 1080]
  }
}
```

### POST /api/convert-to-rooms
Convert wall detections to room polygons

**Request**:
```json
{
  "walls": [...],
  "image_dimensions": [1920, 1080],
  "min_room_area": 2000
}
```

### POST /api/v2/detect-rooms
Direct room detection (v2 model)

**Request**:
```json
{
  "image": "base64_encoded_image",
  "confidence_threshold": 0.50
}
```

## Cost Estimate (Demo Usage)

- **Lambda**: ~$0.20/month (free tier covers most)
- **S3**: ~$0.50/month
- **API Gateway**: ~$0.35/month (free tier: 1M requests)
- **ECR**: ~$0.10/month (500MB images)

**Total**: ~$1-2/month for demo/testing usage

For production with provisioned concurrency: +$15-20/month per Lambda
