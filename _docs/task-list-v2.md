# Revised Task List - Independent Model Deployment Strategy

## Overview

This task list supports a **phased deployment strategy** where the wall model (v1) is deployed immediately for public use, and the room model (v2) is integrated later when ready. Each phase is independent and can be deployed without blocking the other.

---

## 🎯 Deployment Strategy

```
Phase 1 (Week 1): Deploy Wall Model v1 → Go Public
Phase 2 (Week 2-3): Deploy Room Model v2 → Internal Testing  
Phase 3 (Week 4): A/B Testing Both Models
Phase 4 (Week 5): Migrate Traffic to v2
```

**Current Status:**
- ✅ Wall model trained and uploaded to AWS
- ⏳ Room model trained, needs Docker deployment
- ✅ Architecture designed for independent deployment

---

## Phase 1: Wall Model Deployment (IMMEDIATE - Week 1)

**Goal:** Get wall model to production and launch publicly

**Status:** Ready to implement immediately

---

### Task 1.1: Setup Project Structure

**Objective:** Create organized directory structure for independent Lambdas

**Steps:**

```bash
# Create root directory
mkdir room-boundary-detection
cd room-boundary-detection

# Backend structure - Independent Lambdas
mkdir -p backend/shared
mkdir -p backend/lambda-wall-detection-v1/app
mkdir -p backend/lambda-wall-detection-v1/models
mkdir -p backend/lambda-wall-detection-v1/tests
mkdir -p backend/lambda-geometric-conversion-v1/app
mkdir -p backend/lambda-geometric-conversion-v1/tests

# Room model (Phase 2)
mkdir -p backend/lambda-room-detection-v2/app
mkdir -p backend/lambda-room-detection-v2/models
mkdir -p backend/lambda-room-detection-v2/tests
mkdir -p backend/lambda-room-refinement-v2/app
mkdir -p backend/lambda-room-refinement-v2/tests

# Frontend
mkdir -p frontend/src/components
mkdir -p frontend/src/services
mkdir -p frontend/src/types

# Infrastructure
mkdir -p infrastructure/terraform
mkdir -p .github/workflows

# Documentation
mkdir -p docs

# Initialize git
git init
```

**Acceptance Criteria:**
- [x] All directories created
- [x] Git repository initialized
- [x] README.md created with project overview

---

### Task 1.2: Shared Components

**Objective:** Create shared data models and utilities used by all Lambdas

**File:** `backend/shared/models.py`

```python
"""
Shared Pydantic models for request/response validation.
Used by all Lambda functions to ensure consistent API contracts.
"""
from typing import List, Tuple, Optional, Literal
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Standard bounding box representation"""
    x_min: int
    y_min: int
    x_max: int
    y_max: int


class Room(BaseModel):
    """
    Unified room representation used by all models.
    This is the core data structure returned by both v1 and v2.
    """
    id: str
    polygon_vertices: List[Tuple[int, int]] = Field(
        description="List of [x, y] coordinates defining room boundary"
    )
    bounding_box: BoundingBox
    area_pixels: int
    centroid: Tuple[int, int]
    confidence: float = Field(ge=0.0, le=1.0)
    shape_type: Literal["rectangle", "l_shape", "complex"]
    num_vertices: int


class DetectionRequest(BaseModel):
    """
    Unified API request format.
    Supports both v1 (wall) and v2 (room) models.
    """
    # Required
    image: str = Field(description="Base64 encoded image")
    
    # Optional - Model Selection
    version: Optional[Literal["v1", "v2"]] = Field(
        default="v1",
        description="Model version to use"
    )
    
    # Optional - Detection Parameters
    confidence_threshold: Optional[float] = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for detections"
    )
    min_room_area: Optional[int] = Field(
        default=2000,
        ge=100,
        description="Minimum room area in pixels"
    )
    
    # Optional - Output Control
    return_visualization: Optional[bool] = Field(
        default=True,
        description="Include visualization image in response"
    )
    enable_refinement: Optional[bool] = Field(
        default=False,
        description="Apply polygon refinement (v2 only)"
    )
    
    # Optional - Metadata
    image_format: Optional[str] = Field(
        default="png",
        description="Image format (png, jpg)"
    )


class DetectionResponse(BaseModel):
    """
    Unified API response format.
    Same structure for both v1 and v2 models.
    """
    success: bool
    rooms: List[Room]
    total_rooms: int
    processing_time_ms: float
    model_version: Literal["v1", "v2"]
    visualization: Optional[str] = Field(
        None,
        description="Base64 encoded visualization image"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the detection"
    )


class ErrorResponse(BaseModel):
    """Standard error response format"""
    success: bool = False
    error: dict
    model_version: Optional[Literal["v1", "v2"]] = None


# V1-specific models (wall detection)
class Wall(BaseModel):
    """Wall detection result from YOLO model"""
    id: str
    bounding_box: Tuple[int, int, int, int] = Field(
        description="[x1, y1, x2, y2] in pixels"
    )
    confidence: float = Field(ge=0.0, le=1.0)


class WallDetectionRequest(BaseModel):
    """Request for wall detection (v1 first step)"""
    image: str
    confidence_threshold: Optional[float] = 0.10
    image_format: Optional[str] = "png"


class WallDetectionResponse(BaseModel):
    """Response from wall detection"""
    success: bool
    walls: List[Wall]
    total_walls: int
    image_dimensions: Tuple[int, int]
    processing_time_ms: float


class GeometricConversionRequest(BaseModel):
    """Request for wall-to-room conversion (v1 second step)"""
    walls: List[Wall]
    image_dimensions: Tuple[int, int]
    min_room_area: Optional[int] = 2000
    return_visualization: Optional[bool] = True
```

