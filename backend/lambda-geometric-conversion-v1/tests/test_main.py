"""
Unit tests for FastAPI application.
Tests endpoints, error handling, and Lambda handler.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock shared module before importing main
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

# Mock the shared models and utilities
import types
shared_models = types.ModuleType('shared.models')
shared_image_utils = types.ModuleType('shared.image_utils')

# Mock the classes and functions
shared_models.GeometricConversionRequest = Mock
shared_models.DetectionResponse = Mock
shared_models.Room = Mock
shared_models.ErrorResponse = Mock

shared_image_utils.draw_rooms_on_image = Mock(return_value=np.zeros((200, 200, 3), dtype=np.uint8))
shared_image_utils.encode_image_to_base64 = Mock(return_value="base64encodedimage")

sys.modules['shared.models'] = shared_models
sys.modules['shared.image_utils'] = shared_image_utils

from app.main import app


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    def test_root_endpoint(self):
        """Test root health check endpoint"""
        with patch('app.main.converter', None):
            client = TestClient(app)
            response = client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "geometric-conversion-v1"
            assert data["status"] == "healthy"
            assert data["converter_loaded"] == False
    
    def test_health_endpoint_when_converter_loaded(self):
        """Test /health endpoint when converter is loaded"""
        with patch('app.main.converter') as mock_converter:
            mock_converter.get_model_info.return_value = {
                "min_room_area": 2000,
                "kernel_size": 3,
                "epsilon_factor": 0.01
            }
            
            client = TestClient(app)
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
    
    def test_health_endpoint_when_converter_not_loaded(self):
        """Test /health endpoint when converter is not loaded"""
        with patch('app.main.converter', None):
            client = TestClient(app)
            response = client.get("/health")
            
            assert response.status_code == 503


class TestConvertToRoomsEndpoint:
    """Tests for /api/convert-to-rooms endpoint"""
    
    def test_convert_to_rooms_with_valid_request(self):
        """Test room conversion with valid request"""
        # Create mock converter
        mock_converter = Mock()
        mock_converter.convert.return_value = (
            [
                {
                    "id": "room_001",
                    "polygon_vertices": [(10, 10), (90, 10), (90, 90), (10, 90)],
                    "bounding_box": {"x_min": 10, "y_min": 10, "x_max": 90, "y_max": 90},
                    "area_pixels": 6400,
                    "centroid": (50, 50),
                    "confidence": 0.95,
                    "shape_type": "rectangle",
                    "num_vertices": 4
                }
            ],
            123.45
        )
        
        with patch('app.main.converter', mock_converter):
            client = TestClient(app)
            
            # Create valid request
            request_data = {
                "walls": [
                    {"id": "wall_001", "bounding_box": [50, 0, 55, 100], "confidence": 0.85}
                ],
                "image_dimensions": [100, 100],
                "min_room_area": 2000,
                "return_visualization": True
            }
            
            response = client.post("/api/convert-to-rooms", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert len(data["rooms"]) == 1
            assert data["total_rooms"] == 1
            assert data["model_version"] == "v1"
            assert "processing_time_ms" in data
            assert "visualization" in data
    
    def test_convert_to_rooms_without_visualization(self):
        """Test room conversion without visualization"""
        mock_converter = Mock()
        mock_converter.convert.return_value = ([], 50.0)
        
        with patch('app.main.converter', mock_converter):
            client = TestClient(app)
            
            request_data = {
                "walls": [
                    {"id": "wall_001", "bounding_box": [50, 0, 55, 100], "confidence": 0.85}
                ],
                "image_dimensions": [100, 100],
                "return_visualization": False
            }
            
            response = client.post("/api/convert-to-rooms", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            # Visualization should be None when not requested
            assert data.get("visualization") is None or data["visualization"] is None
    
    def test_convert_to_rooms_with_empty_walls(self):
        """Test room conversion with empty walls list"""
        mock_converter = Mock()
        mock_converter.convert.return_value = ([], 50.0)
        
        with patch('app.main.converter', mock_converter):
            client = TestClient(app)
            
            request_data = {
                "walls": [],
                "image_dimensions": [100, 100],
                "return_visualization": False
            }
            
            response = client.post("/api/convert-to-rooms", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["total_rooms"] == 0
    
    def test_convert_to_rooms_with_custom_min_room_area(self):
        """Test room conversion with custom min_room_area"""
        mock_converter = Mock()
        mock_converter.convert.return_value = ([], 50.0)
        
        with patch('app.main.converter', mock_converter):
            client = TestClient(app)
            
            request_data = {
                "walls": [
                    {"id": "wall_001", "bounding_box": [50, 0, 55, 100], "confidence": 0.85}
                ],
                "image_dimensions": [100, 100],
                "min_room_area": 5000,
                "return_visualization": False
            }
            
            response = client.post("/api/convert-to-rooms", json=request_data)
            
            assert response.status_code == 200
            # Note: min_room_area is passed to converter, but converter is initialized with default
            # In real implementation, we'd need to handle this differently
    
    def test_convert_to_rooms_error_handling(self):
        """Test error handling in room conversion"""
        mock_converter = Mock()
        mock_converter.convert.side_effect = Exception("Conversion failed")
        
        with patch('app.main.converter', mock_converter):
            client = TestClient(app)
            
            request_data = {
                "walls": [
                    {"id": "wall_001", "bounding_box": [50, 0, 55, 100], "confidence": 0.85}
                ],
                "image_dimensions": [100, 100],
                "return_visualization": False
            }
            
            response = client.post("/api/convert-to-rooms", json=request_data)
            
            assert response.status_code == 500
            assert "Conversion failed" in response.json()["detail"]
    
    def test_convert_to_rooms_with_visualization(self):
        """Test room conversion with visualization enabled"""
        mock_converter = Mock()
        mock_room = {
            "id": "room_001",
            "polygon_vertices": [(10, 10), (90, 10), (90, 90), (10, 90)],
            "bounding_box": {"x_min": 10, "y_min": 10, "x_max": 90, "y_max": 90},
            "area_pixels": 6400,
            "centroid": (50, 50),
            "confidence": 0.95,
            "shape_type": "rectangle",
            "num_vertices": 4
        }
        mock_converter.convert.return_value = ([mock_room], 123.45)
        
        with patch('app.main.converter', mock_converter):
            with patch('shared.image_utils.draw_rooms_on_image') as mock_draw:
                with patch('shared.image_utils.encode_image_to_base64') as mock_encode:
                    mock_draw.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
                    mock_encode.return_value = "base64encodedimage"
                    
                    client = TestClient(app)
                    
                    request_data = {
                        "walls": [
                            {"id": "wall_001", "bounding_box": [50, 0, 55, 100], "confidence": 0.85}
                        ],
                        "image_dimensions": [100, 100],
                        "return_visualization": True
                    }
                    
                    response = client.post("/api/convert-to-rooms", json=request_data)
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["visualization"] == "base64encodedimage"
                    mock_draw.assert_called_once()
                    mock_encode.assert_called_once()


class TestLambdaHandler:
    """Tests for Lambda handler"""
    
    def test_lambda_handler_exists(self):
        """Test that Lambda handler is defined"""
        from app.main import handler
        assert handler is not None
        assert callable(handler)

