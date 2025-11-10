"""
Unit tests for GeometricRoomConverter class.
Tests geometric algorithm, room extraction, and error handling.
"""
import pytest
import numpy as np
import cv2
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.geometric import GeometricRoomConverter


class TestGeometricRoomConverter:
    """Tests for GeometricRoomConverter class"""
    
    def test_init_with_default_parameters(self):
        """Test GeometricRoomConverter initialization with default parameters"""
        converter = GeometricRoomConverter()
        
        assert converter.min_room_area == 2000
        assert converter.kernel_size == 3
        assert converter.epsilon_factor == 0.01
        assert converter.kernel.shape == (3, 3)
    
    def test_init_with_custom_parameters(self):
        """Test GeometricRoomConverter initialization with custom parameters"""
        converter = GeometricRoomConverter(
            min_room_area=3000,
            kernel_size=5,
            epsilon_factor=0.02
        )
        
        assert converter.min_room_area == 3000
        assert converter.kernel_size == 5
        assert converter.epsilon_factor == 0.02
        assert converter.kernel.shape == (5, 5)
    
    def test_create_grid(self):
        """Test grid creation"""
        converter = GeometricRoomConverter()
        grid = converter._create_grid(100, 200)
        
        assert grid.shape == (200, 100)
        assert grid.dtype == np.uint8
        assert np.all(grid == 0)
    
    def test_draw_walls(self):
        """Test wall drawing on grid"""
        converter = GeometricRoomConverter()
        grid = converter._create_grid(100, 100)
        
        walls = [
            {"id": "wall_001", "bounding_box": [10, 10, 20, 90], "confidence": 0.85},
            {"id": "wall_002", "bounding_box": [50, 10, 60, 90], "confidence": 0.80},
        ]
        
        grid = converter._draw_walls(grid, walls)
        
        # Check that walls are drawn (white pixels)
        assert grid[50, 15] == 255  # Inside first wall
        assert grid[50, 55] == 255  # Inside second wall
        assert grid[50, 30] == 0    # Between walls (room)
    
    def test_draw_walls_clips_to_bounds(self):
        """Test wall drawing clips coordinates to grid bounds"""
        converter = GeometricRoomConverter()
        grid = converter._create_grid(100, 100)
        
        # Wall with coordinates outside bounds
        walls = [
            {"id": "wall_001", "bounding_box": [-10, -10, 150, 150], "confidence": 0.85},
        ]
        
        grid = converter._draw_walls(grid, walls)
        
        # Should not raise error and should clip to bounds
        assert grid.shape == (100, 100)
    
    def test_apply_morphology(self):
        """Test morphological operations"""
        converter = GeometricRoomConverter()
        
        # Create test image with small gaps
        image = np.zeros((100, 100), dtype=np.uint8)
        image[10:20, 10:90] = 255  # Horizontal wall with gap
        image[10:90, 10:20] = 255  # Vertical wall
        
        # Apply morphology
        cleaned = converter._apply_morphology(image)
        
        assert cleaned.shape == image.shape
        assert cleaned.dtype == np.uint8
    
    def test_find_components(self):
        """Test connected components finding"""
        converter = GeometricRoomConverter()
        
        # Create test image with 2 connected components
        image = np.zeros((100, 100), dtype=np.uint8)
        image[10:40, 10:40] = 255  # First component
        image[60:90, 60:90] = 255  # Second component
        
        labels, stats, centroids = converter._find_components(image)
        
        assert labels.shape == (100, 100)
        assert len(stats) >= 3  # Background + 2 components
        assert len(centroids) >= 3
    
    def test_extract_rooms(self):
        """Test room extraction from connected components"""
        converter = GeometricRoomConverter(min_room_area=100)
        
        # Create test image with 2 rooms
        image = np.zeros((100, 100), dtype=np.uint8)
        image[10:40, 10:40] = 255  # First room
        image[60:90, 60:90] = 255  # Second room
        
        labels, stats, centroids = converter._find_components(image)
        rooms = converter._extract_rooms(labels, stats, centroids, 100, 100)
        
        assert len(rooms) >= 1
        assert all(isinstance(room, dict) for room in rooms)
        assert all("id" in room for room in rooms)
        assert all("polygon_vertices" in room for room in rooms)
        assert all("bounding_box" in room for room in rooms)
        assert all("area_pixels" in room for room in rooms)
        assert all("centroid" in room for room in rooms)
        assert all("confidence" in room for room in rooms)
        assert all("shape_type" in room for room in rooms)
        assert all("num_vertices" in room for room in rooms)
    
    def test_extract_rooms_filters_by_area(self):
        """Test room extraction filters by minimum area"""
        converter = GeometricRoomConverter(min_room_area=5000)
        
        # Create test image with small component (should be filtered)
        image = np.zeros((100, 100), dtype=np.uint8)
        image[10:20, 10:20] = 255  # Small component (100 pixels)
        
        labels, stats, centroids = converter._find_components(image)
        rooms = converter._extract_rooms(labels, stats, centroids, 100, 100)
        
        # Small component should be filtered out
        assert all(room["area_pixels"] >= 5000 for room in rooms)
    
    def test_calculate_confidence(self):
        """Test confidence calculation based on shape regularity"""
        converter = GeometricRoomConverter()
        
        # Rectangle (4 vertices) should have high confidence
        vertices_rect = [(0, 0), (100, 0), (100, 100), (0, 100)]
        conf_rect = converter._calculate_confidence(vertices_rect, 10000)
        assert conf_rect == 0.95
        
        # Complex shape (many vertices) should have lower confidence
        vertices_complex = [(0, 0), (50, 0), (100, 0), (100, 50), (100, 100), (50, 100), (0, 100), (0, 50)]
        conf_complex = converter._calculate_confidence(vertices_complex, 10000)
        assert conf_complex < conf_rect
    
    def test_convert_with_valid_wall_data(self):
        """Test convert() with valid wall data"""
        converter = GeometricRoomConverter(min_room_area=100)
        
        # Create walls that form 2 rooms
        walls = [
            {"id": "wall_001", "bounding_box": [50, 0, 55, 100], "confidence": 0.85},  # Vertical divider
            {"id": "wall_002", "bounding_box": [0, 50, 100, 55], "confidence": 0.80},  # Horizontal divider
        ]
        
        rooms, processing_time = converter.convert(walls, 100, 100)
        
        assert isinstance(rooms, list)
        assert len(rooms) >= 1  # Should detect at least one room
        assert isinstance(processing_time, float)
        assert processing_time >= 0
    
    def test_convert_with_empty_walls(self):
        """Test convert() with empty walls list"""
        converter = GeometricRoomConverter(min_room_area=100)
        
        rooms, processing_time = converter.convert([], 100, 100)
        
        # With no walls, entire image is one room (if area is large enough)
        assert isinstance(rooms, list)
        assert isinstance(processing_time, float)
    
    def test_convert_with_multiple_rooms(self):
        """Test convert() with walls forming multiple rooms"""
        converter = GeometricRoomConverter(min_room_area=100)
        
        # Create walls that form 4 rooms (2x2 grid)
        walls = [
            {"id": "wall_001", "bounding_box": [50, 0, 55, 100], "confidence": 0.85},  # Vertical divider
            {"id": "wall_002", "bounding_box": [0, 50, 100, 55], "confidence": 0.80},  # Horizontal divider
        ]
        
        rooms, processing_time = converter.convert(walls, 100, 100)
        
        assert len(rooms) >= 1  # Should detect at least one room
        assert all(isinstance(room, dict) for room in rooms)
        assert all(room["area_pixels"] >= 100 for room in rooms)
    
    def test_convert_returns_correct_format(self):
        """Test that convert() returns correct format"""
        converter = GeometricRoomConverter(min_room_area=100)
        
        walls = [
            {"id": "wall_001", "bounding_box": [50, 0, 55, 100], "confidence": 0.85},
        ]
        
        rooms, processing_time = converter.convert(walls, 100, 100)
        
        # Verify return format
        assert isinstance(rooms, list)
        if len(rooms) > 0:
            room = rooms[0]
            assert "id" in room
            assert "polygon_vertices" in room
            assert "bounding_box" in room
            assert "area_pixels" in room
            assert "centroid" in room
            assert "confidence" in room
            assert "shape_type" in room
            assert "num_vertices" in room
            assert isinstance(room["polygon_vertices"], list)
            assert isinstance(room["bounding_box"], dict)
            assert "x_min" in room["bounding_box"]
            assert "y_min" in room["bounding_box"]
            assert "x_max" in room["bounding_box"]
            assert "y_max" in room["bounding_box"]
        
        assert isinstance(processing_time, float)
        assert processing_time >= 0
    
    def test_convert_room_shape_types(self):
        """Test that convert() correctly identifies room shape types"""
        converter = GeometricRoomConverter(min_room_area=100)
        
        # Create walls forming rectangular room
        walls = [
            {"id": "wall_001", "bounding_box": [10, 10, 90, 15], "confidence": 0.85},  # Top wall
            {"id": "wall_002", "bounding_box": [10, 85, 90, 90], "confidence": 0.85},  # Bottom wall
            {"id": "wall_003", "bounding_box": [10, 10, 15, 90], "confidence": 0.85},  # Left wall
            {"id": "wall_004", "bounding_box": [85, 10, 90, 90], "confidence": 0.85},  # Right wall
        ]
        
        rooms, _ = converter.convert(walls, 100, 100)
        
        if len(rooms) > 0:
            # Should identify shape type
            assert rooms[0]["shape_type"] in ["rectangle", "l_shape", "complex"]
            assert rooms[0]["num_vertices"] >= 3