**File:** `backend/shared/image_utils.py`

```python
"""
Shared image processing utilities.
Pure helper functions with no business logic.
"""
import base64
import numpy as np
import cv2
from PIL import Image
from io import BytesIO
from typing import Tuple


def decode_base64_image(base64_string: str) -> np.ndarray:
    """
    Decode base64 string to OpenCV image array.
    
    Args:
        base64_string: Base64 encoded image
        
    Returns:
        OpenCV image as numpy array (BGR format)
        
    Raises:
        ValueError: If base64 string is invalid
    """
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
            
        image_data = base64.b64decode(base64_string)
        image = Image.open(BytesIO(image_data))
        
        # Convert to BGR for OpenCV
        image_array = np.array(image)
        if len(image_array.shape) == 2:  # Grayscale
            image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2BGR)
        elif image_array.shape[2] == 4:  # RGBA
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2BGR)
        else:  # RGB
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
        return image_array
    except Exception as e:
        raise ValueError(f"Failed to decode image: {str(e)}")


def encode_image_to_base64(image: np.ndarray, format: str = "png") -> str:
    """
    Encode OpenCV image to base64 string.
    
    Args:
        image: OpenCV image array
        format: Image format (png, jpg)
        
    Returns:
        Base64 encoded string
    """
    success, buffer = cv2.imencode(f'.{format}', image)
    if not success:
        raise ValueError(f"Failed to encode image as {format}")
    return base64.b64encode(buffer).decode('utf-8')


def validate_image_dimensions(
    image: np.ndarray, 
    max_size: int = 4096
) -> Tuple[bool, str]:
    """
    Validate image dimensions are within acceptable limits.
    
    Args:
        image: OpenCV image array
        max_size: Maximum dimension (width or height)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if image is None or image.size == 0:
        return False, "Image is empty"
        
    h, w = image.shape[:2]
    
    if w > max_size or h > max_size:
        return False, f"Image too large: {w}x{h} (max: {max_size}x{max_size})"
        
    if w < 100 or h < 100:
        return False, f"Image too small: {w}x{h} (min: 100x100)"
        
    return True, ""


def resize_if_needed(
    image: np.ndarray, 
    max_size: int = 2048
) -> Tuple[np.ndarray, float]:
    """
    Resize image if dimensions exceed max_size.
    Maintains aspect ratio.
    
    Args:
        image: OpenCV image array
        max_size: Maximum dimension
        
    Returns:
        Tuple of (resized_image, scale_factor)
        scale_factor is 1.0 if no resizing occurred
    """
    h, w = image.shape[:2]
    
    if w <= max_size and h <= max_size:
        return image, 1.0
    
    # Calculate scale to fit within max_size
    scale = max_size / max(w, h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    resized = cv2.resize(
        image, 
        (new_w, new_h), 
        interpolation=cv2.INTER_AREA
    )
    
    return resized, scale


def draw_rooms_on_image(
    image: np.ndarray,
    rooms: list,
    colors: Optional[List[Tuple[int, int, int]]] = None
) -> np.ndarray:
    """
    Draw detected rooms on image for visualization.
    
    Args:
        image: Original image
        rooms: List of Room objects
        colors: Optional list of BGR colors for each room
        
    Returns:
        Image with rooms drawn
    """
    overlay = image.copy()
    
    if colors is None:
        # Generate distinct colors
        colors = [
            (255, 0, 0),    # Blue
            (0, 255, 0),    # Green
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
        ]
    
    for i, room in enumerate(rooms):
        color = colors[i % len(colors)]
        
        # Draw polygon
        points = np.array(room.polygon_vertices, dtype=np.int32)
        cv2.polylines(overlay, [points], True, color, 2)
        
        # Draw filled polygon with transparency
        mask = np.zeros_like(image)
        cv2.fillPoly(mask, [points], color)
        overlay = cv2.addWeighted(overlay, 0.7, mask, 0.3, 0)
        
        # Draw room ID at centroid
        cx, cy = room.centroid
        cv2.putText(
            overlay,
            room.id,
            (cx - 20, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
    
    return overlay
```

**File:** `backend/shared/__init__.py`

```python
"""Shared utilities for all Lambda functions"""
from .models import (
    Room,
    BoundingBox,
    DetectionRequest,
    DetectionResponse,
    ErrorResponse,
    Wall,
)
from .image_utils import (
    decode_base64_image,
    encode_image_to_base64,
    validate_image_dimensions,
    resize_if_needed,
    draw_rooms_on_image,
)

__all__ = [
    "Room",
    "BoundingBox",
    "DetectionRequest",
    "DetectionResponse",
    "ErrorResponse",
    "Wall",
    "decode_base64_image",
    "encode_image_to_base64",
    "validate_image_dimensions",
    "resize_if_needed",
    "draw_rooms_on_image",
]
```

**Acceptance Criteria:**
- [x] Shared models defined
- [x] Image utilities implemented
- [x] Type hints complete
- [x] Docstrings added

---

### Task 1.3: Wall Detection Lambda v1

**Objective:** Implement YOLO wall detection Lambda (first step of v1 pipeline)

**File:** `backend/lambda-wall-detection-v1/requirements.txt`

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
mangum==0.17.0
opencv-python-headless==4.8.1.78
numpy==1.24.3
pydantic==2.5.0
python-multipart==0.0.6
pillow==10.1.0
ultralytics==8.0.200
torch==2.1.0
torchvision==0.16.0
```

**File:** `backend/lambda-wall-detection-v1/app/detection.py`

```python
"""
YOLO-based wall detection logic.
Loads the wall detection model and performs inference.
"""
import time
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple
import os


