# Infrastructure Deployment

This directory contains scripts and configuration for deploying the Room Reader application to AWS.

## Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   aws --version
   aws configure
   ```

2. **Docker Desktop** installed and running
   ```bash
   docker --version
   docker ps
   ```

3. **AWS Account** with appropriate permissions:
   - Lambda (create, update functions)
   - ECR (create repositories, push images)
   - IAM (create roles)
   - API Gateway (create APIs)
   - CloudWatch Logs (for Lambda logging)

## Quick Start

### Deploy All v1 Lambda Functions

```bash
./infrastructure/scripts/deploy-all-v1.sh
```

This script will:
1. Create IAM role (if needed)
2. Deploy wall detection Lambda v1
3. Deploy geometric conversion Lambda v1

### Individual Deployment

```bash
# Setup IAM role
./infrastructure/scripts/setup-iam-role.sh

# Deploy wall detection Lambda
./infrastructure/scripts/deploy-wall-detection-v1.sh

# Deploy geometric conversion Lambda
./infrastructure/scripts/deploy-geometric-conversion-v1.sh
```

## Scripts

### `setup-iam-role.sh`
Creates IAM role with necessary permissions for Lambda execution.

### `deploy-wall-detection-v1.sh`
Builds Docker image, pushes to ECR, and creates/updates wall detection Lambda function.

### `deploy-geometric-conversion-v1.sh`
Builds Docker image, pushes to ECR, and creates/updates geometric conversion Lambda function.

### `deploy-all-v1.sh`
Master script that deploys all v1 Lambda functions.

### `setup-api-gateway.sh`
Provides guidance for setting up API Gateway (manual configuration required).

## Configuration

### Environment Variables

- `AWS_REGION`: AWS region (default: `us-east-1`)
- `AWS_ACCOUNT_ID`: Auto-detected from AWS credentials

### Lambda Function Configuration

**Wall Detection Lambda v1:**
- Memory: 3008 MB
- Timeout: 30 seconds
- Package Type: Container Image

**Geometric Conversion Lambda v1:**
- Memory: 2048 MB
- Timeout: 30 seconds
- Package Type: Container Image

## ECR Repositories

- `wall-detection-v1`: Docker images for wall detection Lambda
- `geometric-conversion-v1`: Docker images for geometric conversion Lambda

## API Gateway Setup

API Gateway setup requires manual configuration or Terraform. See `setup-api-gateway.sh` for guidance.

Recommended endpoints:
- `POST /api/detect-walls` → `wall-detection-v1` Lambda
- `POST /api/convert-to-rooms` → `geometric-conversion-v1` Lambda

## Testing

After deployment, test Lambda functions:

```bash
# Test wall detection Lambda
aws lambda invoke \
  --function-name wall-detection-v1 \
  --payload '{"image": "base64-encoded-image"}' \
  response.json

# Test geometric conversion Lambda
aws lambda invoke \
  --function-name geometric-conversion-v1 \
  --payload '{"walls": [...], "image_dimensions": [100, 100]}' \
  response.json
```

## Monitoring

View Lambda logs:

```bash
# Wall detection Lambda logs
aws logs tail /aws/lambda/wall-detection-v1 --follow

# Geometric conversion Lambda logs
aws logs tail /aws/lambda/geometric-conversion-v1 --follow
```

## Troubleshooting

### Docker not running
```bash
# Start Docker Desktop
open -a Docker
```

### AWS credentials not configured
```bash
aws configure
```

### IAM role not found
```bash
./infrastructure/scripts/setup-iam-role.sh
```

### Lambda function update fails
- Check IAM role permissions
- Verify ECR image exists
- Check CloudWatch logs for errors

## Cost Estimates

**Lambda:**
- Wall Detection: ~$0.001-0.002 per image
- Geometric Conversion: ~$0.0005-0.001 per image
- No charges when idle

**ECR:**
- Storage: ~$0.10 per GB/month
- Image size: ~2-3 GB per Lambda

**API Gateway:**
- REST API: $3.50 per million requests
- HTTP API: $1.00 per million requests

## Frontend Deployment

### Deploy Frontend to S3/CloudFront

```bash
# 1. Setup S3 bucket
./infrastructure/scripts/setup-s3-bucket.sh

# 2. Deploy frontend
./infrastructure/scripts/deploy-frontend.sh

# 3. Setup CloudFront (manual or Terraform)
./infrastructure/scripts/setup-cloudfront.sh
```

### Individual Steps

```bash
# Build frontend
./infrastructure/scripts/build-frontend.sh

# Setup S3 bucket
./infrastructure/scripts/setup-s3-bucket.sh

# Deploy to S3
./infrastructure/scripts/deploy-frontend.sh
```

## Frontend Scripts

### `build-frontend.sh`
Builds React application for production.

### `setup-s3-bucket.sh`
Creates S3 bucket, enables static website hosting, and applies bucket policy.

### `deploy-frontend.sh`
Builds and deploys frontend to S3 bucket.

### `setup-cloudfront.sh`
Provides guidance for setting up CloudFront distribution.

## Frontend Configuration

### Environment Variables

- `VITE_API_URL`: API Gateway URL for production
- See `frontend/.env.production.example` for template

### S3 Bucket Configuration

- Bucket Name: `room-reader-frontend-{account-id}` (configurable via `S3_BUCKET_NAME`)
- Static Website Hosting: Enabled
- Public Read Access: Enabled via bucket policy

## Next Steps

1. Set up API Gateway (see `setup-api-gateway.sh`)
2. Deploy frontend to S3/CloudFront
3. Configure CORS for frontend access
4. Set up CloudWatch alarms
5. Configure auto-scaling if needed
6. Set up CI/CD pipeline

