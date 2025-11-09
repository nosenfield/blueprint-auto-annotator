# Technical Context: Room Boundary Detection System

**Last Updated**: 2025-11-09

## Technology Stack

### Backend Stack
```yaml
Language: Python 3.11
Framework: FastAPI 0.104+
Web Server: Uvicorn (ASGI)
Runtime: AWS Lambda (Container Image)
Container: Docker (AWS Lambda base image)

Core Libraries:
  - fastapi: REST API framework with auto-validation
  - uvicorn: ASGI server for FastAPI
  - mangum: Adapter for running ASGI apps on Lambda
  - opencv-python-headless: Image processing and computer vision
  - numpy: Numerical operations and array manipulation
  - ultralytics: YOLO model implementation
  - pydantic: Data validation and settings management
  - pillow: Image manipulation and encoding
```

### Frontend Stack
```yaml
Language: TypeScript 5+
Framework: React 18
Build Tool: Vite (fast builds, HMR)
State Management: React Hooks + Context API
Styling: Tailwind CSS (utility-first)
HTTP Client: Axios

Key Libraries:
  - react: UI library with hooks
  - react-router-dom: Client-side routing (future)
  - axios: HTTP client with interceptors
  - react-dropzone: Drag-and-drop file uploads
  - tailwindcss: Utility-first CSS framework
```

### Infrastructure Stack
```yaml
Compute:
  - AWS Lambda (Container Images)
  - API Gateway (REST API)

Storage:
  - S3 (Static website hosting)
  - ECR (Docker container registry)

CDN:
  - CloudFront (Global CDN, HTTPS)

CI/CD:
  - GitHub Actions (Build & deploy automation)

Monitoring:
  - CloudWatch Logs (Application logs)
  - CloudWatch Metrics (Performance metrics)
```

---

## Architecture Patterns

### Microservices Pattern
- **Wall Detection Lambda**: Independent service for YOLO-based wall detection
- **Room Detection Lambda**: Independent service for geometric room conversion
- **API Gateway**: Unified REST API facade
- **Benefit**: Independent scaling, deployment, and testing

### Serverless Pattern
- **Event-driven**: Lambda functions invoked by API Gateway
- **Stateless**: No persistent connections or sessions
- **Auto-scaling**: AWS manages scaling based on load
- **Pay-per-use**: Only charged for actual execution time

### JAMstack Pattern (Frontend)
- **JavaScript**: React app for dynamic UI
- **APIs**: Backend Lambda functions via API Gateway
- **Markup**: Pre-built HTML served from S3/CloudFront
- **Benefit**: Fast, secure, scalable static hosting

---

## Data Flow Architecture

### Request Pipeline
```
1. User uploads blueprint image
   ↓
2. React app converts to base64
   ↓
3. POST /api/detect-walls
   ↓
4. API Gateway → Wall Detection Lambda
   ↓
5. YOLO model processes image
   ↓
6. Returns wall coordinates
   ↓
7. React app sends walls to POST /api/detect-rooms
   ↓
8. API Gateway → Room Detection Lambda
   ↓
9. Geometric algorithm processes walls
   ↓
10. Returns room polygons + visualization
    ↓
11. React displays results
```

### Data Formats

**Wall Detection Input:**
```json
{
  "image": "base64_encoded_string",
  "confidence_threshold": 0.10,
  "image_format": "png"
}
```

**Wall Detection Output:**
```json
{
  "success": true,
  "walls": [
    {
      "id": "wall_001",
      "bounding_box": [x1, y1, x2, y2],
      "confidence": 0.85
    }
  ],
  "total_walls": 34,
  "image_dimensions": [width, height],
  "processing_time_ms": 35
}
```

**Room Detection Output:**
```json
{
  "success": true,
  "rooms": [
    {
      "id": "room_001",
      "polygon_vertices": [[x1,y1], [x2,y2], ...],
      "area_pixels": 40000,
      "confidence": 0.92,
      "shape_type": "rectangle"
    }
  ],
  "visualization": "base64_encoded_image",
  "total_rooms": 7,
  "processing_time_ms": 50
}
```

