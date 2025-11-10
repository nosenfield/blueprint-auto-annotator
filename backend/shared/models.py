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
    model_config = {"protected_namespaces": ()}
    
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
    model_config = {"protected_namespaces": ()}
    
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

