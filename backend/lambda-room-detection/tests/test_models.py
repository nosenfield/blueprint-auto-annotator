"""
Unit tests for Pydantic models
"""
import pytest
from pydantic import ValidationError
from app.models import Wall, Room, RoomDetectionRequest, RoomDetectionResponse, BoundingBox


class TestWall:
    """Test Wall model"""
    
    def test_valid_wall(self):
        """Test valid wall creation"""
        wall = Wall(
            id="wall_001",
            bounding_box=(10, 20, 30, 40),
            confidence=0.85
        )
        
        assert wall.id == "wall_001"
        assert wall.bounding_box == (10, 20, 30, 40)
        assert wall.confidence == 0.85
    
    def test_wall_invalid_confidence(self):
        """Test wall with invalid confidence"""
        with pytest.raises(ValidationError):
            Wall(
                id="wall_001",
                bounding_box=(10, 20, 30, 40),
                confidence=1.5  # > 1.0
            )
        
        with pytest.raises(ValidationError):
            Wall(
                id="wall_001",
                bounding_box=(10, 20, 30, 40),
                confidence=-0.1  # < 0.0
            )


class TestBoundingBox:
    """Test BoundingBox model"""
    
    def test_valid_bounding_box(self):
        """Test valid bounding box creation"""
        bbox = BoundingBox(x_min=10, y_min=20, x_max=30, y_max=40)
        
        assert bbox.x_min == 10
        assert bbox.y_min == 20
        assert bbox.x_max == 30
        assert bbox.y_max == 40


class TestRoom:
    """Test Room model"""
    
    def test_valid_room(self):
        """Test valid room creation"""
        room = Room(
            id="room_001",
            polygon_vertices=[(10, 10), (40, 10), (40, 40), (10, 40)],
            bounding_box=BoundingBox(x_min=10, y_min=10, x_max=40, y_max=40),
            area_pixels=900,
            centroid=(25, 25),
            confidence=0.85,
            shape_type="rectangle",
            num_vertices=4
        )
        
        assert room.id == "room_001"
        assert len(room.polygon_vertices) == 4
        assert room.area_pixels == 900
        assert room.shape_type == "rectangle"
    
    def test_room_invalid_shape_type(self):
        """Test room with invalid shape type"""
        with pytest.raises(ValidationError):
            Room(
                id="room_001",
                polygon_vertices=[(10, 10), (40, 10), (40, 40), (10, 40)],
                bounding_box=BoundingBox(x_min=10, y_min=10, x_max=40, y_max=40),
                area_pixels=900,
                centroid=(25, 25),
                confidence=0.85,
                shape_type="invalid",  # Not in allowed values
                num_vertices=4
            )


class TestRoomDetectionRequest:
    """Test RoomDetectionRequest model"""
    
    def test_valid_request(self):
        """Test valid request creation"""
        walls = [
            Wall(id="wall_001", bounding_box=(10, 10, 20, 90), confidence=0.85),
        ]
        
        request = RoomDetectionRequest(
            walls=walls,
            image_dimensions=(100, 100)
        )
        
        assert len(request.walls) == 1
        assert request.image_dimensions == (100, 100)
        assert request.min_room_area == 2000  # Default
        assert request.return_visualization == True  # Default
    
    def test_request_empty_walls(self):
        """Test request with empty walls list"""
        with pytest.raises(ValidationError):
            RoomDetectionRequest(
                walls=[],
                image_dimensions=(100, 100)
            )
    
    def test_request_invalid_min_room_area(self):
        """Test request with invalid min_room_area"""
        walls = [
            Wall(id="wall_001", bounding_box=(10, 10, 20, 90), confidence=0.85),
        ]
        
        with pytest.raises(ValidationError):
            RoomDetectionRequest(
                walls=walls,
                image_dimensions=(100, 100),
                min_room_area=50  # < 100
            )


class TestRoomDetectionResponse:
    """Test RoomDetectionResponse model"""
    
    def test_valid_response(self):
        """Test valid response creation"""
        rooms = [
            Room(
                id="room_001",
                polygon_vertices=[(10, 10), (40, 10), (40, 40), (10, 40)],
                bounding_box=BoundingBox(x_min=10, y_min=10, x_max=40, y_max=40),
                area_pixels=900,
                centroid=(25, 25),
                confidence=0.85,
                shape_type="rectangle",
                num_vertices=4
            ),
        ]
        
        response = RoomDetectionResponse(
            success=True,
            rooms=rooms,
            visualization="base64_string",
            total_rooms=1,
            processing_time_ms=50.5,
            metadata={"test": "data"}
        )
        
        assert response.success == True
        assert len(response.rooms) == 1
        assert response.total_rooms == 1
        assert response.visualization == "base64_string"