---

## Key Algorithms

### 1. YOLO Wall Detection
```
Algorithm: YOLOv8 Large (yolov8l)
Purpose: Detect wall bounding boxes in blueprint images
Steps:
  1. Load YOLO model weights
  2. Preprocess image (resize, normalize)
  3. Run inference
  4. Apply Non-Maximum Suppression (NMS)
  5. Filter by confidence threshold
  6. Return bounding boxes

Performance:
  - Inference time: ~1-2 seconds
  - Memory: ~8-10 GB
  - Accuracy: ~85-90% on blueprints
```

### 2. Geometric Room Detection
```
Algorithm: Connected Components + Morphological Operations
Purpose: Convert wall bounding boxes to room polygons
Steps:
  1. Create binary grid (image dimensions)
  2. Draw walls as filled rectangles on grid
  3. Invert grid (walls=black, rooms=white)
  4. Apply morphological closing (fill gaps in walls)
  5. Apply morphological opening (remove noise)
  6. Find connected components (rooms)
  7. Extract contours for each component
  8. Simplify polygons (Douglas-Peucker algorithm)
  9. Filter by minimum area threshold
  10. Return room polygons

Performance:
  - Processing time: ~50-200ms
  - Memory: ~1-2 GB
  - Accuracy: ~90-95% for simple layouts
```

### 3. Polygon Simplification
```
Algorithm: Douglas-Peucker (Ramer-Douglas-Peucker)
Purpose: Reduce polygon vertices while preserving shape
Parameter: epsilon = 0.01 * perimeter
Effect: Converts complex contours to simple polygons
  - Rectangle: 4 vertices
  - L-shape: 5-6 vertices
  - Complex: <20 vertices
```

---

## Performance Considerations

### Lambda Configuration
```yaml
Wall Detection Lambda:
  Memory: 10240 MB (10 GB for YOLO)
  Timeout: 30 seconds
  Reserved Concurrency: 10 (MVP)
  Provisioned Concurrency: 0 (cost optimization)

Room Detection Lambda:
  Memory: 3008 MB (3 GB for OpenCV)
  Timeout: 30 seconds
  Reserved Concurrency: 10 (MVP)
  Provisioned Concurrency: 0
```

### Cold Start Mitigation
- Container image optimization (Alpine base)
- Model pre-loading in global scope
- Keep-warm strategy (future: scheduled CloudWatch events)
- Provisioned concurrency for production (future)

### Cost Optimization
```
MVP (1000 requests/month):
  - Lambda compute: ~$0.04
  - API Gateway: ~$0.007
  - CloudFront: ~$0.086
  - S3: ~$0.002
  - ECR: ~$0.20
  Total: ~$0.34/month

Production (10,000 requests/month):
  Total: ~$1.64/month
```

---

## Security Architecture

### API Security
- HTTPS-only (CloudFront, API Gateway)
- CORS configuration (specific origins in production)
- No authentication in MVP (public access)
- Rate limiting via API Gateway (future)
- Request size limits (10 MB max)

### Data Security
- No persistent storage (ephemeral processing)
- No PII collection
- No user tracking
- Lambda execution role (least privilege)
- Environment variable encryption

### Container Security
- Official AWS Lambda base images
- No secrets in images
- Minimal dependencies
- Regular security updates

---

## Error Handling Strategy

### Backend Error Handling
```python
try:
    # Process request
    result = detect_rooms(walls, dimensions)
    return {"success": True, "rooms": result}
except ValidationError as e:
    # Pydantic validation errors
    raise HTTPException(400, detail={"error": "Invalid input", "details": e.errors()})
except ProcessingError as e:
    # Algorithm failures
    raise HTTPException(500, detail={"error": "Processing failed", "message": str(e)})
except Exception as e:
    # Unexpected errors
    logger.error(f"Unexpected error: {str(e)}")
    raise HTTPException(500, detail={"error": "Internal server error"})
```

