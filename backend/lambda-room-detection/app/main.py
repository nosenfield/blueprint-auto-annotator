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

