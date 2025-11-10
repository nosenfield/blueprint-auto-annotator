"""
Unit tests for shared Pydantic models.
Tests validation, serialization, and model behavior.
"""
import pytest
from typing import List, Tuple
from pydantic import ValidationError

# Import models
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.models import (
    BoundingBox,
    Room,
    DetectionRequest,
    DetectionResponse,
    ErrorResponse,
    Wall,
    WallDetectionRequest,
    WallDetectionResponse,
    GeometricConversionRequest,
)


class TestBoundingBox:
    """Tests for BoundingBox model"""
    
    def test_valid_bounding_box(self):
        """Test creating valid bounding box"""
        bbox = BoundingBox(x_min=0, y_min=0, x_max=100, y_max=100)
        assert bbox.x_min == 0
        assert bbox.y_min == 0
        assert bbox.x_max == 100
        assert bbox.y_max == 100
    
    def test_bounding_box_serialization(self):
        """Test bounding box can be serialized to dict"""
        bbox = BoundingBox(x_min=10, y_min=20, x_max=110, y_max=120)
        data = bbox.model_dump()
        assert data["x_min"] == 10
        assert data["y_max"] == 120


class TestRoom:
    """Tests for Room model"""
    
    def test_valid_room(self):
        """Test creating valid room"""
        bbox = BoundingBox(x_min=0, y_min=0, x_max=100, y_max=100)
        room = Room(
            id="room_001",
            polygon_vertices=[(0, 0), (100, 0), (100, 100), (0, 100)],
            bounding_box=bbox,
            area_pixels=10000,
            centroid=(50, 50),
            confidence=0.95,
            shape_type="rectangle",
            num_vertices=4
        )
        assert room.id == "room_001"
        assert len(room.polygon_vertices) == 4
        assert room.confidence == 0.95
        assert room.shape_type == "rectangle"
    
    def test_room_confidence_validation(self):
        """Test room confidence must be between 0 and 1"""
        bbox = BoundingBox(x_min=0, y_min=0, x_max=100, y_max=100)
        
        # Valid confidence
        room = Room(
            id="room_001",
            polygon_vertices=[(0, 0), (100, 0), (100, 100), (0, 100)],
            bounding_box=bbox,
            area_pixels=10000,
            centroid=(50, 50),
            confidence=0.5,
            shape_type="rectangle",
            num_vertices=4
        )
        assert room.confidence == 0.5
        
        # Invalid confidence (too high)
        with pytest.raises(ValidationError):
            Room(
                id="room_001",
                polygon_vertices=[(0, 0), (100, 0), (100, 100), (0, 100)],
                bounding_box=bbox,
                area_pixels=10000,
                centroid=(50, 50),
                confidence=1.5,  # Invalid
                shape_type="rectangle",
                num_vertices=4
            )
        
        # Invalid confidence (negative)
        with pytest.raises(ValidationError):
            Room(
                id="room_001",
                polygon_vertices=[(0, 0), (100, 0), (100, 100), (0, 100)],
                bounding_box=bbox,
                area_pixels=10000,
                centroid=(50, 50),
                confidence=-0.1,  # Invalid
                shape_type="rectangle",
                num_vertices=4
            )
    
    def test_room_shape_type_validation(self):
        """Test room shape_type must be valid literal"""
        bbox = BoundingBox(x_min=0, y_min=0, x_max=100, y_max=100)
        
        # Valid shape types
        for shape_type in ["rectangle", "l_shape", "complex"]:
            room = Room(
                id="room_001",
                polygon_vertices=[(0, 0), (100, 0), (100, 100), (0, 100)],
                bounding_box=bbox,
                area_pixels=10000,
                centroid=(50, 50),
                confidence=0.9,
                shape_type=shape_type,
                num_vertices=4
            )
            assert room.shape_type == shape_type
        
        # Invalid shape type
        with pytest.raises(ValidationError):
            Room(
                id="room_001",
                polygon_vertices=[(0, 0), (100, 0), (100, 100), (0, 100)],
                bounding_box=bbox,
                area_pixels=10000,
                centroid=(50, 50),
                confidence=0.9,
                shape_type="invalid",  # Invalid
                num_vertices=4
            )


class TestDetectionRequest:
    """Tests for DetectionRequest model"""
    
    def test_valid_detection_request_v1(self):
        """Test creating valid detection request for v1"""
        request = DetectionRequest(
            image="base64encodedstring",
            version="v1"
        )
        assert request.image == "base64encodedstring"
        assert request.version == "v1"
        assert request.confidence_threshold == 0.10  # Default
        assert request.min_room_area == 2000  # Default
        assert request.return_visualization == True  # Default
    
    def test_valid_detection_request_v2(self):
        """Test creating valid detection request for v2"""
        request = DetectionRequest(
            image="base64encodedstring",
            version="v2",
            confidence_threshold=0.15,
            min_room_area=3000,
            enable_refinement=True
        )
        assert request.version == "v2"
        assert request.confidence_threshold == 0.15
        assert request.min_room_area == 3000
        assert request.enable_refinement == True
    
    def test_detection_request_confidence_validation(self):
        """Test confidence threshold validation"""
        # Valid confidence
        request = DetectionRequest(
            image="base64",
            confidence_threshold=0.5
        )
        assert request.confidence_threshold == 0.5
        
        # Invalid confidence (too high)
        with pytest.raises(ValidationError):
            DetectionRequest(
                image="base64",
                confidence_threshold=1.5  # Invalid
            )
        
        # Invalid confidence (negative)
        with pytest.raises(ValidationError):
            DetectionRequest(
                image="base64",
                confidence_threshold=-0.1  # Invalid
            )
    
    def test_detection_request_version_validation(self):
        """Test version must be v1 or v2"""
        # Valid versions
        for version in ["v1", "v2"]:
            request = DetectionRequest(image="base64", version=version)
            assert request.version == version
        
        # Invalid version
        with pytest.raises(ValidationError):
            DetectionRequest(image="base64", version="v3")  # Invalid


