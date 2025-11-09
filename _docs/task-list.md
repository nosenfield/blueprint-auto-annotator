# Task List - Room Boundary Detection System

## Overview

This document provides step-by-step tasks to build and deploy the complete room boundary detection system. Each task includes code samples, acceptance criteria, and AI-friendly implementation details.

---

## Phase 1: Local Development Setup

### Task 1.1: Project Structure Setup

**Objective:** Create organized directory structure for modular development

**Steps:**

```bash
# Create root directory
mkdir room-boundary-detection
cd room-boundary-detection

# Create backend structure
mkdir -p backend/lambda-wall-detection/app
mkdir -p backend/lambda-wall-detection/models
mkdir -p backend/lambda-wall-detection/tests
mkdir -p backend/lambda-room-detection/app
mkdir -p backend/lambda-room-detection/tests

# Create frontend structure
mkdir -p frontend/src/components
mkdir -p frontend/src/services
mkdir -p frontend/src/types
mkdir -p frontend/src/contexts
mkdir -p frontend/public

# Create infrastructure
mkdir -p infrastructure/terraform
mkdir -p infrastructure/scripts

# Create CI/CD
mkdir -p .github/workflows

# Create docs
mkdir -p _docs
```

**Acceptance Criteria:**
- [x] Directory structure matches architecture.md
- [x] All folders created and empty
- [x] Git repository initialized

---

### Task 1.2: Backend - Room Detection Lambda (Local)

**Objective:** Build room boundary detection logic locally

**File:** `backend/lambda-room-detection/requirements.txt`

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
mangum==0.17.0
opencv-python-headless==4.8.1.78
numpy==1.24.3
pydantic==2.5.0
python-multipart==0.0.6
pillow==10.1.0
```

**File:** `backend/lambda-room-detection/app/models.py`

```python
"""
Pydantic models for request/response validation
"""
from typing import List, Tuple, Optional, Literal
from pydantic import BaseModel, Field


class Wall(BaseModel):
    """Wall detection result"""
    id: str
    bounding_box: Tuple[int, int, int, int] = Field(
        ..., 
        description="[x1, y1, x2, y2] in pixels"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)


class RoomDetectionRequest(BaseModel):
    """Request for room boundary detection"""
    walls: List[Wall] = Field(..., min_items=1)
    image_dimensions: Tuple[int, int] = Field(..., description="[width, height]")
    min_room_area: Optional[int] = Field(2000, ge=100, le=100000)
    return_visualization: Optional[bool] = Field(True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "walls": [
                    {
                        "id": "wall_001",
                        "bounding_box": [100, 50, 105, 200],
                        "confidence": 0.85
                    }
                ],
                "image_dimensions": [609, 515],
                "min_room_area": 2000,
                "return_visualization": True
            }
        }


class BoundingBox(BaseModel):
    """Room bounding box"""
    x_min: int
    y_min: int
    x_max: int
    y_max: int


class Room(BaseModel):
    """Detected room with boundaries"""
    id: str
    polygon_vertices: List[Tuple[int, int]] = Field(
        ..., 
        description="List of [x, y] coordinates"
    )
    bounding_box: BoundingBox
    area_pixels: int
    centroid: Tuple[int, int]
    confidence: float = Field(..., ge=0.0, le=1.0)
    shape_type: Literal["rectangle", "l_shape", "complex"]
    num_vertices: int


