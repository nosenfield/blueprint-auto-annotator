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
mock_models = MagicMock()
mock_image_utils = MagicMock()

# Create mock modules
import types
shared_models = types.ModuleType('shared.models')
shared_image_utils = types.ModuleType('shared.image_utils')

# Mock the classes and functions
mock_wall = Mock()
mock_wall.id = "wall_001"
mock_wall.bounding_box = (10, 20, 50, 60)
mock_wall.confidence = 0.85

shared_models.WallDetectionRequest = Mock
shared_models.WallDetectionResponse = Mock
shared_models.ErrorResponse = Mock

shared_image_utils.decode_base64_image = Mock(return_value=np.zeros((200, 200, 3), dtype=np.uint8))
shared_image_utils.validate_image_dimensions = Mock(return_value=(True, ""))

sys.modules['shared.models'] = shared_models
sys.modules['shared.image_utils'] = shared_image_utils

from app.main import app


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    def test_root_endpoint(self):
        """Test root health check endpoint"""
        with patch('app.main.detector', None):
            client = TestClient(app)
            response = client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "wall-detection-v1"
            assert data["status"] == "healthy"
            assert data["model_loaded"] == False
    
    def test_health_endpoint_when_detector_loaded(self):
        """Test /health endpoint when detector is loaded"""
        with patch('app.main.detector') as mock_detector:
            mock_detector.get_model_info.return_value = {
                "model_path": "/app/models/best_wall_model.pt",
                "confidence_threshold": 0.10,
                "model_loaded": True
            }
            
            client = TestClient(app)
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "model_info" in data
    
    def test_health_endpoint_when_detector_not_loaded(self):
        """Test /health endpoint when detector is not loaded"""
        with patch('app.main.detector', None):
            client = TestClient(app)
            response = client.get("/health")
            
            assert response.status_code == 503


class TestDetectWallsEndpoint:
    """Tests for /api/detect-walls endpoint"""
    
    def test_detect_walls_with_valid_request(self):
        """Test wall detection with valid request"""
        # Create mock detector
        mock_detector = Mock()
        mock_detector.detect.return_value = (
            [
                {"id": "wall_001", "bounding_box": [10, 20, 50, 60], "confidence": 0.85},
                {"id": "wall_002", "bounding_box": [100, 120, 150, 170], "confidence": 0.75}
            ],
            123.45
        )
        
        with patch('app.main.detector', mock_detector):
            with patch('shared.image_utils.decode_base64_image') as mock_decode:
                with patch('shared.image_utils.validate_image_dimensions') as mock_validate:
                    mock_decode.return_value = np.zeros((200, 200, 3), dtype=np.uint8)
                    mock_validate.return_value = (True, "")
                    
                    client = TestClient(app)
                    
                    # Create valid request
                    request_data = {
                        "image": "base64encodedstring",
                        "confidence_threshold": 0.10
                    }
                    
                    response = client.post("/api/detect-walls", json=request_data)
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] == True
                    assert len(data["walls"]) == 2
                    assert data["total_walls"] == 2
                    assert data["image_dimensions"] == (200, 200)
                    assert "processing_time_ms" in data
    
    def test_detect_walls_with_invalid_base64(self):
        """Test wall detection with invalid base64 image"""
        with patch('shared.image_utils.decode_base64_image') as mock_decode:
            mock_decode.side_effect = ValueError("Failed to decode image")
            
            client = TestClient(app)
            
            request_data = {
                "image": "invalid_base64",
                "confidence_threshold": 0.10
            }
            
            response = client.post("/api/detect-walls", json=request_data)
            
            assert response.status_code == 400
            assert "Failed to decode" in response.json()["detail"]
    
    def test_detect_walls_with_image_too_large(self):
        """Test wall detection with image that's too large"""
        with patch('shared.image_utils.decode_base64_image') as mock_decode:
            with patch('shared.image_utils.validate_image_dimensions') as mock_validate:
                # Create large image
                large_image = np.zeros((5000, 5000, 3), dtype=np.uint8)
                mock_decode.return_value = large_image
                mock_validate.return_value = (False, "Image too large: 5000x5000 (max: 4096x4096)")
                
                client = TestClient(app)
                
                request_data = {
                    "image": "base64encodedstring",
                    "confidence_threshold": 0.10
                }
                
                response = client.post("/api/detect-walls", json=request_data)
                
                assert response.status_code == 400
                assert "too large" in response.json()["detail"].lower()
    
    def test_detect_walls_with_image_too_small(self):
        """Test wall detection with image that's too small"""
        with patch('shared.image_utils.decode_base64_image') as mock_decode:
            with patch('shared.image_utils.validate_image_dimensions') as mock_validate:
                # Create small image
                small_image = np.zeros((50, 50, 3), dtype=np.uint8)
                mock_decode.return_value = small_image
                mock_validate.return_value = (False, "Image too small: 50x50 (min: 100x100)")
                
                client = TestClient(app)
                
                request_data = {
                    "image": "base64encodedstring",
                    "confidence_threshold": 0.10
                }
                
                response = client.post("/api/detect-walls", json=request_data)
                
                assert response.status_code == 400
                assert "too small" in response.json()["detail"].lower()
    
    def test_detect_walls_with_custom_confidence_threshold(self):
        """Test wall detection with custom confidence threshold"""
        mock_detector = Mock()
        mock_detector.detect.return_value = ([], 50.0)
        
        with patch('app.main.detector', mock_detector):
            with patch('shared.image_utils.decode_base64_image') as mock_decode:
                with patch('shared.image_utils.validate_image_dimensions') as mock_validate:
                    mock_decode.return_value = np.zeros((200, 200, 3), dtype=np.uint8)
                    mock_validate.return_value = (True, "")
                    
                    client = TestClient(app)
                    
                    request_data = {
                        "image": "base64encodedstring",
                        "confidence_threshold": 0.15
                    }
                    
                    response = client.post("/api/detect-walls", json=request_data)
                    
                    assert response.status_code == 200
                    # Verify detector was called with custom threshold
                    mock_detector.detect.assert_called_once()
                    call_args = mock_detector.detect.call_args
                    assert call_args[1]['confidence_threshold'] == 0.15
    
    def test_detect_walls_error_handling(self):
        """Test error handling in wall detection"""
        mock_detector = Mock()
        mock_detector.detect.side_effect = Exception("Model inference failed")
        
        with patch('app.main.detector', mock_detector):
            with patch('shared.image_utils.decode_base64_image') as mock_decode:
                with patch('shared.image_utils.validate_image_dimensions') as mock_validate:
                    mock_decode.return_value = np.zeros((200, 200, 3), dtype=np.uint8)
                    mock_validate.return_value = (True, "")
                    
                    client = TestClient(app)
                    
                    request_data = {
                        "image": "base64encodedstring",
                        "confidence_threshold": 0.10
                    }
                    
                    response = client.post("/api/detect-walls", json=request_data)
                    
                    assert response.status_code == 500
                    assert "Detection failed" in response.json()["detail"]


class TestLambdaHandler:
    """Tests for Lambda handler"""
    
    def test_lambda_handler_exists(self):
        """Test that Lambda handler is defined"""
        from app.main import handler
        assert handler is not None
        assert callable(handler)

