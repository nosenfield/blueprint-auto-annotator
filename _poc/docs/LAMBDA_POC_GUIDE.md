# Lambda + Container POC Guide - YOLO Room Detection

## 🎯 Overview

This approach deploys your trained YOLOv8 model to AWS Lambda using a container image. It provides:

✅ **Direct control** - No TorchServe wrapper  
✅ **Pay-per-use** - ~$0.01/image, no charges when idle  
✅ **Simpler than SageMaker** - No endpoint management  
✅ **Good for low volume** - Ideal for <1000 images/day  
✅ **Your trained model** - Uses your 70% accuracy YOLO model

---

## 📋 Prerequisites

### 1. Docker Desktop
```bash
# Check if Docker is installed
docker --version

# If not installed, download from:
# https://www.docker.com/products/docker-desktop
```

### 2. AWS CLI Configured
```bash
# Check AWS CLI
aws --version

# Verify credentials
aws sts get-caller-identity

# Should show your account ID and user
```

### 3. IAM Permissions
You need permissions for:
- Lambda (create, update functions)
- ECR (create repositories, push images)
- IAM (create roles)
- S3 (read model from bucket)

---

## 🚀 Quick Start (30-45 minutes)

### Step 1: Navigate to Lambda Directory (2 min)

```bash
cd lambda-yolo

# Verify files are present
ls -la

# You should see:
# - Dockerfile
# - requirements.txt
# - lambda_handler.py
# - yolo_inference.py
# - deploy.sh
# - test_lambda.sh
```

---

### Step 2: Make Scripts Executable (1 min)

```bash
chmod +x deploy.sh
chmod +x test_lambda.sh
```

---

### Step 3: Deploy to AWS (15-20 min)

```bash
./deploy.sh
```

**What this does:**
1. Creates ECR repository (if needed)
2. Builds Docker image (~5-10 min)
3. Pushes to ECR (~5-10 min)
4. Creates IAM role (if needed)
5. Creates Lambda function with 3GB memory, 5min timeout

**Expected output:**
```
========================================
YOLO Lambda Deployment Script
========================================

Step 1: Creating ECR repository...
  ✓ ECR repository created
  Repository URI: 971422717446.dkr.ecr.us-east-1.amazonaws.com/yolo-room-detection

Step 2: Building Docker image...
  This may take 5-10 minutes...
  [Docker build output...]
  ✓ Docker image built successfully

Step 3: Tagging image...
  ✓ Image tagged

Step 4: Logging in to ECR...
  ✓ Logged in to ECR

Step 5: Pushing image to ECR...
  This may take 5-10 minutes...
  ✓ Image pushed to ECR

Step 6: Creating Lambda execution role...
  ✓ Role created: arn:aws:iam::971422717446:role/yolo-lambda-execution-role

Step 7: Deploying Lambda function...
  Creating new function...
  ✓ Function created

========================================
Deployment Complete!
========================================

Function Name: yolo-room-detection
Memory: 3008 MB
Timeout: 300 seconds (5 minutes)
```

---

### Step 4: Test the Function (5 min)

```bash
# Copy your test image to lambda-yolo directory
cp ../generated_blueprint.png .

# Test Lambda function
./test_lambda.sh generated_blueprint.png
```

**First invocation (cold start):**
```
========================================
Testing YOLO Lambda Function
========================================

Test image: generated_blueprint.png
Function: yolo-room-detection

Encoding image to base64...
  ✓ Image encoded (123456 characters)

Invoking Lambda function...
  This may take 10-15 seconds on cold start...

Response received in 12s

Results:
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json",
    ...
  },
  "body": {
    "success": true,
    "detected_rooms": [
      {
        "id": "room_001",
        "bounding_box": [85, 110, 335, 890],
        "bounding_box_pixels": [102, 99, 402, 801],
        "name_hint": "room",
        "confidence": 0.87,
        "shape_type": "rectangle"
      },
      ...
    ],
    "total_rooms_detected": 3,
    "model": "YOLOv8-Large",
    "inference_time": 0.45,
    "image_dimensions": [1200, 900]
  }
}

Summary:
  Success: True
  Rooms detected: 3
  Inference time: 0.45s
  Total time (including cold start): 12s

Cost estimate:
  GB-seconds: 36.096
  Estimated cost: $0.000601

Test complete!
```

**Subsequent invocations (warm):**
- Total time: ~1-2 seconds
- Inference time: ~0.5 seconds
- Much faster since container is already loaded

---

### Step 5: Compare with Claude Vision (5 min)

Create a comparison script:

