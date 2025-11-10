"""
Unit tests for WallDetector class.
Tests model loading, detection, and error handling.
"""
import pytest
import numpy as np
import os
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.detection import WallDetector


class TestWallDetector:
    """Tests for WallDetector class"""
    
    def test_init_with_default_parameters(self):
        """Test WallDetector initialization with default parameters"""
        with patch('app.detection.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_yolo.return_value = mock_model
            
            with patch('os.path.exists', return_value=True):
                detector = WallDetector()
                
                assert detector.model_path == "/app/models/best_wall_model.pt"
                assert detector.confidence_threshold == 0.10
                assert detector.model is not None
    
    def test_init_with_custom_parameters(self):
        """Test WallDetector initialization with custom parameters"""
        with patch('app.detection.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_yolo.return_value = mock_model
            
            with patch('os.path.exists', return_value=True):
                detector = WallDetector(
                    model_path="/custom/path/model.pt",
                    confidence_threshold=0.15
                )
                
                assert detector.model_path == "/custom/path/model.pt"
                assert detector.confidence_threshold == 0.15
    
    def test_load_model_with_valid_file(self):
        """Test loading model with valid model file"""
        with patch('app.detection.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_yolo.return_value = mock_model
            
            with patch('os.path.exists', return_value=True):
                detector = WallDetector()
                
                mock_yolo.assert_called_once_with("/app/models/best_wall_model.pt")
                assert detector.model is not None
    
    def test_load_model_with_missing_file(self):
        """Test loading model with missing model file raises error"""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                WallDetector()
    
    def test_detect_with_valid_image(self):
        """Test wall detection with valid image"""
        with patch('app.detection.YOLO') as mock_yolo:
            # Create mock YOLO model and results
            mock_model = Mock()
            mock_box1 = Mock()
            mock_box1.xyxy = [np.array([10, 20, 50, 60])]
            mock_box1.conf = [0.85]
            
            mock_box2 = Mock()
            mock_box2.xyxy = [np.array([100, 120, 150, 170])]
            mock_box2.conf = [0.75]
            
            mock_result = Mock()
            mock_result.boxes = [mock_box1, mock_box2]
            
            mock_results = [mock_result]
            mock_model.return_value = mock_results
            mock_yolo.return_value = mock_model
            
            with patch('os.path.exists', return_value=True):
                detector = WallDetector()
                
                # Create test image
                test_image = np.zeros((200, 200, 3), dtype=np.uint8)
                
                # Run detection
                walls, inference_time = detector.detect(test_image)
                
                # Verify results
                assert len(walls) == 2
                assert walls[0]["id"] == "wall_001"
                assert walls[0]["bounding_box"] == [10, 20, 50, 60]
                assert walls[0]["confidence"] == 0.85
                assert walls[1]["id"] == "wall_002"
                assert walls[1]["bounding_box"] == [100, 120, 150, 170]
                assert walls[1]["confidence"] == 0.75
                assert inference_time >= 0
    
    def test_detect_with_custom_confidence_threshold(self):
        """Test detection with custom confidence threshold"""
        with patch('app.detection.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_result = Mock()
            mock_result.boxes = []
            mock_model.return_value = [mock_result]
            mock_yolo.return_value = mock_model
            
            with patch('os.path.exists', return_value=True):
                detector = WallDetector(confidence_threshold=0.10)
                
                test_image = np.zeros((200, 200, 3), dtype=np.uint8)
                walls, _ = detector.detect(test_image, confidence_threshold=0.15)
                
                # Verify model was called with custom threshold
                mock_model.assert_called_once()
                call_args = mock_model.call_args
                assert call_args[1]['conf'] == 0.15
    
    def test_detect_returns_correct_format(self):
        """Test that detect() returns correct format"""
        with patch('app.detection.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_box = Mock()
            mock_box.xyxy = [np.array([10, 20, 50, 60])]
            mock_box.conf = [0.85]
            
            mock_result = Mock()
            mock_result.boxes = [mock_box]
            mock_model.return_value = [mock_result]
            mock_yolo.return_value = mock_model
            
            with patch('os.path.exists', return_value=True):
                detector = WallDetector()
                
                test_image = np.zeros((200, 200, 3), dtype=np.uint8)
                walls, inference_time = detector.detect(test_image)
                
                # Verify return format
                assert isinstance(walls, list)
                assert len(walls) == 1
                assert isinstance(walls[0], dict)
                assert "id" in walls[0]
                assert "bounding_box" in walls[0]
                assert "confidence" in walls[0]
                assert isinstance(inference_time, float)
                assert inference_time >= 0
    
    def test_get_model_info(self):
        """Test get_model_info() returns correct information"""
        with patch('app.detection.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_yolo.return_value = mock_model
            
            with patch('os.path.exists', return_value=True):
                detector = WallDetector(
                    model_path="/test/model.pt",
                    confidence_threshold=0.15
                )
                
                info = detector.get_model_info()
                
                assert info["model_path"] == "/test/model.pt"
                assert info["confidence_threshold"] == 0.15
                assert info["model_loaded"] == True
    
    def test_get_model_info_when_model_not_loaded(self):
        """Test get_model_info() when model is not loaded"""
        detector = WallDetector.__new__(WallDetector)
        detector.model_path = "/test/model.pt"
        detector.confidence_threshold = 0.10
        detector.model = None
        
        info = detector.get_model_info()
        
        assert info["model_loaded"] == False

