# Quick Reference - Room Boundary Detection System

## 🎯 Project Overview

**Objective:** Automated room boundary detection from architectural blueprints  
**Stack:** Python FastAPI + React TypeScript + AWS Lambda  
**Deployment:** Serverless architecture via GitHub Actions

---

## 📁 Repository Structure

```
room-boundary-detection/
├── backend/
│   ├── lambda-wall-detection/      # YOLO wall detection
│   └── lambda-room-detection/      # Geometric room conversion
├── frontend/                        # React TypeScript SPA
├── infrastructure/                  # AWS deployment scripts
├── .github/workflows/              # CI/CD pipelines
└── _docs/                           # Documentation
```

---

## 🚀 Quick Start Commands

### Local Development

```bash
# Backend (Room Detection)
cd backend/lambda-room-detection
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker Build
docker build -t room-detection .
docker run -p 9000:8080 room-detection
```

### Deployment

```bash
# Push to ECR
./infrastructure/scripts/push-to-ecr.sh

# Deploy Frontend
cd frontend && npm run build
aws s3 sync dist/ s3://room-detection-frontend/
```

---

## 🔌 API Endpoints

### 1. Wall Detection
```
POST /api/detect-walls
Input: {image: base64, confidence_threshold: 0.10}
Output: {walls: [...], total_walls: 34}
```

### 2. Room Detection
```
POST /api/detect-rooms
Input: {walls: [...], image_dimensions: [w,h]}
Output: {rooms: [...], visualization: base64}
```

---

## 🏗️ Core Components

### Backend: Room Detection Lambda

**File:** `backend/lambda-room-detection/app/main.py`

Key functions:
- `detect_rooms()` - Main API endpoint
- `GeometricRoomDetector.detect_rooms()` - Core algorithm
- `RoomVisualizer.create_visualization()` - Image generation

**Algorithm Steps:**
1. Create binary grid
2. Draw walls
3. Invert (rooms = white)
4. Morphological operations
5. Connected components
6. Extract polygons

### Frontend: React Application

**File:** `frontend/src/App.tsx`

Key components:
- `FileUpload` - Drag-and-drop interface
- `ProcessingStatus` - Progress tracking
- `ResultsDisplay` - Visualization + JSON

**User Flow:**
1. Upload blueprint
2. Detect walls (YOLO)
3. Detect rooms (Geometric)
4. Display results
5. Download outputs

---

## 📊 Data Models

### Wall
```typescript
{
  id: string;
  bounding_box: [x1, y1, x2, y2];
  confidence: number;
}
```

### Room
```typescript
{
  id: string;
  polygon_vertices: [[x,y], ...];
  bounding_box: {x_min, y_min, x_max, y_max};
  area_pixels: number;
  confidence: number;
  shape_type: "rectangle" | "l_shape" | "complex";
}
```

---

## 🔧 Configuration

### Environment Variables

**Backend:**
```
# No environment variables needed for MVP
```

**Frontend:**
```
VITE_API_URL=https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod
```

### Lambda Configuration

**Room Detection:**
```yaml
Memory: 3008 MB
Timeout: 30 seconds
Handler: app.main.handler
```

**Wall Detection:**
```yaml
Memory: 10240 MB
Timeout: 30 seconds
Handler: app.main.handler
```

---

## 📈 Performance Targets

```yaml
Wall Detection: <2 seconds
Room Detection: <1 second
Total Pipeline: <5 seconds
Cost per Request: $0.001
```

---

## 🧪 Testing

### Test Locally

```bash
# Backend
cd backend/lambda-room-detection
python test_local.py

# Frontend
cd frontend
npm run test
```

### Test Production

```bash
# API
curl -X POST https://api-url/prod/api/detect-walls \
  -H "Content-Type: application/json" \
  -d @test-data.json

# Frontend
curl https://cloudfront-url
```

---

## 🚨 Common Issues & Solutions

### Issue: Lambda cold start timeout
**Solution:** Increase timeout to 30s, or use provisioned concurrency

### Issue: Image too large
**Solution:** Compress image before upload, or increase Lambda memory

### Issue: CORS errors
**Solution:** Verify API Gateway CORS configuration

### Issue: Build fails
**Solution:** Check Node/Python versions match requirements

---

## 📚 Key Documentation

- [architecture-v2.md](./architecture-v2.md) - System design & diagrams (revised architecture)
- [task-list-v2.md](./task-list-v2.md) - Step-by-step implementation (revised task list)
- [API Reference](https://api-url/docs) - FastAPI auto-generated docs

---

## 🎯 Implementation Checklist

### MVP (Week 1-2)
- [ ] Room detection Lambda implemented
- [ ] React frontend built
- [ ] Basic deployment to AWS
- [ ] End-to-end testing complete

### Production (Week 3-4)
- [ ] CI/CD pipeline configured
- [ ] CloudFront setup
- [ ] Monitoring & logging
- [ ] Performance optimization

### Future Enhancements
- [ ] Async processing (SQS + Step Functions)
- [ ] Batch uploads
- [ ] User authentication
- [ ] Processing history

---

## 💡 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| FastAPI | Type-safe, async, auto-docs |
| React + TypeScript | Industry standard, type safety |
| Lambda Containers | 10GB limit for YOLO model |
| Synchronous API | Simpler for MVP |
| No storage | Stateless, cheaper |
| Geometric Algorithm | Fast, free, deterministic |

---

## 🔗 Useful Links

```yaml
AWS Console: https://console.aws.amazon.com
ECR: https://console.aws.amazon.com/ecr
Lambda: https://console.aws.amazon.com/lambda
API Gateway: https://console.aws.amazon.com/apigateway
S3: https://console.aws.amazon.com/s3
CloudFront: https://console.aws.amazon.com/cloudfront
```

---

## 📞 Support & Resources

**Documentation:**
- FastAPI: https://fastapi.tiangolo.com
- React: https://react.dev
- AWS Lambda: https://docs.aws.amazon.com/lambda

**Community:**
- GitHub Issues
- Stack Overflow

---

## 🎓 For AI Agents

**When implementing this system:**

1. **Read architecture-v2.md first** - Understand system design (revised architecture)
2. **Follow task-list-v2.md sequentially** - Each task builds on previous (revised task list)
3. **Use provided code samples** - Copy/paste ready
4. **Test incrementally** - Validate each phase before proceeding
5. **Refer to this document** - Quick command reference

**Key files to implement:**
```
backend/lambda-room-detection/app/main.py          # FastAPI app
backend/lambda-room-detection/app/geometric.py     # Core algorithm
backend/lambda-room-detection/app/visualization.py # Image generation
frontend/src/App.tsx                                # Main app
frontend/src/services/api.ts                        # API client
.github/workflows/deploy.yml                        # CI/CD
```

**Deployment order:**
1. Build Docker images locally
2. Push to ECR
3. Create Lambda functions
4. Configure API Gateway
5. Build React app
6. Deploy to S3
7. Setup CloudFront (optional)
8. Configure GitHub Actions

**Validation steps:**
1. Test endpoints locally
2. Test Lambda functions via console
3. Test API Gateway endpoints
4. Test frontend locally with production API
5. Test deployed frontend
6. Verify CI/CD pipeline

---

**System is ready for production deployment following this documentation.** 🚀