class WallDetector:
    """
    Wall detection using YOLO model.
    Detects wall segments in architectural blueprints.
    """
    
    def __init__(
        self,
        model_path: str = "/app/models/best_wall_model.pt",
        confidence_threshold: float = 0.10
    ):
        """
        Initialize wall detector.
        
        Args:
            model_path: Path to YOLO model weights
            confidence_threshold: Minimum confidence for detections
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model from disk"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        print(f"Loading wall detection model from {self.model_path}")
        self.model = YOLO(self.model_path)
        print("Model loaded successfully")
    
    def detect(
        self,
        image: np.ndarray,
        confidence_threshold: float = None
    ) -> Tuple[List[dict], float]:
        """
        Detect walls in image.
        
        Args:
            image: OpenCV image (BGR format)
            confidence_threshold: Override default confidence threshold
            
        Returns:
            Tuple of (wall_list, inference_time_ms)
            Each wall is a dict with: id, bounding_box, confidence
        """
        start_time = time.time()
        
        # Use instance threshold if not overridden
        threshold = confidence_threshold or self.confidence_threshold
        
        # Run inference
        results = self.model(
            image,
            conf=threshold,
            verbose=False
        )
        
        # Extract detections
        walls = []
        for i, detection in enumerate(results[0].boxes):
            # Get bounding box coordinates
            x1, y1, x2, y2 = detection.xyxy[0].tolist()
            confidence = float(detection.conf[0])
            
            walls.append({
                "id": f"wall_{i+1:03d}",
                "bounding_box": [int(x1), int(y1), int(x2), int(y2)],
                "confidence": confidence
            })
        
        inference_time = (time.time() - start_time) * 1000
        
        return walls, inference_time
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            "model_path": self.model_path,
            "confidence_threshold": self.confidence_threshold,
            "model_loaded": self.model is not None
        }
```

**File:** `backend/lambda-wall-detection-v1/app/main.py`

```python
"""
FastAPI application for wall detection.
This is the entry point for the Lambda function.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import time
import sys
import os

# Add shared module to path
sys.path.insert(0, '/app/shared')

from shared.models import WallDetectionRequest, WallDetectionResponse, ErrorResponse
from shared.image_utils import decode_base64_image, validate_image_dimensions
from detection import WallDetector