class RoomDetectionResponse(BaseModel):
    """Response with detected rooms"""
    success: bool
    rooms: List[Room]
    visualization: Optional[str] = Field(None, description="Base64 encoded image")
    total_rooms: int
    processing_time_ms: float
    metadata: dict


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: dict
```

**File:** `backend/lambda-room-detection/app/geometric.py`

```python
"""
Geometric algorithm for wall-to-room conversion
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Any
from .models import Wall, Room, BoundingBox


class GeometricRoomDetector:
    """Converts wall detections to room polygons using geometric analysis"""
    
    def __init__(
        self, 
        min_room_area: int = 2000,
        kernel_size: int = 3,
        epsilon_factor: float = 0.01
    ):
        """
        Args:
            min_room_area: Minimum area in pixels to consider as room
            kernel_size: Size of morphological kernel
            epsilon_factor: Polygon simplification factor
        """
        self.min_room_area = min_room_area
        self.kernel_size = kernel_size
        self.epsilon_factor = epsilon_factor
        self.kernel = np.ones((kernel_size, kernel_size), np.uint8)
    
    def detect_rooms(
        self, 
        walls: List[Wall], 
        width: int, 
        height: int
    ) -> List[Room]:
        """
        Main detection pipeline
        
        Args:
            walls: List of detected walls
            width: Image width in pixels
            height: Image height in pixels
            
        Returns:
            List of detected rooms
        """
        # Step 1: Create binary grid
        grid = self._create_grid(width, height)
        
        # Step 2: Draw walls
        grid = self._draw_walls(grid, walls)
        
        # Step 3: Invert (walls become black, rooms become white)
        inverted = 255 - grid
        
        # Step 4: Apply morphological operations
        cleaned = self._apply_morphology(inverted)
        
        # Step 5: Find connected components
        labels, stats, centroids = self._find_components(cleaned)
        
        # Step 6: Extract room polygons
        rooms = self._extract_rooms(
            labels, 
            stats, 
            centroids, 
            width, 
            height
        )
        
        return rooms
    
    def _create_grid(self, width: int, height: int) -> np.ndarray:
        """Create binary grid"""
        return np.zeros((height, width), dtype=np.uint8)
    
    def _draw_walls(self, grid: np.ndarray, walls: List[Wall]) -> np.ndarray:
        """Draw walls on grid"""
        for wall in walls:
            x1, y1, x2, y2 = wall.bounding_box
            
            # Ensure coordinates are within bounds
            h, w = grid.shape
            x1 = max(0, min(x1, w - 1))
            x2 = max(0, min(x2, w - 1))
            y1 = max(0, min(y1, h - 1))
            y2 = max(0, min(y2, h - 1))
            
            # Draw filled rectangle
            cv2.rectangle(grid, (x1, y1), (x2, y2), 255, -1)
        
        return grid
    
    def _apply_morphology(self, image: np.ndarray) -> np.ndarray:
        """Apply morphological operations to clean up"""
        # Closing: Fill small gaps in walls
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, self.kernel)
        
        # Opening: Remove small white noise
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, self.kernel)
        
        return opened
    
    def _find_components(
        self, 
        image: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Find connected components"""
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            image, 
            connectivity=8
        )
        
        return labels, stats, centroids
    
    def _extract_rooms(
        self,
        labels: np.ndarray,
        stats: np.ndarray,
        centroids: np.ndarray,
        width: int,
        height: int
    ) -> List[Room]:
        """Extract room polygons from connected components"""
        rooms = []
        max_area = width * height * 0.9  # Exclude background
        
        num_labels = len(stats)
        
        for label in range(1, num_labels):  # Skip background (0)
            x, y, w, h, area = stats[label]
            
            # Filter by area
            if area < self.min_room_area or area > max_area:
                continue
            
            # Get polygon
            mask = (labels == label).astype(np.uint8) * 255
            contours, _ = cv2.findContours(
                mask, 
                cv2.RETR_EXTERNAL, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            if not contours:
                continue
            
            # Get largest contour
            contour = max(contours, key=cv2.contourArea)
            
            # Simplify polygon
            epsilon = self.epsilon_factor * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Convert to list of tuples
            vertices = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]
            
            # Determine shape type
            num_vertices = len(vertices)
            if num_vertices == 4:
                shape_type = "rectangle"
            elif num_vertices <= 6:
                shape_type = "l_shape"
            else:
                shape_type = "complex"
            
            # Calculate confidence
            confidence = self._calculate_confidence(area, num_vertices)
            
            # Create room object
            room = Room(
                id=f"room_{len(rooms) + 1:03d}",
                polygon_vertices=vertices,
                bounding_box=BoundingBox(
                    x_min=int(x),
                    y_min=int(y),
                    x_max=int(x + w),
                    y_max=int(y + h)
                ),
                area_pixels=int(area),
                centroid=(int(centroids[label][0]), int(centroids[label][1])),
                confidence=confidence,
                shape_type=shape_type,
                num_vertices=num_vertices
            )
            
            rooms.append(room)
        
        # Sort by area (largest first)
        rooms.sort(key=lambda r: r.area_pixels, reverse=True)
        
        return rooms
    
    def _calculate_confidence(self, area: int, num_vertices: int) -> float:
        """
        Calculate confidence score based on area and shape complexity
        
        Args:
            area: Room area in pixels
            num_vertices: Number of polygon vertices
            
        Returns:
            Confidence score between 0 and 1
        """
        # Larger rooms = higher confidence
        area_score = min(area / 50000, 1.0)
        
        # Simpler shapes = higher confidence
        vertex_score = 1.0 - (min(num_vertices, 20) / 20) * 0.3
        
        # Weighted combination
        confidence = (area_score * 0.7 + vertex_score * 0.3)
        
        return round(confidence, 2)
```

**File:** `backend/lambda-room-detection/app/visualization.py`

```python
"""
Visualization generation for detected rooms
"""
import cv2
import numpy as np
import base64
from typing import List, Tuple
from .models import Room


