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
    walls: List[Wall] = Field(..., min_length=1)
    image_dimensions: Tuple[int, int] = Field(..., description="[width, height]")
    min_room_area: Optional[int] = Field(2000, ge=100, le=100000)
    return_visualization: Optional[bool] = Field(True)
    
    model_config = {
        "json_schema_extra": {
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

