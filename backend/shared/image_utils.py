"""
Shared image processing utilities.
Pure helper functions with no business logic.
"""
import base64
import numpy as np
import cv2
from PIL import Image
from io import BytesIO
from typing import Tuple, Optional, List


def decode_base64_image(base64_string: str) -> np.ndarray:
    """
    Decode base64 string to OpenCV image array.
    
    Args:
        base64_string: Base64 encoded image
        
    Returns:
        OpenCV image as numpy array (BGR format)
        
    Raises:
        ValueError: If base64 string is invalid
    """
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
            
        image_data = base64.b64decode(base64_string)
        image = Image.open(BytesIO(image_data))
        
        # Convert to BGR for OpenCV
        image_array = np.array(image)
        if len(image_array.shape) == 2:  # Grayscale
            image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2BGR)
        elif image_array.shape[2] == 4:  # RGBA
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2BGR)
        else:  # RGB
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
        return image_array
    except Exception as e:
        raise ValueError(f"Failed to decode image: {str(e)}")


def encode_image_to_base64(image: np.ndarray, format: str = "png") -> str:
    """
    Encode OpenCV image to base64 string.
    
    Args:
        image: OpenCV image array
        format: Image format (png, jpg)
        
    Returns:
        Base64 encoded string
        
    Raises:
        ValueError: If encoding fails
    """
    success, buffer = cv2.imencode(f'.{format}', image)
    if not success:
        raise ValueError(f"Failed to encode image as {format}")
    return base64.b64encode(buffer).decode('utf-8')


def validate_image_dimensions(
    image: np.ndarray, 
    max_size: int = 4096
) -> Tuple[bool, str]:
    """
    Validate image dimensions are within acceptable limits.
    
    Args:
        image: OpenCV image array
        max_size: Maximum dimension (width or height)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if image is None or image.size == 0:
        return False, "Image is empty"
        
    h, w = image.shape[:2]
    
    if w > max_size or h > max_size:
        return False, f"Image too large: {w}x{h} (max: {max_size}x{max_size})"
        
    if w < 100 or h < 100:
        return False, f"Image too small: {w}x{h} (min: 100x100)"
        
    return True, ""


def resize_if_needed(
    image: np.ndarray, 
    max_size: int = 2048
) -> Tuple[np.ndarray, float]:
    """
    Resize image if dimensions exceed max_size.
    Maintains aspect ratio.
    
    Args:
        image: OpenCV image array
        max_size: Maximum dimension
        
    Returns:
        Tuple of (resized_image, scale_factor)
        scale_factor is 1.0 if no resizing occurred
    """
    h, w = image.shape[:2]
    
    if w <= max_size and h <= max_size:
        return image, 1.0
    
    # Calculate scale to fit within max_size
    scale = max_size / max(w, h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    resized = cv2.resize(
        image, 
        (new_w, new_h), 
        interpolation=cv2.INTER_AREA
    )
    
    return resized, scale


def draw_rooms_on_image(
    image: np.ndarray,
    rooms: list,
    colors: Optional[List[Tuple[int, int, int]]] = None
) -> np.ndarray:
    """
    Draw detected rooms on image for visualization.
    
    Args:
        image: Original image
        rooms: List of Room objects
        colors: Optional list of BGR colors for each room
        
    Returns:
        Image with rooms drawn
    """
    overlay = image.copy()
    
    if colors is None:
        # Generate distinct colors
        colors = [
            (255, 0, 0),    # Blue
            (0, 255, 0),    # Green
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
        ]
    
    for i, room in enumerate(rooms):
        color = colors[i % len(colors)]

        # Draw polygon outline
        points = np.array(room.polygon_vertices, dtype=np.int32)
        cv2.polylines(overlay, [points], True, color, 3)

        # Draw filled polygon with transparency
        temp_mask = np.zeros_like(image)
        cv2.fillPoly(temp_mask, [points], color)
        # Only blend in the polygon region to avoid darkening the whole image
        overlay = cv2.addWeighted(overlay, 0.85, temp_mask, 0.15, 0)
        
        # Draw room ID at centroid
        cx, cy = room.centroid
        cv2.putText(
            overlay,
            room.id,
            (cx - 20, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
    
    return overlay