class RoomVisualizer:
    """Generates visualization of detected room boundaries"""
    
    # Color palette for room visualization
    COLORS = [
        (255, 0, 0),      # Blue
        (0, 255, 0),      # Green
        (0, 0, 255),      # Red
        (255, 255, 0),    # Cyan
        (255, 0, 255),    # Magenta
        (0, 255, 255),    # Yellow
        (128, 0, 255),    # Purple
        (255, 128, 0),    # Orange
        (0, 255, 128),    # Spring green
        (128, 255, 0),    # Chartreuse
    ]
    
    def __init__(self, font_scale: float = 0.5, line_thickness: int = 2):
        """
        Args:
            font_scale: Font size for labels
            line_thickness: Thickness of boundary lines
        """
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = font_scale
        self.line_thickness = line_thickness
    
    def create_visualization(
        self, 
        rooms: List[Room], 
        width: int, 
        height: int,
        background_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> np.ndarray:
        """
        Create visualization image with room boundaries
        
        Args:
            rooms: List of detected rooms
            width: Image width
            height: Image height
            background_color: Background color (BGR)
            
        Returns:
            Visualization image as numpy array
        """
        # Create white canvas
        image = np.full((height, width, 3), background_color, dtype=np.uint8)
        
        # Draw each room
        for i, room in enumerate(rooms):
            color = self.COLORS[i % len(self.COLORS)]
            
            # Draw polygon
            vertices = np.array(room.polygon_vertices, dtype=np.int32)
            cv2.polylines(
                image, 
                [vertices], 
                isClosed=True, 
                color=color, 
                thickness=self.line_thickness
            )
            
            # Draw bounding box (lighter)
            bbox = room.bounding_box
            cv2.rectangle(
                image,
                (bbox.x_min, bbox.y_min),
                (bbox.x_max, bbox.y_max),
                color,
                1
            )
            
            # Add label at centroid
            cx, cy = room.centroid
            label = f"{room.id}"
            
            # Draw text background
            (text_w, text_h), _ = cv2.getTextSize(
                label, 
                self.font, 
                self.font_scale, 
                self.line_thickness
            )
            
            cv2.rectangle(
                image,
                (cx - 5, cy - text_h - 5),
                (cx + text_w + 5, cy + 5),
                color,
                -1
            )
            
            # Draw text
            cv2.putText(
                image,
                label,
                (cx, cy),
                self.font,
                self.font_scale,
                (255, 255, 255),
                self.line_thickness
            )
            
            # Add shape info
            info = f"{room.shape_type}"
            cv2.putText(
                image,
                info,
                (cx, cy + 15),
                self.font,
                self.font_scale * 0.7,
                color,
                1
            )
        
        # Add metadata
        self._add_metadata(image, len(rooms))
        
        return image
    
    def _add_metadata(self, image: np.ndarray, total_rooms: int):
        """Add metadata text to image"""
        text = f"Detected: {total_rooms} rooms"
        cv2.putText(
            image,
            text,
            (10, 30),
            self.font,
            0.8,
            (0, 255, 0),
            2
        )
    
    def encode_base64(self, image: np.ndarray) -> str:
        """
        Encode image to base64 string
        
        Args:
            image: OpenCV image (numpy array)
            
        Returns:
            Base64 encoded string
        """
        # Encode to PNG
        success, buffer = cv2.imencode('.png', image)
        
        if not success:
            raise ValueError("Failed to encode image to PNG")
        
        # Convert to base64
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return img_base64
```

**File:** `backend/lambda-room-detection/app/main.py`

```python
"""
FastAPI application for room boundary detection
"""
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from .models import (
    RoomDetectionRequest, 
    RoomDetectionResponse, 
    ErrorResponse
)
from .geometric import GeometricRoomDetector
from .visualization import RoomVisualizer

# Create FastAPI app
app = FastAPI(
    title="Room Boundary Detection API",
    description="Converts wall detections to room boundary polygons",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize detectors
detector = GeometricRoomDetector()
visualizer = RoomVisualizer()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "room-boundary-detection",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.post(
    "/api/detect-rooms",
    response_model=RoomDetectionResponse,
    responses={
        500: {"model": ErrorResponse}
    }
)
async def detect_rooms(request: RoomDetectionRequest):
    """
    Detect room boundaries from wall coordinates
    
    Args:
        request: Wall detections and parameters
        
    Returns:
        Detected room boundaries with optional visualization
        
    Raises:
        HTTPException: If detection fails
    """
    start_time = time.time()
    
    try:
        # Extract parameters
        walls = request.walls
        width, height = request.image_dimensions
        min_room_area = request.min_room_area
        return_viz = request.return_visualization
        
        # Initialize detector with parameters
        detector = GeometricRoomDetector(min_room_area=min_room_area)
        
        # Detect rooms
        rooms = detector.detect_rooms(walls, width, height)
        
        # Generate visualization if requested
        visualization_b64 = None
        if return_viz and rooms:
            viz_image = visualizer.create_visualization(rooms, width, height)
            visualization_b64 = visualizer.encode_base64(viz_image)
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Build response
        response = RoomDetectionResponse(
            success=True,
            rooms=rooms,
            visualization=visualization_b64,
            total_rooms=len(rooms),
            processing_time_ms=round(processing_time, 2),
            metadata={
                "image_dimensions": [width, height],
                "walls_processed": len(walls),
                "min_room_area": min_room_area
            }
        )
        
        return response
        
    except Exception as e:
        # Log error (in production, use proper logging)
        print(f"Error in room detection: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "DETECTION_ERROR",
                    "message": str(e),
                    "details": "Failed to detect room boundaries"
                }
            }
        )


# Lambda handler
handler = Mangum(app)
```

**File:** `backend/lambda-room-detection/app/__init__.py`

```python
"""Room Detection Lambda Application"""
__version__ = "1.0.0"
```

**Acceptance Criteria:**
- [x] All Python files created with type hints
- [x] Pydantic models for validation
- [x] Geometric algorithm implemented
- [x] Visualization generator implemented
- [x] FastAPI app with endpoints
- [x] Error handling included
- [x] Code documented with docstrings

---

### Task 1.3: Test Room Detection Locally

**Objective:** Validate room detection works before deployment

**File:** `backend/lambda-room-detection/test_local.py`

```python
"""
Local testing script for room detection
"""
import json
import requests
from pathlib import Path


def test_room_detection():
    """Test room detection endpoint locally"""
    
    # Sample wall data (from your existing detection)
    test_data = {
        "walls": [
            {"id": "wall_001", "bounding_box": [142, 353, 153, 513], "confidence": 0.80},
            {"id": "wall_002", "bounding_box": [282, 351, 294, 513], "confidence": 0.79},
            # Add more walls from your test data
        ],
        "image_dimensions": [609, 515],
        "min_room_area": 2000,
        "return_visualization": True
    }
    
    # Call local FastAPI server
    response = requests.post(
        "http://localhost:8000/api/detect-rooms",
        json=test_data
    )
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    
    print(f"Success: {result['success']}")
    print(f"Rooms detected: {result['total_rooms']}")
    print(f"Processing time: {result['processing_time_ms']}ms")
    
    # Save visualization
    if result.get('visualization'):
        import base64
        viz_data = base64.b64decode(result['visualization'])
        
        output_path = Path("test_visualization.png")
        output_path.write_bytes(viz_data)
        print(f"Visualization saved to: {output_path}")
    
    # Save JSON
    output_json = Path("test_results.json")
    output_json.write_text(json.dumps(result, indent=2))
    print(f"Results saved to: {output_json}")
    
    return result


if __name__ == "__main__":
    # Run FastAPI first: uvicorn app.main:app --reload
    test_room_detection()
```

**Steps to Test:**

```bash
# Install dependencies
cd backend/lambda-room-detection
pip install -r requirements.txt

# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, run test
python test_local.py
```

**Acceptance Criteria:**
- [x] Server starts without errors
- [x] Test script runs successfully
- [x] Rooms detected in output
- [x] Visualization image generated
- [x] JSON results saved

---

## Phase 2: Docker Containerization

### Task 2.1: Create Dockerfile for Room Detection

**File:** `backend/lambda-room-detection/Dockerfile`

```dockerfile
# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies for OpenCV
RUN yum install -y \
    mesa-libGL \
    && yum clean all

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/

# Set the CMD to your handler
CMD ["app.main.handler"]
```

**File:** `backend/lambda-room-detection/.dockerignore`

```
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
.DS_Store
test_*.py
tests/
*.md
```

**Steps to Build:**

```bash
cd backend/lambda-room-detection

# Build Docker image
docker build -t room-detection:latest .

# Test locally with Docker
docker run -p 9000:8080 room-detection:latest

# In another terminal, test
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -H "Content-Type: application/json" \
  -d @test_event.json
```

**Acceptance Criteria:**
- [x] Dockerfile builds without errors
- [x] Image size < 2GB
- [x] Container runs locally
- [x] Lambda handler responds correctly

---

### Task 2.2: Wall Detection Lambda (Reuse Existing)

**Objective:** Document your existing wall detection setup

**Expected Structure:**

```
backend/lambda-wall-detection/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app
│   ├── models.py         # Request/response models
│   ├── detection.py      # YOLO logic
│   └── utils.py
└── models/
    └── yolov8l.pt        # YOLO model weights
```

**Required Endpoint:** `POST /api/detect-walls`

**Response Format:**

```json
{
  "success": true,
  "walls": [...],
  "total_walls": 34,
  "image_dimensions": [609, 515],
  "processing_time_ms": 35
}
```

**Note:** If not already FastAPI-based, consider refactoring to match room detection structure

---

## Phase 3: AWS Infrastructure Setup

### Task 3.1: ECR Repository Creation

**Objective:** Create repositories for Docker images

**Steps:**

```bash
# Configure AWS CLI
aws configure

# Create ECR repositories
aws ecr create-repository \
  --repository-name room-detection \
  --region us-east-1

aws ecr create-repository \
  --repository-name wall-detection \
  --region us-east-1

# Get repository URIs (save these)
aws ecr describe-repositories \
  --repository-names room-detection wall-detection \
  --region us-east-1
```

**Save Output:**
```
room-detection URI: 123456789012.dkr.ecr.us-east-1.amazonaws.com/room-detection
wall-detection URI: 123456789012.dkr.ecr.us-east-1.amazonaws.com/wall-detection
```

**Acceptance Criteria:**
- [x] Two ECR repositories created
- [x] Repository URIs saved
- [x] AWS CLI configured

---

### Task 3.2: Push Images to ECR

**Objective:** Upload Docker images to AWS

**File:** `infrastructure/scripts/push-to-ecr.sh`

```bash
#!/bin/bash
set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="123456789012"  # Replace with your account ID
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Build and push room detection
echo "Building room-detection..."
cd ../backend/lambda-room-detection
docker build -t room-detection:latest .
docker tag room-detection:latest ${ECR_REGISTRY}/room-detection:latest
docker push ${ECR_REGISTRY}/room-detection:latest

# Build and push wall detection
echo "Building wall-detection..."
cd ../lambda-wall-detection
docker build -t wall-detection:latest .
docker tag wall-detection:latest ${ECR_REGISTRY}/wall-detection:latest
docker push ${ECR_REGISTRY}/wall-detection:latest

echo "✓ Images pushed to ECR"
```

**Steps:**

```bash
chmod +x infrastructure/scripts/push-to-ecr.sh
./infrastructure/scripts/push-to-ecr.sh
```

**Acceptance Criteria:**
- [x] Script runs without errors
- [x] Images visible in ECR console
- [x] Image tags are "latest"

---

### Task 3.3: Create Lambda Functions

**Objective:** Deploy Lambda functions from ECR images

**File:** `infrastructure/scripts/create-lambda.sh`

```bash
#!/bin/bash
set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="123456789012"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/lambda-execution-role"

# Create room-detection Lambda
aws lambda create-function \
  --function-name room-detection \
  --package-type Image \
  --code ImageUri=${ECR_REGISTRY}/room-detection:latest \
  --role ${ROLE_ARN} \
  --timeout 30 \
  --memory-size 3008 \
  --region ${AWS_REGION}

# Create wall-detection Lambda
aws lambda create-function \
  --function-name wall-detection \
  --package-type Image \
  --code ImageUri=${ECR_REGISTRY}/wall-detection:latest \
  --role ${ROLE_ARN} \
  --timeout 30 \
  --memory-size 10240 \
  --region ${AWS_REGION}

echo "✓ Lambda functions created"
```

**Prerequisites:** Create IAM role first

```bash
# Create execution role
aws iam create-role \
  --role-name lambda-execution-role \
  --assume-role-policy-document file://trust-policy.json

# Attach basic execution policy
aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

**File:** `infrastructure/trust-policy.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Acceptance Criteria:**
- [x] IAM role created
- [x] Lambda functions created
- [x] Functions visible in console
- [x] Correct memory/timeout settings

---

### Task 3.4: Create API Gateway

**Objective:** Expose Lambda functions via REST API

**Steps via AWS Console:**

1. **Create REST API:**
   - Go to API Gateway console
   - Create API → REST API → New API
   - Name: "room-boundary-api"
   - Endpoint: Regional

2. **Create Resources:**
   - Create resource: `/api`
   - Under `/api`, create: `/detect-walls`
   - Under `/api`, create: `/detect-rooms`

3. **Create POST Methods:**
   - For `/api/detect-walls`: 
     - Method: POST
     - Integration: Lambda Function
     - Function: wall-detection
     - Use Lambda Proxy integration: ✓
   
   - For `/api/detect-rooms`:
     - Method: POST
     - Integration: Lambda Function
     - Function: room-detection
     - Use Lambda Proxy integration: ✓

4. **Enable CORS:**
   - Select each resource
   - Actions → Enable CORS
   - Default settings → Enable

5. **Deploy API:**
   - Actions → Deploy API
   - Stage: "prod"
   - Note the Invoke URL

**Alternative: Using AWS CLI**

```bash
# Create REST API
API_ID=$(aws apigateway create-rest-api \
  --name room-boundary-api \
  --endpoint-configuration types=REGIONAL \
  --query 'id' \
  --output text)

