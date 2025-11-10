"""
Unit tests for shared image utilities.
Tests image encoding, decoding, validation, and manipulation.
"""
import pytest
import numpy as np
import cv2
import base64
from io import BytesIO
from PIL import Image

# Import utilities
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.image_utils import (
    decode_base64_image,
    encode_image_to_base64,
    validate_image_dimensions,
    resize_if_needed,
    draw_rooms_on_image,
)


class TestDecodeBase64Image:
    """Tests for decode_base64_image function"""
    
    def test_decode_valid_base64_image(self):
        """Test decoding valid base64 image"""
        # Create a simple test image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img.fill(255)  # White image
        
        # Encode to base64
        success, buffer = cv2.imencode('.png', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Decode
        decoded = decode_base64_image(img_base64)
        
        assert decoded is not None
        assert decoded.shape == (100, 100, 3)
        assert decoded.dtype == np.uint8
    
    def test_decode_base64_with_data_url_prefix(self):
        """Test decoding base64 with data URL prefix"""
        # Create test image
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        success, buffer = cv2.imencode('.png', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Add data URL prefix
        data_url = f"data:image/png;base64,{img_base64}"
        
        # Decode should handle prefix
        decoded = decode_base64_image(data_url)
        assert decoded is not None
        assert decoded.shape == (50, 50, 3)
    
    def test_decode_invalid_base64(self):
        """Test decoding invalid base64 raises error"""
        with pytest.raises(ValueError):
            decode_base64_image("invalid_base64_string!!!")


class TestEncodeImageToBase64:
    """Tests for encode_image_to_base64 function"""
    
    def test_encode_image_to_base64_png(self):
        """Test encoding image to base64 PNG"""
        # Create test image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img.fill(128)  # Gray image
        
        # Encode
        encoded = encode_image_to_base64(img, format="png")
        
        assert encoded is not None
        assert isinstance(encoded, str)
        # Should be valid base64
        decoded_data = base64.b64decode(encoded)
        assert len(decoded_data) > 0
    
    def test_encode_image_to_base64_jpg(self):
        """Test encoding image to base64 JPG"""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img.fill(128)
        
        encoded = encode_image_to_base64(img, format="jpg")
        
        assert encoded is not None
        assert isinstance(encoded, str)
    
    def test_encode_invalid_format(self):
        """Test encoding with invalid format raises error"""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        with pytest.raises(ValueError):
            encode_image_to_base64(img, format="invalid")


class TestValidateImageDimensions:
    """Tests for validate_image_dimensions function"""
    
    def test_validate_valid_dimensions(self):
        """Test validating valid image dimensions"""
        img = np.zeros((1000, 1000, 3), dtype=np.uint8)
        is_valid, error_msg = validate_image_dimensions(img, max_size=4096)
        
        assert is_valid == True
        assert error_msg == ""
    
    def test_validate_too_large_image(self):
        """Test validating image that's too large"""
        img = np.zeros((5000, 5000, 3), dtype=np.uint8)
        is_valid, error_msg = validate_image_dimensions(img, max_size=4096)
        
        assert is_valid == False
        assert "too large" in error_msg.lower()
    
    def test_validate_too_small_image(self):
        """Test validating image that's too small"""
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        is_valid, error_msg = validate_image_dimensions(img, max_size=4096)
        
        assert is_valid == False
        assert "too small" in error_msg.lower()
    
    def test_validate_empty_image(self):
        """Test validating empty image"""
        img = np.array([])
        is_valid, error_msg = validate_image_dimensions(img)
        
        assert is_valid == False
        assert "empty" in error_msg.lower()


class TestResizeIfNeeded:
    """Tests for resize_if_needed function"""
    
    def test_resize_image_that_needs_resizing(self):
        """Test resizing image that exceeds max_size"""
        # Create large image
        img = np.zeros((3000, 3000, 3), dtype=np.uint8)
        
        resized, scale = resize_if_needed(img, max_size=2048)
        
        assert resized is not None
        assert scale < 1.0  # Should be scaled down
        h, w = resized.shape[:2]
        assert max(w, h) <= 2048
    
    def test_resize_image_that_doesnt_need_resizing(self):
        """Test resizing image that doesn't need resizing"""
        img = np.zeros((1000, 1000, 3), dtype=np.uint8)
        
        resized, scale = resize_if_needed(img, max_size=2048)
        
        assert resized is not None
        assert scale == 1.0  # Should not be scaled
        assert np.array_equal(resized, img)
    
    def test_resize_maintains_aspect_ratio(self):
        """Test resizing maintains aspect ratio"""
        # Create wide image
        img = np.zeros((1000, 3000, 3), dtype=np.uint8)
        
        resized, scale = resize_if_needed(img, max_size=2048)
        
        h, w = resized.shape[:2]
        original_ratio = 3000 / 1000
        resized_ratio = w / h
        
        # Aspect ratio should be maintained (within floating point error)
        assert abs(original_ratio - resized_ratio) < 0.01


class TestDrawRoomsOnImage:
    """Tests for draw_rooms_on_image function"""
    
    def test_draw_rooms_on_image(self):
        """Test drawing rooms on image"""
        # Create test image
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        img.fill(255)  # White background
        
        # Create test room (using Room model)
        from shared.models import Room, BoundingBox
        
        bbox = BoundingBox(x_min=50, y_min=50, x_max=150, y_max=150)
        room = Room(
            id="room_001",
            polygon_vertices=[(50, 50), (150, 50), (150, 150), (50, 150)],
            bounding_box=bbox,
            area_pixels=10000,
            centroid=(100, 100),
            confidence=0.9,
            shape_type="rectangle",
            num_vertices=4
        )
        
        # Draw rooms
        result = draw_rooms_on_image(img, [room])
        
        assert result is not None
        assert result.shape == img.shape
        # Image should be modified (not identical)
        assert not np.array_equal(result, img)
    
    def test_draw_multiple_rooms(self):
        """Test drawing multiple rooms"""
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        img.fill(255)
        
        from shared.models import Room, BoundingBox
        
        rooms = []
        for i in range(3):
            bbox = BoundingBox(
                x_min=50 + i*100,
                y_min=50 + i*100,
                x_max=150 + i*100,
                y_max=150 + i*100
            )
            room = Room(
                id=f"room_{i+1:03d}",
                polygon_vertices=[
                    (50 + i*100, 50 + i*100),
                    (150 + i*100, 50 + i*100),
                    (150 + i*100, 150 + i*100),
                    (50 + i*100, 150 + i*100)
                ],
                bounding_box=bbox,
                area_pixels=10000,
                centroid=(100 + i*100, 100 + i*100),
                confidence=0.9,
                shape_type="rectangle",
                num_vertices=4
            )
            rooms.append(room)
        
        result = draw_rooms_on_image(img, rooms)
        
        assert result is not None
        assert result.shape == img.shape
    
    def test_draw_rooms_with_custom_colors(self):
        """Test drawing rooms with custom colors"""
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        img.fill(255)
        
        from shared.models import Room, BoundingBox
        
        bbox = BoundingBox(x_min=50, y_min=50, x_max=150, y_max=150)
        room = Room(
            id="room_001",
            polygon_vertices=[(50, 50), (150, 50), (150, 150), (50, 150)],
            bounding_box=bbox,
            area_pixels=10000,
            centroid=(100, 100),
            confidence=0.9,
            shape_type="rectangle",
            num_vertices=4
        )
        
        custom_colors = [(255, 0, 0)]  # Blue
        result = draw_rooms_on_image(img, [room], colors=custom_colors)
        
        assert result is not None

