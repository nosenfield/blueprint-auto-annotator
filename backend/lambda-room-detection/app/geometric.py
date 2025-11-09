"""
Geometric algorithm for wall-to-room conversion
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Any
from .models import Wall, Room, BoundingBox


class GeometricRoomDetector:
    """Converts wall detections to room polygons using geometric analysis"""
    
    def __init__(
        self, 
        min_room_area: int = 2000,
        kernel_size: int = 3,
        epsilon_factor: float = 0.01
    ):
        """
        Args:
            min_room_area: Minimum area in pixels to consider as room
            kernel_size: Size of morphological kernel
            epsilon_factor: Polygon simplification factor
        """
        self.min_room_area = min_room_area
        self.kernel_size = kernel_size
        self.epsilon_factor = epsilon_factor
        self.kernel = np.ones((kernel_size, kernel_size), np.uint8)
    
    def detect_rooms(
        self, 
        walls: List[Wall], 
        width: int, 
        height: int
    ) -> List[Room]:
        """
        Main detection pipeline
        
        Args:
            walls: List of detected walls
            width: Image width in pixels
            height: Image height in pixels
            
        Returns:
            List of detected rooms
        """
        # Step 1: Create binary grid
        grid = self._create_grid(width, height)
        
        # Step 2: Draw walls
        grid = self._draw_walls(grid, walls)
        
        # Step 3: Invert (walls become black, rooms become white)
        inverted = 255 - grid
        
        # Step 4: Apply morphological operations
        cleaned = self._apply_morphology(inverted)
        
        # Step 5: Find connected components
        labels, stats, centroids = self._find_components(cleaned)
        
        # Step 6: Extract room polygons
        rooms = self._extract_rooms(
            labels, 
            stats, 
            centroids, 
            width, 
            height
        )
        
        return rooms
    
    def _create_grid(self, width: int, height: int) -> np.ndarray:
        """Create binary grid"""
        return np.zeros((height, width), dtype=np.uint8)
    
    def _draw_walls(self, grid: np.ndarray, walls: List[Wall]) -> np.ndarray:
        """Draw walls on grid"""
        for wall in walls:
            x1, y1, x2, y2 = wall.bounding_box
            
            # Ensure coordinates are within bounds
            h, w = grid.shape
            x1 = max(0, min(x1, w - 1))
            x2 = max(0, min(x2, w - 1))
            y1 = max(0, min(y1, h - 1))
            y2 = max(0, min(y2, h - 1))
            
            # Draw filled rectangle
            cv2.rectangle(grid, (x1, y1), (x2, y2), 255, -1)
        
        return grid
    
    def _apply_morphology(self, image: np.ndarray) -> np.ndarray:
        """Apply morphological operations to clean up"""
        # Closing: Fill small gaps in walls
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, self.kernel)
        
        # Opening: Remove small white noise
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, self.kernel)
        
        return opened
    
    def _find_components(
        self, 
        image: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Find connected components"""
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            image, 
            connectivity=8
        )
        
        return labels, stats, centroids
    
    def _extract_rooms(
        self,
        labels: np.ndarray,
        stats: np.ndarray,
        centroids: np.ndarray,
        width: int,
        height: int
    ) -> List[Room]:
        """Extract room polygons from connected components"""
        rooms = []
        max_area = width * height * 0.9  # Exclude background
        
        num_labels = len(stats)
        
        for label in range(1, num_labels):  # Skip background (0)
            x, y, w, h, area = stats[label]
            
            # Filter by area
            if area < self.min_room_area or area > max_area:
                continue
            
            # Get polygon
            mask = (labels == label).astype(np.uint8) * 255
            contours, _ = cv2.findContours(
                mask, 
                cv2.RETR_EXTERNAL, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            if not contours:
                continue
            
            # Get largest contour
            contour = max(contours, key=cv2.contourArea)
            
            # Simplify polygon
            epsilon = self.epsilon_factor * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Convert to list of tuples
            vertices = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]
            
            # Determine shape type
            num_vertices = len(vertices)
            if num_vertices == 4:
                shape_type = "rectangle"
            elif num_vertices <= 6:
                shape_type = "l_shape"
            else:
                shape_type = "complex"
            
            # Calculate confidence
            confidence = self._calculate_confidence(area, num_vertices)
            
            # Create room object
            room = Room(
                id=f"room_{len(rooms) + 1:03d}",
                polygon_vertices=vertices,
                bounding_box=BoundingBox(
                    x_min=int(x),
                    y_min=int(y),
                    x_max=int(x + w),
                    y_max=int(y + h)
                ),
                area_pixels=int(area),
                centroid=(int(centroids[label][0]), int(centroids[label][1])),
                confidence=confidence,
                shape_type=shape_type,
                num_vertices=num_vertices
            )
            
            rooms.append(room)
        
        # Sort by area (largest first)
        rooms.sort(key=lambda r: r.area_pixels, reverse=True)
        
        return rooms
    
    def _calculate_confidence(self, area: int, num_vertices: int) -> float:
        """
        Calculate confidence score based on area and shape complexity
        
        Args:
            area: Room area in pixels
            num_vertices: Number of polygon vertices
            
        Returns:
            Confidence score between 0 and 1
        """
        # Larger rooms = higher confidence
        area_score = min(area / 50000, 1.0)
        
        # Simpler shapes = higher confidence
        vertex_score = 1.0 - (min(num_vertices, 20) / 20) * 0.3
        
        # Weighted combination
        confidence = (area_score * 0.7 + vertex_score * 0.3)
        
        return round(confidence, 2)

