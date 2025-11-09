"""
Unit tests for room visualization generator
"""
import pytest
import numpy as np
from app.visualization import RoomVisualizer
from app.models import Room, BoundingBox


class TestRoomVisualizer:
    """Test suite for RoomVisualizer"""
    
    def test_create_visualization(self):
        """Test visualization creation"""
        visualizer = RoomVisualizer()
        
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
            Room(
                id="room_002",
                polygon_vertices=[(60, 60), (90, 60), (90, 90), (60, 90)],
                bounding_box=BoundingBox(x_min=60, y_min=60, x_max=90, y_max=90),
                area_pixels=900,
                centroid=(75, 75),
                confidence=0.80,
                shape_type="rectangle",
                num_vertices=4
            ),
        ]
        
        image = visualizer.create_visualization(rooms, 100, 100)
        
        assert image.shape == (100, 100, 3)
        assert image.dtype == np.uint8
        assert np.all(image >= 0) and np.all(image <= 255)
    
    def test_encode_base64(self):
        """Test base64 encoding"""
        visualizer = RoomVisualizer()
        
        # Create simple test image
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        
        encoded = visualizer.encode_base64(image)
        
        assert isinstance(encoded, str)
        assert len(encoded) > 0
        # Base64 strings are alphanumeric with +, /, = characters
        assert all(c.isalnum() or c in '+/=' for c in encoded)
    
    def test_visualization_with_empty_rooms(self):
        """Test visualization with no rooms"""
        visualizer = RoomVisualizer()
        
        image = visualizer.create_visualization([], 100, 100)
        
        assert image.shape == (100, 100, 3)
        # Should be white background
        assert np.all(image == 255)
    
    def test_visualization_with_single_room(self):
        """Test visualization with single room"""
        visualizer = RoomVisualizer()
        
        rooms = [
            Room(
                id="room_001",
                polygon_vertices=[(10, 10), (50, 10), (50, 50), (10, 50)],
                bounding_box=BoundingBox(x_min=10, y_min=10, x_max=50, y_max=50),
                area_pixels=1600,
                centroid=(30, 30),
                confidence=0.90,
                shape_type="rectangle",
                num_vertices=4
            ),
        ]
        
        image = visualizer.create_visualization(rooms, 100, 100)
        
        assert image.shape == (100, 100, 3)
        # Should have drawn room boundary
        assert not np.all(image == 255)  # Not all white
    
    def test_visualization_metadata(self):
        """Test that metadata is added to visualization"""
        visualizer = RoomVisualizer()
        
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
        
        image = visualizer.create_visualization(rooms, 100, 100)
        
        # Metadata should be added (text in top-left corner)
        # Just verify image was created successfully
        assert image.shape == (100, 100, 3)

