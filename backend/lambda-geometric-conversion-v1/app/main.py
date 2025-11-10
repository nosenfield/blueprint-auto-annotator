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
    start_time = time.time()
    
    try:
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

