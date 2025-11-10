"""Shared utilities for all Lambda functions"""
from .models import (
    Room,
    BoundingBox,
    DetectionRequest,
    DetectionResponse,
    ErrorResponse,
    Wall,
    WallDetectionRequest,
    WallDetectionResponse,
    GeometricConversionRequest,
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
    "WallDetectionRequest",
    "WallDetectionResponse",
    "GeometricConversionRequest",
    "decode_base64_image",
    "encode_image_to_base64",
    "validate_image_dimensions",
    "resize_if_needed",
    "draw_rooms_on_image",
]