class TestDetectionResponse:
    """Tests for DetectionResponse model"""
    
    def test_valid_detection_response(self):
        """Test creating valid detection response"""
        bbox = BoundingBox(x_min=0, y_min=0, x_max=100, y_max=100)
        room = Room(
            id="room_001",
            polygon_vertices=[(0, 0), (100, 0), (100, 100), (0, 100)],
            bounding_box=bbox,
            area_pixels=10000,
            centroid=(50, 50),
            confidence=0.95,
            shape_type="rectangle",
            num_vertices=4
        )
        
        response = DetectionResponse(
            success=True,
            rooms=[room],
            total_rooms=1,
            processing_time_ms=123.45,
            model_version="v1",
            visualization="base64image",
            metadata={"key": "value"}
        )
        assert response.success == True
        assert len(response.rooms) == 1
        assert response.total_rooms == 1
        assert response.model_version == "v1"
        assert response.visualization == "base64image"
    
    def test_detection_response_without_visualization(self):
        """Test detection response without visualization"""
        response = DetectionResponse(
            success=True,
            rooms=[],
            total_rooms=0,
            processing_time_ms=50.0,
            model_version="v2"
        )
        assert response.visualization is None
        assert response.metadata == {}


class TestErrorResponse:
    """Tests for ErrorResponse model"""
    
    def test_valid_error_response(self):
        """Test creating valid error response"""
        error = ErrorResponse(
            error={"message": "Something went wrong", "code": 500},
            model_version="v1"
        )
        assert error.success == False  # Default
        assert error.error["message"] == "Something went wrong"
        assert error.model_version == "v1"
    
    def test_error_response_without_version(self):
        """Test error response without model version"""
        error = ErrorResponse(
            error={"message": "Error"}
        )
        assert error.model_version is None


class TestWall:
    """Tests for Wall model"""
    
    def test_valid_wall(self):
        """Test creating valid wall"""
        wall = Wall(
            id="wall_001",
            bounding_box=(0, 0, 100, 200),
            confidence=0.85
        )
        assert wall.id == "wall_001"
        assert wall.bounding_box == (0, 0, 100, 200)
        assert wall.confidence == 0.85
    
    def test_wall_confidence_validation(self):
        """Test wall confidence validation"""
        # Valid confidence
        wall = Wall(id="wall_001", bounding_box=(0, 0, 100, 100), confidence=0.5)
        assert wall.confidence == 0.5
        
        # Invalid confidence
        with pytest.raises(ValidationError):
            Wall(id="wall_001", bounding_box=(0, 0, 100, 100), confidence=1.5)


class TestWallDetectionRequest:
    """Tests for WallDetectionRequest model"""
    
    def test_valid_wall_detection_request(self):
        """Test creating valid wall detection request"""
        request = WallDetectionRequest(
            image="base64encodedstring",
            confidence_threshold=0.15
        )
        assert request.image == "base64encodedstring"
        assert request.confidence_threshold == 0.15
        assert request.image_format == "png"  # Default


class TestWallDetectionResponse:
    """Tests for WallDetectionResponse model"""
    
    def test_valid_wall_detection_response(self):
        """Test creating valid wall detection response"""
        wall = Wall(id="wall_001", bounding_box=(0, 0, 100, 200), confidence=0.85)
        response = WallDetectionResponse(
            success=True,
            walls=[wall],
            total_walls=1,
            image_dimensions=(800, 600),
            processing_time_ms=234.56
        )
        assert response.success == True
        assert len(response.walls) == 1
        assert response.total_walls == 1
        assert response.image_dimensions == (800, 600)


class TestGeometricConversionRequest:
    """Tests for GeometricConversionRequest model"""
    
    def test_valid_geometric_conversion_request(self):
        """Test creating valid geometric conversion request"""
        wall = Wall(id="wall_001", bounding_box=(0, 0, 100, 200), confidence=0.85)
        request = GeometricConversionRequest(
            walls=[wall],
            image_dimensions=(800, 600),
            min_room_area=3000,
            return_visualization=True
        )
        assert len(request.walls) == 1
        assert request.image_dimensions == (800, 600)
        assert request.min_room_area == 3000
        assert request.return_visualization == True

