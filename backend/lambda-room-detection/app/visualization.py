"""
Visualization generation for detected rooms
"""
import cv2
import numpy as np
import base64
from typing import List, Tuple
from .models import Room


class RoomVisualizer:
    """Generates visualization of detected room boundaries"""
    
    # Color palette for room visualization
    COLORS = [
        (255, 0, 0),      # Blue
        (0, 255, 0),      # Green
        (0, 0, 255),      # Red
        (255, 255, 0),    # Cyan
        (255, 0, 255),    # Magenta
        (0, 255, 255),    # Yellow
        (128, 0, 255),    # Purple
        (255, 128, 0),    # Orange
        (0, 255, 128),    # Spring green
        (128, 255, 0),    # Chartreuse
    ]
    
    def __init__(self, font_scale: float = 0.5, line_thickness: int = 2):
        """
        Args:
            font_scale: Font size for labels
            line_thickness: Thickness of boundary lines
        """
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = font_scale
        self.line_thickness = line_thickness
    
    def create_visualization(
        self, 
        rooms: List[Room], 
        width: int, 
        height: int,
        background_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> np.ndarray:
        """
        Create visualization image with room boundaries
        
        Args:
            rooms: List of detected rooms
            width: Image width
            height: Image height
            background_color: Background color (BGR)
            
        Returns:
            Visualization image as numpy array
        """
        # Create white canvas
        image = np.full((height, width, 3), background_color, dtype=np.uint8)
        
        # Draw each room
        for i, room in enumerate(rooms):
            color = self.COLORS[i % len(self.COLORS)]
            
            # Draw polygon
            vertices = np.array(room.polygon_vertices, dtype=np.int32)
            cv2.polylines(
                image, 
                [vertices], 
                isClosed=True, 
                color=color, 
                thickness=self.line_thickness
            )
            
            # Draw bounding box (lighter)
            bbox = room.bounding_box
            cv2.rectangle(
                image,
                (bbox.x_min, bbox.y_min),
                (bbox.x_max, bbox.y_max),
                color,
                1
            )
            
            # Add label at centroid
            cx, cy = room.centroid
            label = f"{room.id}"
            
            # Draw text background
            (text_w, text_h), _ = cv2.getTextSize(
                label, 
                self.font, 
                self.font_scale, 
                self.line_thickness
            )
            
            cv2.rectangle(
                image,
                (cx - 5, cy - text_h - 5),
                (cx + text_w + 5, cy + 5),
                color,
                -1
            )
            
            # Draw text
            cv2.putText(
                image,
                label,
                (cx, cy),
                self.font,
                self.font_scale,
                (255, 255, 255),
                self.line_thickness
            )
            
            # Add shape info
            info = f"{room.shape_type}"
            cv2.putText(
                image,
                info,
                (cx, cy + 15),
                self.font,
                self.font_scale * 0.7,
                color,
                1
            )
        
        # Add metadata
        self._add_metadata(image, len(rooms))
        
        return image
    
    def _add_metadata(self, image: np.ndarray, total_rooms: int):
        """Add metadata text to image"""
        text = f"Detected: {total_rooms} rooms"
        cv2.putText(
            image,
            text,
            (10, 30),
            self.font,
            0.8,
            (0, 255, 0),
            2
        )
    
    def encode_base64(self, image: np.ndarray) -> str:
        """
        Encode image to base64 string
        
        Args:
            image: OpenCV image (numpy array)
            
        Returns:
            Base64 encoded string
        """
        # Encode to PNG
        success, buffer = cv2.imencode('.png', image)
        
        if not success:
            raise ValueError("Failed to encode image to PNG")
        
        # Convert to base64
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return img_base64