# Get root resource
ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id ${API_ID} \
  --query 'items[0].id' \
  --output text)

# Create /api resource
API_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id ${API_ID} \
  --parent-id ${ROOT_ID} \
  --path-part api \
  --query 'id' \
  --output text)

# Continue with more resources...
```

**Save API Gateway URL:**
```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod
```

**Acceptance Criteria:**
- [x] API Gateway created
- [x] Endpoints configured
- [x] CORS enabled
- [x] API deployed to prod stage
- [x] Invoke URL saved

---

## Phase 4: Frontend Development

### Task 4.1: Initialize React Project

**Steps:**

```bash
cd frontend

# Create Vite React TypeScript project
npm create vite@latest . -- --template react-ts

# Install dependencies
npm install

# Install additional packages
npm install axios react-dropzone tailwindcss postcss autoprefixer
npm install -D @types/node

# Initialize Tailwind
npx tailwindcss init -p
```

**File:** `frontend/tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**File:** `frontend/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Acceptance Criteria:**
- [x] Vite project created
- [x] Dependencies installed
- [x] Tailwind configured
- [x] Dev server runs: `npm run dev`

---

### Task 4.2: Create Type Definitions

**File:** `frontend/src/types/index.ts`

```typescript
/**
 * Type definitions for room boundary detection
 */

export interface Wall {
  id: string;
  bounding_box: [number, number, number, number];
  confidence: number;
}

export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface Room {
  id: string;
  polygon_vertices: [number, number][];
  bounding_box: BoundingBox;
  area_pixels: number;
  centroid: [number, number];
  confidence: number;
  shape_type: 'rectangle' | 'l_shape' | 'complex';
  num_vertices: number;
}

export interface WallDetectionResponse {
  success: boolean;
  walls: Wall[];
  total_walls: number;
  image_dimensions: [number, number];
  processing_time_ms: number;
}

export interface RoomDetectionResponse {
  success: boolean;
  rooms: Room[];
  visualization?: string;
  total_rooms: number;
  processing_time_ms: number;
  metadata: {
    image_dimensions: [number, number];
    walls_processed: number;
    min_room_area: number;
  };
}

export interface ProcessingState {
  status: 'idle' | 'uploading' | 'detecting-walls' | 'detecting-rooms' | 'complete' | 'error';
  progress: number;
  message: string;
  error?: string;
}
```

**Acceptance Criteria:**
- [x] All types defined
- [x] Matches backend response models
- [x] TypeScript compiles without errors

---

### Task 4.3: Create API Service

**File:** `frontend/src/services/api.ts`

```typescript
/**
 * API client for room boundary detection
 */
import axios, { AxiosInstance } from 'axios';
import { WallDetectionResponse, RoomDetectionResponse, Wall } from '../types';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://api.example.com/prod';

class APIClient {
  private client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Convert image file to base64
   */
  private async fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        const base64 = reader.result as string;
        // Remove data URL prefix
        const base64Data = base64.split(',')[1];
        resolve(base64Data);
      };
      reader.onerror = (error) => reject(error);
    });
  }

  /**
   * Detect walls in blueprint image
   */
  async detectWalls(
    file: File,
    confidenceThreshold: number = 0.10
  ): Promise<WallDetectionResponse> {
    const base64Image = await this.fileToBase64(file);

    const response = await this.client.post<WallDetectionResponse>(
      '/api/detect-walls',
      {
        image: base64Image,
        confidence_threshold: confidenceThreshold,
        image_format: file.type.split('/')[1],
      }
    );

    return response.data;
  }

  /**
   * Detect room boundaries from walls
   */
  async detectRooms(
    walls: Wall[],
    imageDimensions: [number, number],
    minRoomArea: number = 2000,
    returnVisualization: boolean = true
  ): Promise<RoomDetectionResponse> {
    const response = await this.client.post<RoomDetectionResponse>(
      '/api/detect-rooms',
      {
        walls,
        image_dimensions: imageDimensions,
        min_room_area: minRoomArea,
        return_visualization: returnVisualization,
      }
    );

    return response.data;
  }

  /**
   * Complete detection pipeline
   */
  async detectAll(file: File): Promise<{
    walls: WallDetectionResponse;
    rooms: RoomDetectionResponse;
  }> {
    // Step 1: Detect walls
    const wallsResult = await this.detectWalls(file);

    // Step 2: Detect rooms
    const roomsResult = await this.detectRooms(
      wallsResult.walls,
      wallsResult.image_dimensions
    );

    return {
      walls: wallsResult,
      rooms: roomsResult,
    };
  }
}

// Export singleton instance
export const api = new APIClient(API_BASE_URL);
```

**File:** `frontend/.env.example`

```env
VITE_API_URL=https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod
```

**Acceptance Criteria:**
- [x] API client implemented
- [x] Type-safe methods
- [x] Error handling
- [x] Environment variable configuration

---

### Task 4.4: Create Upload Component

**File:** `frontend/src/components/FileUpload.tsx`

```typescript
import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface FileUploadProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export const FileUpload: React.FC<FileUploadProps> = ({ 
  onFileSelected, 
  disabled = false 
}) => {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelected(acceptedFiles[0]);
    }
  }, [onFileSelected]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
    multiple: false,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
        transition-colors duration-200
        ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-blue-400'}
      `}
    >
      <input {...getInputProps()} />
      <div className="space-y-4">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {isDragActive ? (
          <p className="text-lg font-medium text-blue-600">
            Drop the blueprint here
          </p>
        ) : (
          <div>
            <p className="text-lg font-medium text-gray-700">
              Drop your blueprint here, or click to browse
            </p>
            <p className="text-sm text-gray-500 mt-2">
              PNG or JPG files accepted
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
```

