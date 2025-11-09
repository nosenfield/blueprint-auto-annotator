# Room Boundary Detection System - Project Setup

**Status**: ✅ Project Structure Ready
**Date**: 2025-11-09
**Phase**: Setup Complete - Ready for Phase 1 Development

---

## Project Overview

Automated room boundary detection system using YOLO for wall detection and geometric algorithms for room polygon extraction. Serverless architecture on AWS Lambda with React frontend.

**Key Features:**
- YOLO-based wall detection (<2s)
- Geometric room boundary conversion (<1s)
- Web-based upload interface
- JSON + visualization export
- Serverless AWS deployment

---

## Directory Structure

```
room-reader/
├── backend/
│   ├── lambda-wall-detection/        # YOLO wall detection Lambda
│   │   ├── app/                      # Application code
│   │   │   └── __init__.py
│   │   ├── models/                   # YOLO model weights (download separately)
│   │   │   └── .gitkeep
│   │   ├── tests/                    # Unit tests
│   │   ├── Dockerfile                # Lambda container image
│   │   ├── .dockerignore
│   │   └── requirements.txt          # Python dependencies
│   │
│   └── lambda-room-detection/        # Geometric room detection Lambda
│       ├── app/                      # Application code
│       │   └── __init__.py
│       ├── tests/                    # Unit tests
│       ├── Dockerfile                # Lambda container image
│       ├── .dockerignore
│       └── requirements.txt          # Python dependencies
│
├── frontend/                         # React web application
│   ├── src/
│   │   ├── components/              # React components
│   │   ├── services/                # API client
│   │   ├── types/                   # TypeScript types
│   │   └── contexts/                # React contexts
│   └── public/                      # Static assets
│
├── infrastructure/
│   ├── terraform/                   # Infrastructure as Code
│   │   └── variables.tf
│   ├── scripts/                     # Deployment scripts
│   │   └── push-to-ecr.sh          # Push Docker images to AWS ECR
│   └── trust-policy.json           # IAM trust policy
│
├── tests/
│   ├── fixtures/                    # Test data
│   └── data/                        # Sample blueprints
│
├── memory-bank/                     # AI project context (Memory Bank system)
│   ├── projectbrief.md             # Project overview and scope
│   ├── activeContext.md            # Current work context
│   ├── progress.md                 # Task tracking
│   ├── productContext.md           # Product vision and UX
│   ├── techContext.md              # Technical architecture
│   └── systemPatterns.md           # Coding standards
│
├── _docs/                          # Project documentation
│   ├── architecture.md             # System architecture
│   ├── task-list.md               # Detailed implementation tasks
│   └── guides/                    # Workflow guides
│
├── .cursor/                        # Cursor IDE configuration
│   ├── commands/                  # Slash commands
│   └── rules/                     # AI behavior rules
│
├── scripts/                        # Project automation scripts
│
├── .gitignore                      # Git ignore patterns
└── README.md                       # Project README
```

---

## Quick Start

### 1. Prerequisites

```bash
# Required
- Python 3.11+
- Node.js 18+
- Docker Desktop
- AWS CLI configured
- Git

# Optional
- Terraform (for infrastructure)
- YOLO model weights (yolov8l.pt)
```

### 2. Backend Setup (Local Development)

```bash
# Navigate to room detection Lambda
cd backend/lambda-room-detection

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run local server (after implementing main.py)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test endpoint
curl http://localhost:8000/
```

### 3. Frontend Setup (When Ready)

```bash
# Navigate to frontend
cd frontend

# Initialize React project (Phase 4)
npm create vite@latest . -- --template react-ts
npm install

# Install additional dependencies
npm install axios react-dropzone tailwindcss postcss autoprefixer

# Run development server
npm run dev
```

### 4. Docker Testing

```bash
# Build room detection image
cd backend/lambda-room-detection
docker build -t room-detection:latest .

# Run locally
docker run -p 9000:8080 room-detection:latest

# Test with Lambda runtime interface
curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
  -d @test-event.json
```

---

## Development Workflow

### Starting a Development Session

```bash
# Option 1: Use Cursor slash command
/begin-development

# Option 2: Manually review Memory Bank
Read memory-bank/activeContext.md
Read memory-bank/progress.md
```

### Test-First Development

1. Write tests first (see `systemPatterns.md` for patterns)
2. Implement functionality
3. Run tests
4. Refactor
5. Update Memory Bank files

### Memory Bank Updates

