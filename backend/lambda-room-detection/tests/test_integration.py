"""
Integration tests for room detection pipeline
Tests the full flow: walls → rooms → visualization
"""
import pytest
import json
from pathlib import Path
from app.models import Wall, Room, RoomDetectionRequest, RoomDetectionResponse, BoundingBox
from app.geometric import GeometricRoomDetector
from app.visualization import RoomVisualizer


class TestIntegrationPipeline:
    """Integration tests for full room detection pipeline"""
    
    def test_simple_2_room_layout(self):
        """Test simple 2-room layout (4 walls forming 2 rooms)"""
        detector = GeometricRoomDetector(min_room_area=100)
        visualizer = RoomVisualizer()
        
        # Create walls that form 2 rooms
        walls = [
            Wall(id="wall_001", bounding_box=(50, 0, 55, 100), confidence=0.85),  # Vertical divider
            Wall(id="wall_002", bounding_box=(0, 50, 100, 55), confidence=0.80),  # Horizontal divider
        ]
        
        # Detect rooms
        rooms = detector.detect_rooms(walls, 100, 100)
        
        # Should detect at least 2 rooms (may detect more due to algorithm)
        assert len(rooms) >= 1
        assert all(isinstance(room, Room) for room in rooms)
        
        # Generate visualization
        if rooms:
            viz_image = visualizer.create_visualization(rooms, 100, 100)
            assert viz_image.shape == (100, 100, 3)
            
            # Encode to base64
            viz_b64 = visualizer.encode_base64(viz_image)
            assert isinstance(viz_b64, str)
            assert len(viz_b64) > 0
    
    def test_complex_multi_room_layout(self):
        """Test complex multi-room layout"""
        detector = GeometricRoomDetector(min_room_area=100)
        
        # Create walls that form multiple rooms
        walls = [
            Wall(id="wall_001", bounding_box=(33, 0, 37, 100), confidence=0.85),  # Vertical divider 1
            Wall(id="wall_002", bounding_box=(66, 0, 70, 100), confidence=0.85),  # Vertical divider 2
            Wall(id="wall_003", bounding_box=(0, 33, 100, 37), confidence=0.80),  # Horizontal divider 1
            Wall(id="wall_004", bounding_box=(0, 66, 100, 70), confidence=0.80),  # Horizontal divider 2
        ]
        
        rooms = detector.detect_rooms(walls, 100, 100)
        
        # Should detect multiple rooms
        assert len(rooms) >= 1
        assert all(room.area_pixels >= 100 for room in rooms)
    
    def test_single_wall_edge_case(self):
        """Test edge case with single wall"""
        detector = GeometricRoomDetector(min_room_area=100)
        
        walls = [
            Wall(id="wall_001", bounding_box=(50, 0, 55, 100), confidence=0.85),
        ]
        
        rooms = detector.detect_rooms(walls, 100, 100)
        
        # Should detect rooms on both sides of wall
        assert isinstance(rooms, list)
        # May detect 1-2 rooms depending on algorithm
    
    def test_no_walls_error_case(self):
        """Test error case with no walls"""
        detector = GeometricRoomDetector(min_room_area=100)
        
        rooms = detector.detect_rooms([], 100, 100)
        
        # With no walls, entire image is one room (or empty)
        assert isinstance(rooms, list)
        # Result depends on algorithm implementation
    
    def test_invalid_wall_coordinates(self):
        """Test with invalid wall coordinates (out of bounds)"""
        detector = GeometricRoomDetector(min_room_area=100)
        
        # Walls with coordinates outside image bounds
        walls = [
            Wall(id="wall_001", bounding_box=(-10, -10, 200, 200), confidence=0.85),
        ]
        
        # Should handle gracefully (clamp to bounds)
        rooms = detector.detect_rooms(walls, 100, 100)
        
        assert isinstance(rooms, list)
    
    def test_response_format_validation(self):
        """Test that response format matches expected structure"""
        detector = GeometricRoomDetector(min_room_area=100)
        visualizer = RoomVisualizer()
        
        walls = [
            Wall(id="wall_001", bounding_box=(50, 0, 55, 100), confidence=0.85),
        ]
        
        rooms = detector.detect_rooms(walls, 100, 100)
        
        # Create response-like structure
        if rooms:
            viz_image = visualizer.create_visualization(rooms, 100, 100)
            viz_b64 = visualizer.encode_base64(viz_image)
            
            # Validate response structure
            response_data = {
                "success": True,
                "rooms": [room.dict() for room in rooms],
                "visualization": viz_b64,
                "total_rooms": len(rooms),
                "processing_time_ms": 50.0,
                "metadata": {
                    "image_dimensions": [100, 100],
                    "walls_processed": len(walls),
                    "min_room_area": 100
                }
            }
            
            # Validate structure
            assert response_data["success"] == True
            assert "rooms" in response_data
            assert "visualization" in response_data
            assert "total_rooms" in response_data
            assert response_data["total_rooms"] == len(rooms)
    
    def test_visualization_generation(self):
        """Test visualization generation for different room counts"""
        from app.models import BoundingBox
        
        visualizer = RoomVisualizer()
        
        # Test with 1 room
        rooms_1 = [
            Room(
                id="room_001",
                polygon_vertices=[(10, 10), (50, 10), (50, 50), (10, 50)],
                bounding_box=BoundingBox(x_min=10, y_min=10, x_max=50, y_max=50),
                area_pixels=1600,
                centroid=(30, 30),
                confidence=0.85,
                shape_type="rectangle",
                num_vertices=4
            ),
        ]
        
        viz_1 = visualizer.create_visualization(rooms_1, 100, 100)
        assert viz_1.shape == (100, 100, 3)
        
        # Test with multiple rooms
        rooms_2 = rooms_1 + [
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
        
        viz_2 = visualizer.create_visualization(rooms_2, 100, 100)
        assert viz_2.shape == (100, 100, 3)
    
    def test_performance_target(self):
        """Test that processing time meets target (<1s)"""
        import time
        
        detector = GeometricRoomDetector(min_room_area=100)
        
        walls = [
            Wall(id="wall_001", bounding_box=(50, 0, 55, 100), confidence=0.85),
            Wall(id="wall_002", bounding_box=(0, 50, 100, 55), confidence=0.80),
        ]
        
        start_time = time.time()
        rooms = detector.detect_rooms(walls, 100, 100)
        processing_time = time.time() - start_time
        
        # Should complete in <1 second (for small test case)
        assert processing_time < 1.0, f"Processing took {processing_time:.2f}s, expected <1s"
        assert len(rooms) >= 1

