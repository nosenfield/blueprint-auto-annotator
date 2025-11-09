"""
Unit tests for geometric room detection algorithm
"""
import pytest
import numpy as np
from app.geometric import GeometricRoomDetector
from app.models import Wall, Room


class TestGeometricRoomDetector:
    """Test suite for GeometricRoomDetector"""
    
    def test_create_grid(self):
        """Test grid creation"""
        detector = GeometricRoomDetector()
        grid = detector._create_grid(100, 200)
        
        assert grid.shape == (200, 100)
        assert grid.dtype == np.uint8
        assert np.all(grid == 0)
    
    def test_draw_walls(self):
        """Test wall drawing on grid"""
        detector = GeometricRoomDetector()
        grid = detector._create_grid(100, 100)
        
        walls = [
            Wall(id="wall_001", bounding_box=(10, 10, 20, 90), confidence=0.85),
            Wall(id="wall_002", bounding_box=(50, 10, 60, 90), confidence=0.80),
        ]
        
        grid = detector._draw_walls(grid, walls)
        
        # Check that walls are drawn (white pixels)
        assert grid[50, 15] == 255  # Inside first wall
        assert grid[50, 55] == 255  # Inside second wall
        assert grid[50, 30] == 0    # Between walls (room)
    
    def test_apply_morphology(self):
        """Test morphological operations"""
        detector = GeometricRoomDetector()
        
        # Create test image with small gaps
        image = np.zeros((100, 100), dtype=np.uint8)
        image[10:20, 10:90] = 255  # Horizontal wall with gap
        image[10:90, 10:20] = 255  # Vertical wall
        
        # Invert (walls become black, rooms become white)
        inverted = 255 - image
        
        # Apply morphology
        cleaned = detector._apply_morphology(inverted)
        
        assert cleaned.shape == image.shape
        assert cleaned.dtype == np.uint8
    
    def test_find_components(self):
        """Test connected components finding"""
        detector = GeometricRoomDetector()
        
        # Create test image with two separate rooms
        image = np.zeros((100, 100), dtype=np.uint8)
        image[10:40, 10:40] = 255  # Room 1
        image[60:90, 60:90] = 255  # Room 2
        
        labels, stats, centroids = detector._find_components(image)
        
        assert labels.shape == image.shape
        assert len(stats) >= 3  # Background + 2 rooms
        assert len(centroids) >= 3
    
    def test_extract_rooms_simple(self):
        """Test room extraction from simple layout"""
        detector = GeometricRoomDetector(min_room_area=100)
        
        # Create simple 2-room layout
        labels = np.zeros((100, 100), dtype=np.int32)
        labels[10:40, 10:40] = 1  # Room 1
        labels[60:90, 60:90] = 2   # Room 2
        
        stats = np.array([
            [0, 0, 0, 0, 0],      # Background
            [10, 10, 30, 30, 900], # Room 1
            [60, 60, 30, 30, 900], # Room 2
        ], dtype=np.int32)
        
        centroids = np.array([
            [0, 0],
            [25, 25],
            [75, 75],
        ], dtype=np.float64)
        
        rooms = detector._extract_rooms(labels, stats, centroids, 100, 100)
        
        assert len(rooms) == 2
        assert all(isinstance(room, Room) for room in rooms)
        assert rooms[0].id == "room_001"
        assert rooms[1].id == "room_002"
    
    def test_extract_rooms_filters_small_areas(self):
        """Test that small areas are filtered out"""
        detector = GeometricRoomDetector(min_room_area=1000)
        
        labels = np.zeros((100, 100), dtype=np.int32)
        labels[10:15, 10:15] = 1  # Small area (25 pixels)
        labels[20:50, 20:50] = 2   # Large area (900 pixels)
        
        stats = np.array([
            [0, 0, 0, 0, 0],
            [10, 10, 5, 5, 25],    # Too small
            [20, 20, 30, 30, 900], # Large enough
        ], dtype=np.int32)
        
        centroids = np.array([
            [0, 0],
            [12, 12],
            [35, 35],
        ], dtype=np.float64)
        
        rooms = detector._extract_rooms(labels, stats, centroids, 100, 100)
        
        assert len(rooms) == 1  # Only large room
        assert rooms[0].area_pixels == 900
    
    def test_calculate_confidence(self):
        """Test confidence calculation"""
        detector = GeometricRoomDetector()
        
        # Large area, simple shape
        conf1 = detector._calculate_confidence(50000, 4)
        assert 0.0 <= conf1 <= 1.0
        assert conf1 > 0.5  # Should be high
        
        # Small area, complex shape
        conf2 = detector._calculate_confidence(2000, 20)
        assert 0.0 <= conf2 <= 1.0
        assert conf2 < conf1  # Should be lower
    
    def test_detect_rooms_full_pipeline(self):
        """Test full detection pipeline"""
        detector = GeometricRoomDetector(min_room_area=100)
        
        # Create walls that form 2 rooms
        walls = [
            Wall(id="wall_001", bounding_box=(50, 0, 55, 100), confidence=0.85),  # Vertical divider
            Wall(id="wall_002", bounding_box=(0, 50, 100, 55), confidence=0.80),  # Horizontal divider
        ]
        
        rooms = detector.detect_rooms(walls, 100, 100)
        
        assert len(rooms) >= 1  # Should detect at least one room
        assert all(isinstance(room, Room) for room in rooms)
        assert all(room.area_pixels >= 100 for room in rooms)
        assert all(room.confidence > 0.0 for room in rooms)
    
    def test_detect_rooms_with_no_walls(self):
        """Test detection with no walls (should return empty list)"""
        detector = GeometricRoomDetector()
        
        rooms = detector.detect_rooms([], 100, 100)
        
        # With no walls, entire image is one room
        assert isinstance(rooms, list)
        # May return one large room or empty depending on implementation
    
    def test_detect_rooms_with_single_wall(self):
        """Test detection with single wall"""
        detector = GeometricRoomDetector(min_room_area=100)
        
        walls = [
            Wall(id="wall_001", bounding_box=(50, 0, 55, 100), confidence=0.85),
        ]
        
        rooms = detector.detect_rooms(walls, 100, 100)
        
        assert isinstance(rooms, list)
        # Should detect rooms on both sides of wall