### Frontend Error Handling
```typescript
try {
  const result = await api.detectWalls(file);
  setWallsData(result);
} catch (error) {
  if (axios.isAxiosError(error)) {
    // Network or API errors
    setError(error.response?.data?.error || "API request failed");
  } else {
    // Unexpected errors
    setError("An unexpected error occurred");
  }
  console.error("Detection error:", error);
}
```

---

## Development Environment

### Local Development Setup
```bash
# Backend
cd backend/lambda-room-detection
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Docker Testing
```bash
# Build image
docker build -t room-detection:latest .

# Run locally
docker run -p 9000:8080 room-detection:latest

# Test with curl
curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
  -d @test-event.json
```

### Environment Variables
```bash
# Backend (Lambda)
LOG_LEVEL=INFO
MODEL_PATH=/var/task/models/yolov8l.pt

# Frontend (React)
VITE_API_URL=https://api.example.com/prod
```

---

## Testing Strategy

### Backend Testing
```yaml
Unit Tests:
  - Pydantic model validation
  - Geometric algorithm functions
  - Utility functions
  - Coverage target: >80%

Integration Tests:
  - FastAPI endpoints
  - Lambda handler
  - Error scenarios

Performance Tests:
  - Execution time benchmarks
  - Memory usage profiling
  - Cold start measurement
```

### Frontend Testing
```yaml
Unit Tests:
  - React components
  - API client functions
  - Utility functions

Integration Tests:
  - User workflows
  - API mocking
  - Error states

E2E Tests (future):
  - Cypress or Playwright
  - Full upload-to-download flow
```

---

## Deployment Process

### CI/CD Pipeline (GitHub Actions)
```yaml
Triggers:
  - Push to main branch
  - Manual workflow dispatch

Backend Pipeline:
  1. Checkout code
  2. Configure AWS credentials
  3. Login to ECR
  4. Build Docker images
  5. Push to ECR
  6. Update Lambda functions

Frontend Pipeline:
  1. Checkout code
  2. Install Node.js
  3. Install dependencies
  4. Build React app
  5. Deploy to S3
  6. Invalidate CloudFront cache
```

### Deployment Stages
```
Development → Staging → Production

Development:
  - Local testing only
  - FastAPI dev server
  - Vite dev server

Staging:
  - AWS Lambda (separate functions)
  - Separate S3 bucket
  - Testing environment

Production:
  - AWS Lambda (production functions)
  - Production S3 bucket
  - CloudFront distribution
```

---

## Monitoring & Observability

### Logging
```yaml
Application Logs:
  - Structured JSON logging
  - CloudWatch Log Groups
  - Retention: 7 days (MVP)

Log Levels:
  - ERROR: Failures, exceptions
  - WARN: Recoverable issues
  - INFO: Request/response, processing time
  - DEBUG: Detailed execution flow (dev only)
```

### Metrics
```yaml
Lambda Metrics:
  - Invocations
  - Duration (p50, p95, p99)
  - Errors
  - Throttles
  - Concurrent executions

API Gateway Metrics:
  - Request count
  - Latency
  - 4xx errors
  - 5xx errors

Custom Metrics:
  - Walls detected per request
  - Rooms detected per request
  - Processing time breakdown
```

### Alarms (Future)
```yaml
- Error rate > 5%
- API latency > 5 seconds
- Lambda throttles > 10
```

---

## Technical Debt & Future Improvements

### Known Limitations
1. **Cold starts**: 3-5 seconds for container images
2. **Image size limit**: 10 MB max (API Gateway limit)
3. **Synchronous processing**: Blocks user during processing
4. **No caching**: Re-processes identical blueprints

### Future Technical Improvements
1. **Async processing**: SQS + WebSocket for long-running jobs
2. **Model optimization**: Quantization, pruning for smaller/faster YOLO
3. **Caching layer**: Redis/ElastiCache for repeated blueprints
4. **Batch processing**: Step Functions for multiple blueprints
5. **Custom model training**: Fine-tune YOLO on specific blueprint types
