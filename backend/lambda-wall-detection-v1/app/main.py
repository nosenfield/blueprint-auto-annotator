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
# Support both Docker (/app/shared) and local development (../shared)
if os.path.exists('/app/shared'):
    # Docker environment
    sys.path.insert(0, '/app')
else:
    # Local development - add backend directory so 'shared' can be imported
    _backend_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sys.path.insert(0, os.path.abspath(_backend_path))

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
    global detector
    start_time = time.time()

    try:
        # Lazy initialization for Lambda (startup event doesn't always fire)
        if detector is None:
            print("Lazy-initializing wall detector...")
            detector = WallDetector()
            print("Wall detector ready")

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


# Lambda handler with CORS support
# Following POC pattern: create_response function ensures CORS headers are always present
mangum_handler = Mangum(app, lifespan="off")


def create_response(status_code: int, body: dict) -> dict:
    """
    Create Lambda response for API Gateway with CORS headers.
    Following POC pattern to ensure CORS headers are always present.
    
    Args:
        status_code: HTTP status code
        body: Response body dictionary
        
    Returns:
        Lambda response object with CORS headers
    """
    import json
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # CORS
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS,GET'
        },
        'body': json.dumps(body)
    }


def handler(event, context):
    """
    Lambda handler - delegates to Mangum for FastAPI integration.
    FastAPI CORSMiddleware handles CORS headers automatically.
    Handles warmup events from EventBridge.
    """
    import json
    import traceback

    # Handle warmup events from EventBridge
    if isinstance(event, dict) and event.get('warmup'):
        print("Warmup event received - keeping Lambda warm")
        # Ensure detector is initialized
        global detector
        if detector is None:
            print("Initializing detector on warmup...")
            detector = WallDetector()
            print("Detector initialized")
        else:
            print("Detector already initialized (warm)")

        return create_response(200, {
            'success': True,
            'message': 'Lambda warmed up',
            'model_loaded': detector is not None
        })

    try:
        # Call Mangum handler (it handles async internally)
        # FastAPI CORSMiddleware will add CORS headers automatically
        response = mangum_handler(event, context)

        # Ensure body is a string if it exists
        if 'body' in response and not isinstance(response['body'], str):
            response['body'] = json.dumps(response['body'])

        return response

    except Exception as e:
        # If handler fails, return error response
        error_details = traceback.format_exc()
        print(f"Lambda handler error: {error_details}")

        return create_response(500, {
            'success': False,
            'error': 'Internal server error',
            'message': str(e),
            'error_type': type(e).__name__
        })