```bash
# Create comparison
python3 << 'EOF'
import json

# Load Lambda results
with open('lambda_test_results_*.json') as f:
    lambda_data = json.load(f)
    lambda_body = json.loads(lambda_data['body'])

# Load Claude results (from earlier POC)
with open('../poc_test_results.json') as f:
    claude_data = json.load(f)

# Load ground truth
with open('../generated_blueprint_ground_truth.json') as f:
    gt_data = json.load(f)

print("="*70)
print("COMPARISON: Lambda YOLO vs Claude Vision")
print("="*70)
print()

print("Detection Count:")
print(f"  Lambda YOLO: {lambda_body['total_rooms_detected']} rooms")
print(f"  Claude:      {claude_data['total_rooms_detected']} rooms")
print(f"  Ground Truth: {gt_data['total_rooms']} rooms")
print()

print("Inference Speed:")
print(f"  Lambda (warm): ~1-2s")
print(f"  Lambda (cold): ~10-15s")
print(f"  Claude:        ~5-10s")
print()

print("Cost Per Image:")
print(f"  Lambda: ~$0.001-0.002")
print(f"  Claude: $0.0086")
print(f"  Winner: Lambda is 4-8x cheaper per image")
print()

print("Coordinate Accuracy:")
lambda_rooms = lambda_body['detected_rooms']
claude_rooms = claude_data['detected_rooms']
gt_rooms = gt_data['rooms']

lambda_error = sum(
    sum(abs(lambda_rooms[i]['bounding_box'][j] - gt_rooms[i]['bbox_normalized'][j]) 
        for j in range(4)) / 4
    for i in range(min(len(lambda_rooms), len(gt_rooms)))
) / len(gt_rooms)

claude_error = sum(
    sum(abs(claude_rooms[i]['bounding_box'][j] - gt_rooms[i]['bbox_normalized'][j]) 
        for j in range(4)) / 4
    for i in range(min(len(claude_rooms), len(gt_rooms)))
) / len(gt_rooms)

print(f"  Lambda avg error: {lambda_error:.1f} pixels")
print(f"  Claude avg error: {claude_error:.1f} pixels")
print(f"  Lambda accuracy: {100 - (lambda_error/1000*100):.1f}%")
print(f"  Claude accuracy: {100 - (claude_error/1000*100):.1f}%")
print()

EOF
```

---

## 📊 Expected Results

### Lambda YOLO Performance

**Accuracy:**
- Should match training accuracy (~70-80% detection rate)
- Coordinate precision: ~95%+ (better than Claude)
- Confidence scores: Numeric (0.0-1.0)

**Speed:**
- Cold start: 10-15 seconds (first request or after 15 min idle)
- Warm invocation: 1-2 seconds
- Inference only: ~0.5 seconds

**Cost:**
- Per image: ~$0.001-0.002
- 1000 images/month: ~$1-2
- 10,000 images/month: ~$10-20
- No charges when idle

### vs Claude Vision

| Metric | Lambda YOLO | Claude Vision | Winner |
|--------|-------------|---------------|--------|
| Coordinate Accuracy | ~95% | ~85% | Lambda |
| Detection Rate | ~70-80% | 100% | Claude |
| Speed (warm) | 1-2s | 5-10s | Lambda |
| Speed (cold) | 10-15s | 5-10s | Claude |
| Cost/image | $0.001-0.002 | $0.0086 | Lambda |
| Maintenance | Low | None | Claude |
| Room Labels | Limited | Excellent | Claude |

---

## 🎯 Decision Framework

### Choose Lambda YOLO if:
- ✅ Coordinate precision is critical (>90% required)
- ✅ Processing >200 images/month (cost-effective)
- ✅ Sub-2s latency needed (warm invocations)
- ✅ Comfortable with AWS infrastructure
- ✅ Detection rate of 70-80% is acceptable

### Choose Claude Vision if:
- ✅ Need 100% detection rate
- ✅ Processing <200 images/month
- ✅ Want zero infrastructure
- ✅ Need room semantic labeling
- ✅ 85% coordinate accuracy acceptable

### Choose Hybrid if:
- ✅ Need both precision AND detection rate
- ✅ Budget allows ($15-20/month at MVP scale)
- ✅ Can handle 3-5s total latency

---

## 💰 Cost Analysis

### Scenario 1: MVP (<10 users, ~50 images/day)

**Lambda YOLO:**
```
50 images/day × 30 days = 1,500 images/month
Cost: 1,500 × $0.0015 = $2.25/month
✅ Very cheap
```

**Claude Vision:**
```
1,500 × $0.0086 = $12.90/month
⚠️ 5.7x more expensive than Lambda
```

**Winner: Lambda** (but both are affordable)

---

### Scenario 2: Growth (~500 images/day)

**Lambda YOLO:**
```
500 × 30 = 15,000 images/month
Cost: 15,000 × $0.0015 = $22.50/month
✅ Still very affordable
```

