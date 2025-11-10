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
from app.detection import WallDetector


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

