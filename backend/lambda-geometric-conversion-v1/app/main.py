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
from app.geometric import GeometricRoomConverter


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


@app.get("/health")
async def health():
    """Detailed health check"""
    if converter is None:
        raise HTTPException(status_code=503, detail="Converter not initialized")
    
    return {
        "status": "healthy",
        "converter_info": {
            "min_room_area": converter.min_room_area,
            "kernel_size": converter.kernel_size,
            "epsilon_factor": converter.epsilon_factor
        }
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
    global converter
    start_time = time.time()

    try:
        # Lazy initialization for Lambda (startup event doesn't always fire)
        if converter is None:
            print("Lazy-initializing geometric converter...")
            converter = GeometricRoomConverter()
            print("Converter ready")

        # Extract data
        walls = [wall.dict() for wall in request.walls]
        width, height = request.image_dimensions

        # Update converter min_room_area if specified in request
        if request.min_room_area and request.min_room_area != converter.min_room_area:
            # Create new converter with custom min_room_area
            temp_converter = GeometricRoomConverter(
                min_room_area=request.min_room_area,
                kernel_size=converter.kernel_size,
                epsilon_factor=converter.epsilon_factor
            )
            rooms, processing_time = temp_converter.convert(walls, width, height)
        else:
            # Convert walls to rooms
            rooms, processing_time = converter.convert(walls, width, height)
        
        # Create visualization if requested
        visualization = None
        if request.return_visualization and rooms:
            # Create white background image
            blank = np.ones((height, width, 3), dtype=np.uint8) * 255

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
    """
    import json
    import traceback

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

