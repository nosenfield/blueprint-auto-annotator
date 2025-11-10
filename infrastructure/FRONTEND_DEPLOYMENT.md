# Frontend Deployment Guide

This guide walks you through deploying the Room Reader frontend to AWS S3 and CloudFront.

## Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   aws --version
   aws configure
   ```

2. **Node.js and npm** installed
   ```bash
   node --version
   npm --version
   ```

3. **Frontend built** (or use deployment script)

## Quick Start

### Deploy Frontend to S3

```bash
# 1. Setup S3 bucket
./infrastructure/scripts/setup-s3-bucket.sh

# 2. Deploy frontend
./infrastructure/scripts/deploy-frontend.sh
```

This will:
1. Build the frontend for production
2. Create S3 bucket (if needed)
3. Enable static website hosting
4. Upload build files to S3
5. Configure public access

## Step-by-Step Guide

### Step 1: Build Frontend

```bash
./infrastructure/scripts/build-frontend.sh
```

This script:
- Installs npm dependencies
- Builds React app for production
- Outputs to `frontend/dist/` directory

**Manual build:**
```bash
cd frontend
npm install
npm run build
```

### Step 2: Setup S3 Bucket

```bash
./infrastructure/scripts/setup-s3-bucket.sh
```

This script:
- Creates S3 bucket (if doesn't exist)
- Enables static website hosting
- Applies bucket policy for public read access
- Configures public access settings

**Bucket Name:** `room-reader-frontend-{account-id}` (configurable via `S3_BUCKET_NAME`)

**Manual setup:**
```bash
# Create bucket
aws s3 mb s3://room-reader-frontend-{account-id} --region us-east-1

# Enable static website hosting
aws s3 website s3://room-reader-frontend-{account-id} \
  --index-document index.html \
  --error-document index.html

# Apply bucket policy
aws s3api put-bucket-policy \
  --bucket room-reader-frontend-{account-id} \
  --policy file://infrastructure/config/bucket-policy.json
```

### Step 3: Deploy to S3

```bash
./infrastructure/scripts/deploy-frontend.sh
```

This script:
- Builds frontend (if not already built)
- Uploads files to S3
- Sets appropriate cache headers
- Deletes old files

**Manual deployment:**
```bash
cd frontend
aws s3 sync dist/ s3://room-reader-frontend-{account-id}/ \
  --delete \
  --cache-control "public, max-age=31536000, immutable"
```

### Step 4: Setup CloudFront (Optional but Recommended)

CloudFront provides:
- HTTPS/SSL certificate
- Global CDN distribution
- Better performance
- Custom domain support

**Via AWS Console:**
1. Go to CloudFront in AWS Console
2. Create Distribution
3. Origin: S3 bucket website endpoint
4. Default Root Object: `index.html`
5. Viewer Protocol Policy: Redirect HTTP to HTTPS
6. Error Pages: 404 → `/index.html` (200 status)

**Via Terraform:**
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

**Via Script (Guidance):**
```bash
./infrastructure/scripts/setup-cloudfront.sh
```

## Configuration

### Environment Variables

**Production Environment:**
```bash
# Copy template
cp frontend/.env.production.example frontend/.env.production

# Edit with your API Gateway URL
VITE_API_URL=https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod
```

**Build with production environment:**
```bash
cd frontend
npm run build
```

### S3 Bucket Name

Default: `room-reader-frontend-{account-id}`

Override:
```bash
export S3_BUCKET_NAME=my-custom-bucket-name
./infrastructure/scripts/setup-s3-bucket.sh
```

### AWS Region

Default: `us-east-1`

Override:
```bash
export AWS_REGION=us-west-2
./infrastructure/scripts/setup-s3-bucket.sh
```

## Accessing Your Site

### S3 Website URL
```
http://room-reader-frontend-{account-id}.s3-website-us-east-1.amazonaws.com
```

### CloudFront URL (after setup)
```
https://d1234567890.cloudfront.net
```

## Testing

### Test S3 Website
```bash
# Get website URL
aws s3api get-bucket-website \
  --bucket room-reader-frontend-{account-id}

# Open in browser
open http://room-reader-frontend-{account-id}.s3-website-us-east-1.amazonaws.com
```

### Test CloudFront
```bash
# Get distribution URL
aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?DomainName=='room-reader-frontend-{account-id}.s3-website-us-east-1.amazonaws.com']].DomainName" \
  --output text

# Open in browser
open https://d1234567890.cloudfront.net
```

## Troubleshooting

### Build Fails
- Check Node.js version (should be 18+)
- Check npm dependencies: `cd frontend && npm install`
- Check for TypeScript errors: `npm run build`

### S3 Upload Fails
- Verify AWS credentials: `aws sts get-caller-identity`
- Check bucket exists: `aws s3 ls s3://bucket-name`
- Check IAM permissions (S3 write access)

### Site Not Accessible
- Check bucket policy is applied
- Check public access settings
- Verify static website hosting is enabled
- Check CloudFront distribution status (if using)

### CORS Issues
- Verify API Gateway CORS is configured
- Check frontend API URL is correct
- Verify CloudFront allows OPTIONS requests

## Cost Estimates

**S3:**
- Storage: ~$0.023 per GB/month
- Requests: ~$0.0004 per 1,000 GET requests
- Frontend size: ~1-5 MB

**CloudFront:**
- Data Transfer: ~$0.085 per GB (first 10 TB)
- Requests: ~$0.0075 per 10,000 HTTPS requests
- Free tier: 1 TB transfer/month

**Estimated Monthly Cost (1000 users, 5MB site):**
- S3: ~$0.10/month
- CloudFront: ~$0.50-2.00/month
- Total: ~$0.60-2.10/month

## Security Considerations

1. **Bucket Policy**: Only allows GetObject (read-only)
2. **HTTPS**: Use CloudFront for HTTPS/SSL
3. **API Keys**: Never commit API keys to repository
4. **Environment Variables**: Use `.env.production` for production config
5. **CORS**: Configure API Gateway CORS properly

## Next Steps

1. Set up custom domain (optional)
2. Configure CloudFront caching
3. Set up monitoring and alerts
4. Configure CI/CD for automatic deployments
5. Set up CloudWatch alarms