After completing work:
```bash
# Update active context
memory-bank/activeContext.md - Current focus, decisions, next steps

# Update progress
memory-bank/progress.md - Completed tasks, blockers, metrics

# Use slash command (optional)
/update-memory-bank
```

---

## Next Steps - Phase 1: Local Development

### 1. Implement Room Detection Lambda

Files to create:
- `backend/lambda-room-detection/app/models.py` - Pydantic models
- `backend/lambda-room-detection/app/geometric.py` - Room detection algorithm
- `backend/lambda-room-detection/app/visualization.py` - Image generation
- `backend/lambda-room-detection/app/main.py` - FastAPI application

### 2. Download YOLO Model

```bash
# Download YOLOv8 Large model
cd backend/lambda-wall-detection/models
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8l.pt
```

### 3. Create Test Data

- Add sample blueprint images to `tests/fixtures/`
- Create test wall detection responses
- Prepare test events for Lambda

### 4. Local Testing

```bash
# Create test script
backend/lambda-room-detection/test_local.py

# Run tests
python test_local.py
```

---

## Deployment Guide

### Prerequisites

1. AWS Account configured
2. ECR repositories created
3. IAM roles created
4. API Gateway configured

### Deploy Backend

```bash
# Set environment variables
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1

# Push images to ECR
./infrastructure/scripts/push-to-ecr.sh

# Update Lambda functions (manual or via Terraform)
aws lambda update-function-code \
  --function-name room-detection \
  --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/room-detection:latest
```

### Deploy Frontend

```bash
# Build React app
cd frontend
npm run build

# Deploy to S3
aws s3 sync dist/ s3://room-detection-frontend/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

---

## Environment Variables

### Backend (Lambda)

```bash
LOG_LEVEL=INFO
MODEL_PATH=/var/task/models/yolov8l.pt
```

### Frontend (React)

Create `.env.local`:
```bash
VITE_API_URL=http://localhost:8000  # Development
# VITE_API_URL=https://api.yourdomain.com/prod  # Production
```

---

## Key Resources

### Documentation
- Architecture: `_docs/architecture.md`
- Task List: `_docs/task-list.md`
- Memory Bank: `memory-bank/README.md`

### Memory Bank Files (Read These First!)
- `memory-bank/projectbrief.md` - What we're building
- `memory-bank/activeContext.md` - Current work focus
- `memory-bank/progress.md` - Task status
- `memory-bank/techContext.md` - Technical details
- `memory-bank/systemPatterns.md` - Coding standards

### Cursor Commands
- `/begin-development` - Start session with Memory Bank loaded
- `/start-task [id]` - Begin specific task with context
- `/implement [id]` - Execute approved implementation plan
- `/update-memory-bank` - Review and update Memory Bank

---

## Troubleshooting

### Docker Build Fails
```bash
# Check Dockerfile syntax
docker build --no-cache -t test .

# Verify base image
docker pull public.ecr.aws/lambda/python:3.11
```

### Lambda Cold Starts
- Container images have 3-5s cold start
- Use provisioned concurrency for production
- Optimize image size with multi-stage builds

### YOLO Model Not Found
```bash
# Verify model location
ls -lh backend/lambda-wall-detection/models/

# Download if missing
wget -P backend/lambda-wall-detection/models/ \
  https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8l.pt
```

---

## Project Timeline

- **Phase 1**: Local Development (2 days) - Days 1-2
- **Phase 2**: Dockerization (1 day) - Day 3
- **Phase 3**: AWS Infrastructure (1 day) - Day 4
- **Phase 4**: Frontend Development (3 days) - Days 5-7
- **Phase 5**: Deployment (1 day) - Day 8
- **Phase 6**: CI/CD (1 day) - Day 9
- **Phase 7**: Testing & Launch (2 days) - Days 10-11

**Total**: 11 days to MVP

---

## Support

### Memory Bank Management
See `.cursor/rules/memory-bank-management.mdc` for complete procedures.

### Multi-Agent Workflow
See `_docs/guides/multi-agent-workflow.md` for parallel development patterns.

### Test-First Workflow
See `_docs/guides/test-first-workflow.md` for TDD procedures.

---

## Status

- ✅ Project structure created
- ✅ Memory Bank initialized
- ✅ Dockerfiles ready
- ✅ Infrastructure scripts prepared
- ⏳ Backend implementation (Phase 1)
- ⏳ Frontend implementation (Phase 4)
- ⏳ AWS deployment (Phase 5)
- ⏳ CI/CD setup (Phase 6)

**Current Phase**: Ready to begin Phase 1 - Local Development

**Next Task**: Implement `backend/lambda-room-detection/app/models.py`