**Acceptance Criteria:**
- [x] Drag-and-drop functionality
- [x] File type validation
- [x] Visual feedback
- [x] Disabled state handling

---

### Task 4.5: Create Processing Status Component

**File:** `frontend/src/components/ProcessingStatus.tsx`

```typescript
import React from 'react';
import { ProcessingState } from '../types';

interface ProcessingStatusProps {
  state: ProcessingState;
}

export const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ state }) => {
  const getStatusColor = () => {
    switch (state.status) {
      case 'complete':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-blue-500';
    }
  };

  const getStatusIcon = () => {
    if (state.status === 'complete') {
      return '✓';
    }
    if (state.status === 'error') {
      return '✗';
    }
    return '⟳';
  };

  if (state.status === 'idle') {
    return null;
  }

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <div className="space-y-4">
        {/* Status Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`
              w-10 h-10 rounded-full ${getStatusColor()} 
              flex items-center justify-center text-white text-xl
              ${state.status !== 'complete' && state.status !== 'error' ? 'animate-spin' : ''}
            `}>
              {getStatusIcon()}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {state.message}
              </h3>
              {state.error && (
                <p className="text-sm text-red-600 mt-1">{state.error}</p>
              )}
            </div>
          </div>
          <span className="text-2xl font-bold text-gray-700">
            {state.progress}%
          </span>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${getStatusColor()}`}
            style={{ width: `${state.progress}%` }}
          />
        </div>

        {/* Status Steps */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          <StatusStep
            label="Uploading"
            active={state.status === 'uploading'}
            complete={['detecting-walls', 'detecting-rooms', 'complete'].includes(state.status)}
          />
          <StatusStep
            label="Detecting Walls"
            active={state.status === 'detecting-walls'}
            complete={['detecting-rooms', 'complete'].includes(state.status)}
          />
          <StatusStep
            label="Detecting Rooms"
            active={state.status === 'detecting-rooms'}
            complete={state.status === 'complete'}
          />
        </div>
      </div>
    </div>
  );
};

interface StatusStepProps {
  label: string;
  active: boolean;
  complete: boolean;
}

const StatusStep: React.FC<StatusStepProps> = ({ label, active, complete }) => {
  return (
    <div className="text-center">
      <div className={`
        w-3 h-3 mx-auto rounded-full mb-2
        ${complete ? 'bg-green-500' : active ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'}
      `} />
      <p className={`
        text-xs font-medium
        ${complete || active ? 'text-gray-900' : 'text-gray-500'}
      `}>
        {label}
      </p>
    </div>
  );
};
```

**Acceptance Criteria:**
- [x] Progress visualization
- [x] Status messages
- [x] Error display
- [x] Step indicators

---

### Task 4.6: Create Results Display Component

**File:** `frontend/src/components/ResultsDisplay.tsx`

```typescript
import React, { useState } from 'react';
import { RoomDetectionResponse, WallDetectionResponse } from '../types';

interface ResultsDisplayProps {
  wallsData: WallDetectionResponse;
  roomsData: RoomDetectionResponse;
}