**Claude Vision:**
```
15,000 × $0.0086 = $129/month
⚠️ 5.7x more expensive
```

**Winner: Lambda** (significant savings)

---

### Scenario 3: Scale (~2000 images/day)

**Lambda YOLO:**
```
2000 × 30 = 60,000 images/month
Cost: 60,000 × $0.0015 = $90/month
✅ Scales linearly
```

**Claude Vision:**
```
60,000 × $0.0086 = $516/month
❌ Getting expensive
```

**SageMaker (always-on):**
```
$193/month (fixed)
✅ Now competitive with Lambda
```

**Winner: Depends on actual usage patterns**

---

## 🔧 Configuration & Optimization

### Adjust Lambda Settings

**Memory (affects speed and cost):**
```bash
# Increase memory for faster inference (also increases cost)
aws lambda update-function-configuration \
    --function-name yolo-room-detection \
    --memory-size 5120  # 5GB (max for non-GPU)
```

**Environment Variables:**
```bash
# Adjust confidence threshold
aws lambda update-function-configuration \
    --function-name yolo-room-detection \
    --environment Variables="{
        CONFIDENCE_THRESHOLD=0.6,
        IOU_THRESHOLD=0.5,
        IMAGE_SIZE=640
    }"
```

### Provisioned Concurrency (Eliminate Cold Starts)

```bash
# Keep 1 instance warm at all times
aws lambda put-provisioned-concurrency-config \
    --function-name yolo-room-detection \
    --provisioned-concurrent-executions 1

# Cost: ~$12/month additional
# Benefit: No cold starts (always 1-2s response)
```

---

## 🐛 Troubleshooting

### Issue: "Task timed out after 300 seconds"

**Solution:** Model may be too large or inference too slow
```bash
# Check CloudWatch logs
aws logs tail /aws/lambda/yolo-room-detection --follow

# Optimize: Use smaller image size
# Update environment: IMAGE_SIZE=416 (instead of 640)
```

### Issue: "Container image size exceeded"

**Solution:** Image > 10GB limit
```bash
# Check image size
docker images yolo-room-detection

# Optimize: Remove unnecessary dependencies in Dockerfile
```

### Issue: "Out of memory"

**Solution:** Increase Lambda memory
```bash
aws lambda update-function-configuration \
    --function-name yolo-room-detection \
    --memory-size 10240  # Maximum
```

---

## 📈 Monitoring

### View Logs
```bash
# Real-time logs
aws logs tail /aws/lambda/yolo-room-detection --follow

# Recent logs
aws logs tail /aws/lambda/yolo-room-detection --since 1h
```

### Check Metrics
```bash
# Invocation count
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=yolo-room-detection \
    --start-time 2025-11-01T00:00:00Z \
    --end-time 2025-11-08T23:59:59Z \
    --period 86400 \
    --statistics Sum

# Duration
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Duration \
    --dimensions Name=FunctionName,Value=yolo-room-detection \
    --start-time 2025-11-01T00:00:00Z \
    --end-time 2025-11-08T23:59:59Z \
    --period 86400 \
    --statistics Average
```

---

## 🗑️ Cleanup

### Delete Lambda Function
```bash
aws lambda delete-function \
    --function-name yolo-room-detection
```

### Delete ECR Repository
```bash
aws ecr delete-repository \
    --repository-name yolo-room-detection \
    --force
```

### Delete IAM Role
```bash
aws iam detach-role-policy \
    --role-name yolo-lambda-execution-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam detach-role-policy \
    --role-name yolo-lambda-execution-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

aws iam delete-role \
    --role-name yolo-lambda-execution-role
```

---

## 🎬 Next Steps After POC

### If Lambda YOLO works well:

1. **Request architecture.md for Lambda-based system**
2. Set up API Gateway for HTTP endpoint
3. Add authentication (API keys)
4. Implement caching layer
5. Set up monitoring/alerts

### If results are mixed:

1. **Compare results** with ground truth
2. **Calculate accuracy metrics** systematically
3. **Test with more blueprints** (10+ different layouts)
4. **Consider hybrid** (Lambda + Claude for labels)

---

## 📞 What to Report Back

After testing, tell me:

```
Lambda POC Results:

1. Deployment: [Success/Failed]
2. Test Results:
   - Rooms detected: X out of Y
   - Coordinate accuracy: X%
   - Inference time (warm): Xs
   - Cost per image: $X

3. Comparison vs Claude:
   - Which is more accurate?
   - Which is faster?
   - Which is cheaper?

4. Decision: [Use Lambda / Use Claude / Use Hybrid / Need more testing]
```

---

**Ready to deploy? Run `./deploy.sh` in the lambda-yolo directory!** 🚀