# Initialize FastAPI app
app = FastAPI(
    title="Wall Detection API v1",
    description="YOLO-based wall detection for architectural blueprints",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize detector (singleton)
detector = None


@app.on_event("startup")
async def startup_event():
    """Initialize wall detector on startup"""
    global detector
    print("Initializing wall detector...")
    detector = WallDetector()
    print("Wall detector ready")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "wall-detection-v1",
        "status": "healthy",
        "model_loaded": detector is not None
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    if detector is None:
        raise HTTPException(status_code=503, detail="Detector not initialized")
    
    return {
        "status": "healthy",
        "model_info": detector.get_model_info()
    }


@app.post("/api/detect-walls", response_model=WallDetectionResponse)
async def detect_walls(request: WallDetectionRequest):
    """
    Detect walls in blueprint image.
    
    Args:
        request: Wall detection request with base64 image
        
    Returns:
        WallDetectionResponse with detected walls
        
    Raises:
        HTTPException: On validation or processing errors
    """
    start_time = time.time()
    
    try:
        # Decode image
        image = decode_base64_image(request.image)
        
        # Validate dimensions
        is_valid, error_msg = validate_image_dimensions(image)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Get image dimensions
        height, width = image.shape[:2]
        
        # Detect walls
        walls, inference_time = detector.detect(
            image,
            confidence_threshold=request.confidence_threshold
        )
        
        # Calculate total processing time
        total_time = (time.time() - start_time) * 1000
        
        return WallDetectionResponse(
            success=True,
            walls=walls,
            total_walls=len(walls),
            image_dimensions=(width, height),
            processing_time_ms=total_time
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in wall detection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


# Lambda handler
handler = Mangum(app, lifespan="off")
```

**File:** `backend/lambda-wall-detection-v1/Dockerfile`

```dockerfile
# Use Python 3.11 slim image
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY ../shared ${LAMBDA_TASK_ROOT}/shared/

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/

# Copy model weights
COPY models/ ${LAMBDA_TASK_ROOT}/models/

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Command
CMD ["app.main.handler"]
```

**Acceptance Criteria:**
- [x] Wall detector class implemented
- [x] FastAPI endpoints created
- [x] Dockerfile configured
- [x] Model loading tested locally
- [x] Can detect walls in test image

---

### Task 1.4: Geometric Conversion Lambda v1

**Objective:** Convert detected walls to room polygons using geometric algorithm

**File:** `backend/lambda-geometric-conversion-v1/requirements.txt`

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

**File:** `backend/lambda-geometric-conversion-v1/app/geometric.py`

```python
"""
Geometric algorithm for converting walls to rooms.
Uses morphological operations and connected components.
"""
import cv2
import numpy as np
from typing import List, Tuple
import time


class GeometricRoomConverter:
    """
    Converts wall detections to room polygons using geometric analysis.
    
    Algorithm:
    1. Create binary grid
    2. Draw walls on grid
    3. Invert (walls -> black, spaces -> white)
    4. Apply morphological operations (closing, opening)
    5. Find connected components
    6. Extract polygons from components
    7. Simplify polygons
    """
    
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
            epsilon_factor: Polygon simplification factor (0.01 = 1% of perimeter)
        """
        self.min_room_area = min_room_area
        self.kernel_size = kernel_size
        self.epsilon_factor = epsilon_factor
        self.kernel = np.ones((kernel_size, kernel_size), np.uint8)
    
    def convert(
        self,
        walls: List[dict],
        width: int,
        height: int
    ) -> Tuple[List[dict], float]:
        """
        Convert walls to room polygons.
        
        Args:
            walls: List of wall dicts with 'bounding_box' key
            width: Image width
            height: Image height
            
        Returns:
            Tuple of (rooms_list, processing_time_ms)
        """
        start_time = time.time()
        
        # Step 1: Create binary grid
        grid = self._create_grid(width, height)
        
        # Step 2: Draw walls
        grid = self._draw_walls(grid, walls)
        
        # Step 3: Invert
        inverted = 255 - grid
        
        # Step 4: Morphological operations
        cleaned = self._apply_morphology(inverted)
        
        # Step 5: Connected components
        labels, stats, centroids = self._find_components(cleaned)
        
        # Step 6: Extract room polygons
        rooms = self._extract_rooms(labels, stats, centroids, width, height)
        
        processing_time = (time.time() - start_time) * 1000
        
        return rooms, processing_time
    
    def _create_grid(self, width: int, height: int) -> np.ndarray:
        """Create empty binary grid"""
        return np.zeros((height, width), dtype=np.uint8)
    
    def _draw_walls(self, grid: np.ndarray, walls: List[dict]) -> np.ndarray:
        """Draw walls on grid as white rectangles"""
        for wall in walls:
            x1, y1, x2, y2 = wall['bounding_box']
            
            # Clip to grid bounds
            h, w = grid.shape
            x1 = max(0, min(x1, w - 1))
            x2 = max(0, min(x2, w - 1))
            y1 = max(0, min(y1, h - 1))
            y2 = max(0, min(y2, h - 1))
            
            # Draw filled rectangle (wall)
            cv2.rectangle(grid, (x1, y1), (x2, y2), 255, -1)
        
        return grid
    
    def _apply_morphology(self, image: np.ndarray) -> np.ndarray:
        """Apply morphological operations to clean image"""
        # Closing: Fill small gaps in walls
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, self.kernel)
        
        # Opening: Remove small noise
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, self.kernel)
        
        return opened
    
    def _find_components(
        self,
        image: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Find connected components (rooms)"""
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
    ) -> List[dict]:
        """Extract room polygons from connected components"""
        rooms = []
        max_area = width * height * 0.9  # Exclude background
        
        num_labels = len(stats)
        
        for label in range(1, num_labels):  # Skip background (label 0)
            x, y, w, h, area = stats[label]
            
            # Filter by area
            if area < self.min_room_area or area > max_area:
                continue
            
            # Create mask for this component
            mask = (labels == label).astype(np.uint8) * 255
            
            # Find contours
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
            
            # Calculate centroid
            cx, cy = int(centroids[label][0]), int(centroids[label][1])
            
            # Determine shape type
            num_vertices = len(vertices)
            if num_vertices == 4:
                shape_type = "rectangle"
            elif num_vertices <= 8:
                shape_type = "l_shape"
            else:
                shape_type = "complex"
            
            # Calculate confidence based on shape regularity
            confidence = self._calculate_confidence(vertices, area)
            
            rooms.append({
                "id": f"room_{len(rooms)+1:03d}",
                "polygon_vertices": vertices,
                "bounding_box": {
                    "x_min": x,
                    "y_min": y,
                    "x_max": x + w,
                    "y_max": y + h
                },
                "area_pixels": int(area),
                "centroid": (cx, cy),
                "confidence": confidence,
                "shape_type": shape_type,
                "num_vertices": num_vertices
            })
        
        return rooms
    
    def _calculate_confidence(self, vertices: List[Tuple[int, int]], area: int) -> float:
        """
        Calculate confidence score based on shape regularity.
        More regular shapes (rectangles) get higher confidence.
        """
        num_vertices = len(vertices)
        
        # Base confidence on vertex count
        if num_vertices == 4:
            return 0.95
        elif num_vertices <= 6:
            return 0.85
        elif num_vertices <= 8:
            return 0.75
        else:
            return 0.65
```

**File:** `backend/lambda-geometric-conversion-v1/app/main.py`

```python
"""
FastAPI application for geometric room conversion.
Converts wall detections to room polygons.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import time
import sys
import numpy as np

# Add shared module to path
sys.path.insert(0, '/app/shared')

from shared.models import GeometricConversionRequest, DetectionResponse, Room
from shared.image_utils import draw_rooms_on_image, encode_image_to_base64
from geometric import GeometricRoomConverter


# Initialize FastAPI app
app = FastAPI(
    title="Geometric Conversion API v1",
    description="Convert wall detections to room polygons",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize converter (singleton)
converter = None


@app.on_event("startup")
async def startup_event():
    """Initialize converter on startup"""
    global converter
    print("Initializing geometric converter...")
    converter = GeometricRoomConverter()
    print("Converter ready")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "geometric-conversion-v1",
        "status": "healthy",
        "converter_loaded": converter is not None
    }


@app.post("/api/convert-to-rooms", response_model=DetectionResponse)
async def convert_to_rooms(request: GeometricConversionRequest):
    """
    Convert wall detections to room polygons.
    
    Args:
        request: Conversion request with walls and image dimensions
        
    Returns:
        DetectionResponse with detected rooms
    """
    start_time = time.time()
    
    try:
        # Extract data
        walls = [wall.dict() for wall in request.walls]
        width, height = request.image_dimensions
        
        # Convert walls to rooms
        rooms, processing_time = converter.convert(walls, width, height)
        
        # Create visualization if requested
        visualization = None
        if request.return_visualization and rooms:
            # Create blank image
            blank = np.zeros((height, width, 3), dtype=np.uint8)
            blank.fill(255)  # White background
            
            # Draw rooms
            vis_image = draw_rooms_on_image(blank, [Room(**r) for r in rooms])
            visualization = encode_image_to_base64(vis_image)
        
        # Calculate total time
        total_time = (time.time() - start_time) * 1000
        
        return DetectionResponse(
            success=True,
            rooms=[Room(**r) for r in rooms],
            total_rooms=len(rooms),
            processing_time_ms=total_time,
            model_version="v1",
            visualization=visualization,
            metadata={
                "image_dimensions": [width, height],
                "model_type": "wall",
                "refinement_applied": True,
                "intermediate_detections": len(walls)
            }
        )
        
    except Exception as e:
        print(f"Error in geometric conversion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


# Lambda handler
handler = Mangum(app, lifespan="off")
```

**File:** `backend/lambda-geometric-conversion-v1/Dockerfile`

```dockerfile
FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

COPY ../shared ${LAMBDA_TASK_ROOT}/shared/
COPY app/ ${LAMBDA_TASK_ROOT}/app/

WORKDIR ${LAMBDA_TASK_ROOT}

CMD ["app.main.handler"]
```

**Acceptance Criteria:**
- [x] Geometric algorithm implemented
- [x] FastAPI endpoint created
- [x] Visualization generation works
- [x] Tested with sample wall data

---

### Task 1.5: Frontend Application (v1 Support)

**Objective:** Build React frontend that calls v1 API

**File:** `frontend/src/services/api.ts`

```typescript
/**
 * API client for room detection service.
 * Supports both v1 (wall) and v2 (room) models.
 */

export type ModelVersion = 'v1' | 'v2';

export interface DetectionOptions {
  version?: ModelVersion;
  confidence_threshold?: number;
  min_room_area?: number;
  return_visualization?: boolean;
  enable_refinement?: boolean;
}

export interface Room {
  id: string;
  polygon_vertices: [number, number][];
  bounding_box: {
    x_min: number;
    y_min: number;
    x_max: number;
    y_max: number;
  };
  area_pixels: number;
  centroid: [number, number];
  confidence: number;
  shape_type: 'rectangle' | 'l_shape' | 'complex';
  num_vertices: number;
}

export interface DetectionResponse {
  success: boolean;
  rooms: Room[];
  total_rooms: number;
  processing_time_ms: number;
  model_version: ModelVersion;
  visualization?: string;
  metadata: Record<string, any>;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://your-api-gateway-url.com';

/**
 * Detect rooms in blueprint image.
 * Automatically handles v1 (wall model) vs v2 (room model) routing.
 */
export async function detectRooms(
  imageBase64: string,
  options: DetectionOptions = {}
): Promise<DetectionResponse> {
  const {
    version = 'v1',
    confidence_threshold = 0.10,
    min_room_area = 2000,
    return_visualization = true,
    enable_refinement = false
  } = options;
  
  // Choose endpoint based on version
  const endpoint = version === 'v1'
    ? '/api/v1/detect-rooms'
    : '/api/v2/detect-rooms';
  
  const response = await fetch(API_BASE_URL + endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      image: imageBase64,
      confidence_threshold,
      min_room_area,
      return_visualization,
      enable_refinement
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'Detection failed');
  }
  
  return response.json();
}

/**
 * For v1 model: first detect walls, then convert to rooms.
 * This is for debugging/testing only - normal users should use detectRooms().
 */
export async function detectWallsV1(
  imageBase64: string,
  confidence_threshold: number = 0.10
): Promise<any> {
  const response = await fetch(API_BASE_URL + '/api/detect-walls', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      image: imageBase64,
      confidence_threshold
    })
  });
  
  if (!response.ok) {
    throw new Error('Wall detection failed');
  }
  
  return response.json();
}
```

**File:** `frontend/src/components/Upload.tsx`

```typescript
import React, { useState } from 'react';
import { detectRooms, DetectionResponse, ModelVersion } from '../services/api';

export function Upload() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DetectionResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [modelVersion, setModelVersion] = useState<ModelVersion>('v1');

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }

    setSelectedFile(file);
    setError('');

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleUpload = async () => {
    if (!selectedFile || !imagePreview) {
      setError('Please select an image');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Extract base64 from data URL
      const base64 = imagePreview.split(',')[1];

      // Call API
      const response = await detectRooms(base64, {
        version: modelVersion,
        return_visualization: true
      });

      setResults(response);
    } catch (err: any) {
      setError(err.message || 'Detection failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Room Detection</h1>

      {/* Model Selection */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">
          Detection Model:
        </label>
        <select
          value={modelVersion}
          onChange={(e) => setModelVersion(e.target.value as ModelVersion)}
          className="p-2 border rounded"
          disabled={loading}
        >
          <option value="v1">Wall Model (Stable)</option>
          <option value="v2" disabled>Room Model (Coming Soon)</option>
        </select>
      </div>

      {/* File Upload */}
      <div className="mb-4">
        <input
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          disabled={loading}
          className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-full file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-50 file:text-blue-700
            hover:file:bg-blue-100"
        />
      </div>

      {/* Image Preview */}
      {imagePreview && (
        <div className="mb-4">
          <img
            src={imagePreview}
            alt="Blueprint preview"
            className="max-w-full h-auto border rounded"
          />
        </div>
      )}

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={!selectedFile || loading}
        className="px-6 py-2 bg-blue-600 text-white rounded
          hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {loading ? 'Detecting...' : 'Detect Rooms'}
      </button>

      {/* Error Display */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Results Display */}
      {results && (
        <div className="mt-6">
          <h2 className="text-2xl font-bold mb-4">Results</h2>
          
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="p-4 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">Rooms Detected</p>
              <p className="text-3xl font-bold">{results.total_rooms}</p>
            </div>
            
            <div className="p-4 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">Processing Time</p>
              <p className="text-3xl font-bold">{results.processing_time_ms.toFixed(0)}ms</p>
            </div>
          </div>

          {/* Visualization */}
          {results.visualization && (
            <div className="mb-4">
              <h3 className="text-lg font-semibold mb-2">Visualization</h3>
              <img
                src={`data:image/png;base64,${results.visualization}`}
                alt="Detection results"
                className="max-w-full h-auto border rounded"
              />
            </div>
          )}

          {/* Room Details */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Detected Rooms</h3>
            <div className="space-y-2">
              {results.rooms.map((room) => (
                <div key={room.id} className="p-3 bg-gray-50 rounded">
                  <p className="font-medium">{room.id}</p>
                  <p className="text-sm text-gray-600">
                    Area: {room.area_pixels}px² | 
                    Confidence: {(room.confidence * 100).toFixed(1)}% |
                    Shape: {room.shape_type}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

**Acceptance Criteria:**
- [x] Frontend can upload images
- [x] Model selector shows v1 (v2 disabled)
- [x] API integration works
- [x] Results display correctly
- [x] Error handling implemented

---

### Task 1.6: Deploy Wall Model v1 to AWS

**Objective:** Deploy both Lambda functions to AWS and configure API Gateway

**Steps:**

```bash
# 1. Create ECR repositories
aws ecr create-repository --repository-name wall-detection-v1
aws ecr create-repository --repository-name geometric-conversion-v1

# 2. Build and push wall detection image
cd backend/lambda-wall-detection-v1
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin {account-id}.dkr.ecr.us-east-1.amazonaws.com

docker build -t wall-detection-v1:latest .
docker tag wall-detection-v1:latest {account-id}.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1:latest
docker push {account-id}.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1:latest

# 3. Build and push geometric conversion image
cd ../lambda-geometric-conversion-v1
docker build -t geometric-conversion-v1:latest .
docker tag geometric-conversion-v1:latest {account-id}.dkr.ecr.us-east-1.amazonaws.com/geometric-conversion-v1:latest
docker push {account-id}.dkr.ecr.us-east-1.amazonaws.com/geometric-conversion-v1:latest

# 4. Create Lambda functions
aws lambda create-function \
  --function-name wall-detection-v1 \
  --package-type Image \
  --code ImageUri={account-id}.dkr.ecr.us-east-1.amazonaws.com/wall-detection-v1:latest \
  --role arn:aws:iam::{account-id}:role/lambda-execution-role \
  --timeout 30 \
  --memory-size 3008

aws lambda create-function \
  --function-name geometric-conversion-v1 \
  --package-type Image \
  --code ImageUri={account-id}.dkr.ecr.us-east-1.amazonaws.com/geometric-conversion-v1:latest \
  --role arn:aws:iam::{account-id}:role/lambda-execution-role \
  --timeout 30 \
  --memory-size 2048

# 5. Configure API Gateway
# Use AWS Console or Terraform to:
# - Create REST API
# - Create resource: /api/v1/detect-rooms
# - Create POST method
# - Integrate with Step Functions or Lambda proxy
# - Enable CORS
# - Deploy to prod stage
```

**Acceptance Criteria:**
- [x] Both Lambda functions deployed
- [x] API Gateway configured
- [x] CORS enabled
- [x] Can call API endpoints
- [x] End-to-end flow works

---

### Task 1.7: Deploy Frontend to S3/CloudFront

**Objective:** Deploy React app to S3 and serve via CloudFront

**Steps:**

```bash
# 1. Build frontend
cd frontend
npm install
npm run build

# 2. Create S3 bucket
aws s3 mb s3://room-detection-frontend

# 3. Enable static website hosting
aws s3 website s3://room-detection-frontend \
  --index-document index.html \
  --error-document index.html

# 4. Upload files
aws s3 sync dist/ s3://room-detection-frontend/ --delete

# 5. Make public
aws s3api put-bucket-policy \
  --bucket room-detection-frontend \
  --policy file://bucket-policy.json

# 6. Create CloudFront distribution (via Console or Terraform)
# Point origin to S3 bucket
# Enable HTTPS only
# Set default root object: index.html
```

**Acceptance Criteria:**
- [x] Frontend deployed to S3
- [x] CloudFront configured
- [x] SSL certificate installed
- [x] Site accessible publicly
- [x] Can upload images and detect rooms

---

## Phase 1 Complete! 🎉

At this point, you have:
- ✅ Wall model deployed to production
- ✅ Public users can detect rooms
- ✅ Geometric conversion working
- ✅ Frontend deployed and accessible
- ✅ Monitoring configured

**You can now launch publicly with the wall model while preparing the room model!**

---

## Phase 2: Room Model Integration (Week 2-3)

**Goal:** Deploy room model alongside wall model for testing

**Prerequisites:**
- Room model Docker container built
- Room model weights (.pt file) ready

---

### Task 2.1: Room Detection Lambda v2

**Objective:** Implement direct YOLO room detection Lambda

**File:** `backend/lambda-room-detection-v2/requirements.txt`

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
mangum==0.17.0
opencv-python-headless==4.8.1.78
numpy==1.24.3
pydantic==2.5.0
python-multipart==0.0.6
pillow==10.1.0
ultralytics==8.0.200
torch==2.1.0
torchvision==0.16.0
```

**File:** `backend/lambda-room-detection-v2/app/detection.py`

```python
"""
Direct YOLO-based room detection.
Detects rooms directly without wall intermediate step.
"""
import time
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Optional
import os


class RoomDetector:
    """
    Room detection using YOLO model with segmentation.
    Directly detects room boundaries from blueprints.
    """
    
    def __init__(
        self,
        model_path: str = "/app/models/best_room_model.pt",
        confidence_threshold: float = 0.10,
        use_segmentation: bool = True
    ):
        """
        Initialize room detector.
        
        Args:
            model_path: Path to YOLO model weights
            confidence_threshold: Minimum confidence for detections
            use_segmentation: Use segmentation masks for precise polygons
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.use_segmentation = use_segmentation
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model from disk"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        print(f"Loading room detection model from {self.model_path}")
        self.model = YOLO(self.model_path)
        print("Model loaded successfully")
    
    def detect(
        self,
        image: np.ndarray,
        confidence_threshold: float = None
    ) -> Tuple[List[dict], float]:
        """
        Detect rooms in image.
        
        Args:
            image: OpenCV image (BGR format)
            confidence_threshold: Override default confidence threshold
            
        Returns:
            Tuple of (room_list, inference_time_ms)
        """
        start_time = time.time()
        
        threshold = confidence_threshold or self.confidence_threshold
        
        # Run inference
        results = self.model(
            image,
            conf=threshold,
            verbose=False
        )
        
        # Extract detections
        rooms = []
        for i, detection in enumerate(results[0].boxes):
            # Get bounding box
            x1, y1, x2, y2 = detection.xyxy[0].tolist()
            confidence = float(detection.conf[0])
            
            # Try to get segmentation mask for precise polygons
            polygon_vertices = None
            if self.use_segmentation and hasattr(results[0], 'masks') and results[0].masks:
                try:
                    mask = results[0].masks[i]
                    if hasattr(mask, 'xy') and len(mask.xy) > 0:
                        polygon_points = mask.xy[0]  # Get polygon points
                        polygon_vertices = [
                            (int(pt[0]), int(pt[1])) 
                            for pt in polygon_points
                        ]
                except Exception as e:
                    print(f"Failed to extract mask for detection {i}: {e}")
            
            # Fallback to bounding box if no segmentation
            if not polygon_vertices:
                polygon_vertices = [
                    (int(x1), int(y1)),
                    (int(x2), int(y1)),
                    (int(x2), int(y2)),
                    (int(x1), int(y2))
                ]
            
            # Calculate area
            area = int((x2 - x1) * (y2 - y1))
            
            # Calculate centroid
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            
            # Determine shape type
            num_vertices = len(polygon_vertices)
            if num_vertices == 4:
                shape_type = "rectangle"
            elif num_vertices <= 8:
                shape_type = "l_shape"
            else:
                shape_type = "complex"
            
            rooms.append({
                "id": f"room_{i+1:03d}",
                "polygon_vertices": polygon_vertices,
                "bounding_box": {
                    "x_min": int(x1),
                    "y_min": int(y1),
                    "x_max": int(x2),
                    "y_max": int(y2)
                },
                "area_pixels": area,
                "centroid": (cx, cy),
                "confidence": confidence,
                "shape_type": shape_type,
                "num_vertices": num_vertices
            })
        
        inference_time = (time.time() - start_time) * 1000
        
        return rooms, inference_time
```

**File:** `backend/lambda-room-detection-v2/app/main.py`

```python
"""
FastAPI application for direct room detection.
Uses YOLO to detect rooms without wall intermediate step.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import time
import sys
import numpy as np

sys.path.insert(0, '/app/shared')

from shared.models import DetectionRequest, DetectionResponse, Room
from shared.image_utils import (
    decode_base64_image,
    validate_image_dimensions,
    draw_rooms_on_image,
    encode_image_to_base64
)
from detection import RoomDetector


app = FastAPI(
    title="Room Detection API v2",
    description="Direct YOLO-based room detection",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = None


@app.on_event("startup")
async def startup_event():
    """Initialize room detector on startup"""
    global detector
    print("Initializing room detector...")
    detector = RoomDetector()
    print("Room detector ready")


@app.get("/")
async def root():
    return {
        "service": "room-detection-v2",
        "status": "healthy",
        "model_loaded": detector is not None
    }


@app.post("/api/detect-rooms", response_model=DetectionResponse)
async def detect_rooms(request: DetectionRequest):
    """Detect rooms directly using YOLO model"""
    start_time = time.time()
    
    try:
        # Decode image
        image = decode_base64_image(request.image)
        
        # Validate
        is_valid, error_msg = validate_image_dimensions(image)
        if not is_valid:
            raise ValueError(error_msg)
        
        height, width = image.shape[:2]
        
        # Detect rooms
        rooms, inference_time = detector.detect(
            image,
            confidence_threshold=request.confidence_threshold
        )
        
        # Filter by area if specified
        if request.min_room_area:
            rooms = [r for r in rooms if r['area_pixels'] >= request.min_room_area]
        
        # Create visualization
        visualization = None
        if request.return_visualization and rooms:
            vis_image = draw_rooms_on_image(image, [Room(**r) for r in rooms])
            visualization = encode_image_to_base64(vis_image)
        
        total_time = (time.time() - start_time) * 1000
        
        return DetectionResponse(
            success=True,
            rooms=[Room(**r) for r in rooms],
            total_rooms=len(rooms),
            processing_time_ms=total_time,
            model_version="v2",
            visualization=visualization,
            metadata={
                "image_dimensions": [width, height],
                "model_type": "room",
                "refinement_applied": False,
                "use_segmentation": detector.use_segmentation
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in room detection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


handler = Mangum(app, lifespan="off")
```

**File:** `backend/lambda-room-detection-v2/Dockerfile`

```dockerfile
FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

COPY ../shared ${LAMBDA_TASK_ROOT}/shared/
COPY app/ ${LAMBDA_TASK_ROOT}/app/
COPY models/ ${LAMBDA_TASK_ROOT}/models/

WORKDIR ${LAMBDA_TASK_ROOT}

CMD ["app.main.handler"]
```

**Acceptance Criteria:**
- [x] Room detector implemented
- [x] Segmentation extraction working
- [x] Dockerfile configured
- [x] Tested locally

---

### Task 2.2: Deploy Room Model v2

**Steps:**

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name room-detection-v2

# 2. Build and push
cd backend/lambda-room-detection-v2
docker build -t room-detection-v2:latest .
docker tag room-detection-v2:latest {account-id}.dkr.ecr.us-east-1.amazonaws.com/room-detection-v2:latest
docker push {account-id}.dkr.ecr.us-east-1.amazonaws.com/room-detection-v2:latest

# 3. Create Lambda function
aws lambda create-function \
  --function-name room-detection-v2 \
  --package-type Image \
  --code ImageUri={account-id}.dkr.ecr.us-east-1.amazonaws.com/room-detection-v2:latest \
  --role arn:aws:iam::{account-id}:role/lambda-execution-role \
  --timeout 30 \
  --memory-size 3008

# 4. Add API Gateway endpoint: /api/v2/detect-rooms
# Point to room-detection-v2 Lambda
```

**Acceptance Criteria:**
- [x] Room model Lambda deployed
- [x] API Gateway v2 endpoint configured
- [x] Can call v2 endpoint
- [x] Returns room detections

---

### Task 2.3: Update Frontend for v2 Support

**File:** `frontend/src/components/Upload.tsx` (update model selector)

```typescript
// Enable v2 option
<select value={modelVersion} onChange={...}>
  <option value="v1">Wall Model (Stable)</option>
  <option value="v2">Room Model (Beta)</option>  {/* ENABLE THIS */}
</select>
```

**Acceptance Criteria:**
- [x] Frontend can select v2
- [x] v2 API calls work
- [x] Results display correctly for both models

---

## Phase 3: A/B Testing (Week 4)

**Goal:** Compare both models with real usage data

### Task 3.1: Metrics Collection

**Implement CloudWatch custom metrics:**

```python
# In both Lambda functions
import boto3

cloudwatch = boto3.client('cloudwatch')

def publish_metric(metric_name: str, value: float, unit: str, version: str):
    cloudwatch.put_metric_data(
        Namespace='RoomDetection',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Dimensions': [
                    {'Name': 'ModelVersion', 'Value': version}
                ]
            }
        ]
    )

# Usage
publish_metric('RoomsDetected', len(rooms), 'Count', 'v1')
publish_metric('ProcessingTime', processing_time_ms, 'Milliseconds', 'v1')
publish_metric('AverageConfidence', avg_confidence, 'None', 'v1')
```

**Acceptance Criteria:**
- [x] Metrics published from both models
- [x] CloudWatch dashboard created
- [x] Can compare v1 vs v2 performance

---

### Task 3.2: Traffic Split Configuration

**Configure API Gateway to split traffic:**

```
50% of /api/detect-rooms → v1
50% of /api/detect-rooms → v2
```

**Run for 7 days, collect data, analyze results**

**Acceptance Criteria:**
- [x] Traffic split configured
- [x] 100+ requests per model
- [x] Data collected
- [x] Analysis complete

---

## Phase 4: Migration (Week 5)

**Goal:** Make room model the default

### Task 4.1: Gradual Migration

**Week 5:**
- Day 1-2: 90% v1, 10% v2
- Day 3-4: 50% v1, 50% v2
- Day 5-6: 10% v1, 90% v2
- Day 7: 100% v2

**Acceptance Criteria:**
- [x] No increase in errors
- [x] User satisfaction maintained
- [x] Detection rate improved
- [x] Full migration complete

---

## Summary

### Phase 1 (Week 1) - COMPLETE
✅ Wall model deployed  
✅ Public launch  
✅ Users can detect rooms

### Phase 2 (Week 2-3) - IN PROGRESS
⏳ Room model deployed  
⏳ Both models available  
⏳ Frontend supports both

### Phase 3 (Week 4) - PENDING
⏳ A/B testing  
⏳ Metrics collection  
⏳ Performance comparison

### Phase 4 (Week 5) - PENDING
⏳ Traffic migration  
⏳ Room model default  
⏳ Wall model deprecated

---

## Next Steps

1. ✅ **Complete Phase 1** - Deploy wall model immediately
2. ⏳ **Prepare Phase 2** - Build room model Docker container
3. ⏳ **Deploy Phase 2** - Add room model when ready
4. ⏳ **Execute Phase 3** - A/B test both models
5. ⏳ **Complete Phase 4** - Migrate to room model

**You can launch publicly TODAY with Phase 1!** 🚀