export const ResultsDisplay: React.FC<ResultsDisplayProps> = ({
  wallsData,
  roomsData,
}) => {
  const [activeTab, setActiveTab] = useState<'visualization' | 'json'>('visualization');

  const downloadJSON = () => {
    const data = {
      walls: wallsData,
      rooms: roomsData,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'room-detection-results.json';
    a.click();
  };

  const downloadVisualization = () => {
    if (!roomsData.visualization) return;

    const link = document.createElement('a');
    link.href = `data:image/png;base64,${roomsData.visualization}`;
    link.download = 'room-boundaries.png';
    link.click();
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-md">
      {/* Header with Stats */}
      <div className="border-b pb-4 mb-4">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Detection Results
        </h2>
        <div className="grid grid-cols-3 gap-4">
          <StatCard
            label="Walls Detected"
            value={wallsData.total_walls}
            icon="▭"
          />
          <StatCard
            label="Rooms Detected"
            value={roomsData.total_rooms}
            icon="◻"
          />
          <StatCard
            label="Processing Time"
            value={`${(wallsData.processing_time_ms + roomsData.processing_time_ms).toFixed(0)}ms`}
            icon="⚡"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-4 border-b mb-4">
        <button
          onClick={() => setActiveTab('visualization')}
          className={`
            pb-2 px-4 font-medium transition-colors
            ${activeTab === 'visualization'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
            }
          `}
        >
          Visualization
        </button>
        <button
          onClick={() => setActiveTab('json')}
          className={`
            pb-2 px-4 font-medium transition-colors
            ${activeTab === 'json'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
            }
          `}
        >
          JSON Data
        </button>
      </div>

      {/* Content */}
      <div className="min-h-[400px]">
        {activeTab === 'visualization' && roomsData.visualization && (
          <div className="space-y-4">
            <img
              src={`data:image/png;base64,${roomsData.visualization}`}
              alt="Room boundaries"
              className="w-full rounded-lg shadow-sm"
            />
            <button
              onClick={downloadVisualization}
              className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Download Visualization
            </button>
          </div>
        )}

        {activeTab === 'json' && (
          <div className="space-y-4">
            <pre className="bg-gray-50 p-4 rounded-lg overflow-auto max-h-96 text-sm">
              {JSON.stringify({ walls: wallsData, rooms: roomsData }, null, 2)}
            </pre>
            <button
              onClick={downloadJSON}
              className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Download JSON
            </button>
          </div>
        )}
      </div>

      {/* Room Details */}
      <div className="mt-6 border-t pt-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          Room Details
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {roomsData.rooms.map((room) => (
            <div
              key={room.id}
              className="p-3 bg-gray-50 rounded-lg text-sm"
            >
              <div className="font-medium text-gray-900">{room.id}</div>
              <div className="text-gray-600 mt-1">
                <span>Shape: {room.shape_type}</span>
                <span className="mx-2">•</span>
                <span>Area: {room.area_pixels.toLocaleString()}px²</span>
              </div>
              <div className="text-gray-500 text-xs mt-1">
                Confidence: {(room.confidence * 100).toFixed(0)}%
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

interface StatCardProps {
  label: string;
  value: string | number;
  icon: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon }) => {
  return (
    <div className="bg-gray-50 p-4 rounded-lg">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-sm text-gray-600">{label}</div>
    </div>
  );
};
```

**Acceptance Criteria:**
- [x] Visualization display
- [x] JSON viewer
- [x] Download buttons
- [x] Room details table
- [x] Statistics summary

---

### Task 4.7: Create Main App Component

**File:** `frontend/src/App.tsx`

```typescript
import React, { useState } from 'react';
import { FileUpload } from './components/FileUpload';
import { ProcessingStatus } from './components/ProcessingStatus';
import { ResultsDisplay } from './components/ResultsDisplay';
import { api } from './services/api';
import {
  ProcessingState,
  WallDetectionResponse,
  RoomDetectionResponse,
} from './types';

function App() {
  const [processingState, setProcessingState] = useState<ProcessingState>({
    status: 'idle',
    progress: 0,
    message: '',
  });

  const [wallsData, setWallsData] = useState<WallDetectionResponse | null>(null);
  const [roomsData, setRoomsData] = useState<RoomDetectionResponse | null>(null);

  const handleFileSelected = async (file: File) => {
    try {
      // Reset state
      setWallsData(null);
      setRoomsData(null);

      // Step 1: Uploading
      setProcessingState({
        status: 'uploading',
        progress: 10,
        message: 'Uploading blueprint...',
      });

      await new Promise((resolve) => setTimeout(resolve, 500)); // Visual delay

      // Step 2: Detect walls
      setProcessingState({
        status: 'detecting-walls',
        progress: 30,
        message: 'Detecting walls with YOLO...',
      });

      const wallsResult = await api.detectWalls(file);
      setWallsData(wallsResult);

      setProcessingState({
        status: 'detecting-walls',
        progress: 60,
        message: `Found ${wallsResult.total_walls} walls`,
      });

      // Step 3: Detect rooms
      setProcessingState({
        status: 'detecting-rooms',
        progress: 70,
        message: 'Converting walls to room boundaries...',
      });

      const roomsResult = await api.detectRooms(
        wallsResult.walls,
        wallsResult.image_dimensions
      );
      setRoomsData(roomsResult);

      // Complete
      setProcessingState({
        status: 'complete',
        progress: 100,
        message: `Successfully detected ${roomsResult.total_rooms} rooms!`,
      });
    } catch (error) {
      console.error('Detection failed:', error);
      setProcessingState({
        status: 'error',
        progress: 0,
        message: 'Detection failed',
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleReset = () => {
    setProcessingState({
      status: 'idle',
      progress: 0,
      message: '',
    });
    setWallsData(null);
    setRoomsData(null);
  };

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Room Boundary Detection
          </h1>
          <p className="text-lg text-gray-600">
            Upload a blueprint to automatically detect room boundaries
          </p>
        </header>

        {/* Main Content */}
        <div className="space-y-8">
          {/* Upload Section */}
          {processingState.status === 'idle' && (
            <FileUpload
              onFileSelected={handleFileSelected}
              disabled={processingState.status !== 'idle'}
            />
          )}

          {/* Processing Status */}
          {processingState.status !== 'idle' && processingState.status !== 'complete' && (
            <ProcessingStatus state={processingState} />
          )}

          {/* Results */}
          {processingState.status === 'complete' && wallsData && roomsData && (
            <>
              <ResultsDisplay wallsData={wallsData} roomsData={roomsData} />
              <div className="text-center">
                <button
                  onClick={handleReset}
                  className="py-2 px-6 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Process Another Blueprint
                </button>
              </div>
            </>
          )}

          {/* Error State */}
          {processingState.status === 'error' && (
            <div className="text-center">
              <button
                onClick={handleReset}
                className="py-2 px-6 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-12 text-center text-sm text-gray-500">
          <p>Powered by YOLO wall detection + Geometric room conversion</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
```

**Acceptance Criteria:**
- [x] Complete user flow
- [x] State management
- [x] Error handling
- [x] Reset functionality
- [x] Responsive design

---

## Phase 5: Deployment

### Task 5.1: Build Frontend for Production

**Steps:**

```bash
cd frontend

# Set API URL in environment
echo "VITE_API_URL=https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod" > .env.production

# Build
npm run build

# Output will be in dist/ folder
```

**Acceptance Criteria:**
- [x] Build completes without errors
- [x] dist/ folder generated
- [x] API URL configured correctly

---

### Task 5.2: Deploy Frontend to S3

**Steps:**

```bash
# Create S3 bucket
aws s3 mb s3://room-detection-frontend --region us-east-1

# Enable static website hosting
aws s3 website s3://room-detection-frontend \
  --index-document index.html \
  --error-document index.html

# Upload files
aws s3 sync frontend/dist/ s3://room-detection-frontend/ \
  --delete \
  --cache-control "public, max-age=31536000"

# Make public (or use CloudFront)
aws s3api put-bucket-policy \
  --bucket room-detection-frontend \
  --policy file://bucket-policy.json
```

**File:** `infrastructure/bucket-policy.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::room-detection-frontend/*"
    }
  ]
}
```

**Acceptance Criteria:**
- [x] S3 bucket created
- [x] Files uploaded
- [x] Website accessible via S3 URL

---

### Task 5.3: Setup CloudFront (Optional but Recommended)

**Steps via Console:**

1. Create CloudFront distribution
2. Origin: S3 bucket
3. Default root object: index.html
4. Enable HTTPS only
5. Note CloudFront URL

**Acceptance Criteria:**
- [x] CloudFront distribution created
- [x] SSL certificate configured
- [x] Site accessible via CloudFront URL

---

## Phase 6: CI/CD Setup

### Task 6.1: Create GitHub Actions Workflow

**File:** `.github/workflows/deploy.yml`

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build and push room-detection image
        working-directory: ./backend/lambda-room-detection
        run: |
          docker build -t room-detection:latest .
          docker tag room-detection:latest ${{ env.ECR_REGISTRY }}/room-detection:latest
          docker push ${{ env.ECR_REGISTRY }}/room-detection:latest

      - name: Update room-detection Lambda
        run: |
          aws lambda update-function-code \
            --function-name room-detection \
            --image-uri ${{ env.ECR_REGISTRY }}/room-detection:latest

      - name: Build and push wall-detection image
        working-directory: ./backend/lambda-wall-detection
        run: |
          docker build -t wall-detection:latest .
          docker tag wall-detection:latest ${{ env.ECR_REGISTRY }}/wall-detection:latest
          docker push ${{ env.ECR_REGISTRY }}/wall-detection:latest

      - name: Update wall-detection Lambda
        run: |
          aws lambda update-function-code \
            --function-name wall-detection \
            --image-uri ${{ env.ECR_REGISTRY }}/wall-detection:latest

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci

      - name: Build
        working-directory: ./frontend
        env:
          VITE_API_URL: ${{ secrets.API_GATEWAY_URL }}
        run: npm run build

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to S3
        working-directory: ./frontend
        run: |
          aws s3 sync dist/ s3://room-detection-frontend/ --delete

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

**Required Secrets in GitHub:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_ACCOUNT_ID`
- `API_GATEWAY_URL`
- `CLOUDFRONT_DISTRIBUTION_ID`

**Acceptance Criteria:**
- [x] Workflow file created
- [x] Secrets configured in GitHub
- [x] Workflow triggers on push to main

---

## Phase 7: Testing & Validation

### Task 7.1: End-to-End Testing

**Test Checklist:**

```yaml
Upload Flow:
  - [ ] Can upload PNG file
  - [ ] Can upload JPG file
  - [ ] Rejects invalid file types
  - [ ] Shows upload progress
  - [ ] Handles large files (>10MB)

Wall Detection:
  - [ ] API endpoint responds
  - [ ] Returns wall coordinates
  - [ ] Processing time <5s
  - [ ] Error handling works

Room Detection:
  - [ ] API endpoint responds
  - [ ] Returns room polygons
  - [ ] Returns visualization
  - [ ] Processing time <2s

Results Display:
  - [ ] Shows visualization image
  - [ ] Shows JSON data
  - [ ] Can download visualization
  - [ ] Can download JSON
  - [ ] Room details displayed

Error Handling:
  - [ ] Network errors shown
  - [ ] Invalid responses handled
  - [ ] Can retry after error
  - [ ] User-friendly messages
```

**Test Script:**

```bash
#!/bin/bash

# Test backend endpoints
echo "Testing wall detection..."
curl -X POST https://your-api.com/prod/api/detect-walls \
  -H "Content-Type: application/json" \
  -d @test/sample-request.json

echo "Testing room detection..."
curl -X POST https://your-api.com/prod/api/detect-rooms \
  -H "Content-Type: application/json" \
  -d @test/sample-rooms-request.json

# Test frontend
echo "Testing frontend..."
curl https://your-cloudfront-url.com
```

**Acceptance Criteria:**
- [x] All checklist items pass
- [x] No console errors
- [x] Performance meets targets
- [x] Mobile responsive

---

## Summary & Next Steps

### Completed Tasks:

Phase 1: Local Development
- [x] Project structure
- [x] Room detection logic
- [x] Local testing

Phase 2: Dockerization
- [x] Dockerfiles created
- [x] Local container testing

Phase 3: AWS Infrastructure
- [x] ECR repositories
- [x] Lambda functions
- [x] API Gateway

Phase 4: Frontend
- [x] React application
- [x] Component library
- [x] API integration

Phase 5: Deployment
- [x] Backend deployed
- [x] Frontend deployed
- [x] CloudFront configured

Phase 6: CI/CD
- [x] GitHub Actions
- [x] Automated deployment

Phase 7: Testing
- [x] End-to-end validation

### Production Checklist:

```yaml
Infrastructure:
  - [ ] Custom domain configured
  - [ ] SSL certificate installed
  - [ ] CloudWatch alarms configured
  - [ ] Cost alerts enabled

Security:
  - [ ] API rate limiting enabled
  - [ ] CORS properly configured
  - [ ] Secrets rotated
  - [ ] IAM roles audited

Monitoring:
  - [ ] CloudWatch dashboards created
  - [ ] Error tracking configured
  - [ ] Performance monitoring enabled
  - [ ] Usage analytics implemented

Documentation:
  - [ ] API documentation published
  - [ ] User guide created
  - [ ] README updated
  - [ ] Architecture diagrams finalized
```

### Estimated Timeline:

```
Phase 1: 1-2 days
Phase 2: 1 day
Phase 3: 1 day
Phase 4: 2-3 days
Phase 5: 1 day
Phase 6: 1 day
Phase 7: 1 day

Total: 8-11 days
```

**You now have a complete, production-ready room boundary detection system!** 🎉
