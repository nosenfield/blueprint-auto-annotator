"""
Geometric algorithm for converting walls to rooms.
Uses morphological operations and connected components.
"""
import cv2
import numpy as np
from typing import List, Tuple
import time


class GeometricRoomConverter:
    """
    Converts wall detections to room polygons using geometric analysis.
    
    Algorithm:
    1. Create binary grid
    2. Draw walls on grid
    3. Invert (walls -> black, spaces -> white)
    4. Apply morphological operations (closing, opening)
    5. Find connected components
    6. Extract polygons from components
    7. Simplify polygons
    """
    
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
            epsilon_factor: Polygon simplification factor (0.01 = 1% of perimeter)
        """
        self.min_room_area = min_room_area
        self.kernel_size = kernel_size
        self.epsilon_factor = epsilon_factor
        self.kernel = np.ones((kernel_size, kernel_size), np.uint8)
    
    def convert(
        self,
        walls: List[dict],
        width: int,
        height: int
    ) -> Tuple[List[dict], float]:
        """
        Convert walls to room polygons.
        
        Args:
            walls: List of wall dicts with 'bounding_box' key
            width: Image width
            height: Image height
            
        Returns:
            Tuple of (rooms_list, processing_time_ms)
        """
        start_time = time.time()
        
        # Step 1: Create binary grid
        grid = self._create_grid(width, height)
        
        # Step 2: Draw walls
        grid = self._draw_walls(grid, walls)
        
        # Step 3: Invert
        inverted = 255 - grid
        
        # Step 4: Morphological operations
        cleaned = self._apply_morphology(inverted)
        
        # Step 5: Connected components
        labels, stats, centroids = self._find_components(cleaned)
        
        # Step 6: Extract room polygons
        rooms = self._extract_rooms(labels, stats, centroids, width, height)
        
        processing_time = (time.time() - start_time) * 1000
        
        return rooms, processing_time
    
    def _create_grid(self, width: int, height: int) -> np.ndarray:
        """Create empty binary grid"""
        return np.zeros((height, width), dtype=np.uint8)
    
    def _draw_walls(self, grid: np.ndarray, walls: List[dict]) -> np.ndarray:
        """Draw walls on grid as white rectangles"""
        for wall in walls:
            x1, y1, x2, y2 = wall['bounding_box']
            
            # Clip to grid bounds
            h, w = grid.shape
            x1 = max(0, min(x1, w - 1))
            x2 = max(0, min(x2, w - 1))
            y1 = max(0, min(y1, h - 1))
            y2 = max(0, min(y2, h - 1))
            
            # Draw filled rectangle (wall)
            cv2.rectangle(grid, (x1, y1), (x2, y2), 255, -1)
        
        return grid
    
    def _apply_morphology(self, image: np.ndarray) -> np.ndarray:
        """Apply morphological operations to clean image"""
        # Closing: Fill small gaps in walls
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, self.kernel)
        
        # Opening: Remove small noise
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, self.kernel)
        
        return opened
    
    def _find_components(
        self,
        image: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Find connected components (rooms)"""
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
    ) -> List[dict]:
        """Extract room polygons from connected components"""
        rooms = []
        max_area = width * height * 0.9  # Exclude background
        
        num_labels = len(stats)
        
        for label in range(1, num_labels):  # Skip background (label 0)
            x, y, w, h, area = stats[label]
            
            # Filter by area
            if area < self.min_room_area or area > max_area:
                continue
            
            # Create mask for this component
            mask = (labels == label).astype(np.uint8) * 255
            
            # Find contours
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
            
            # Calculate centroid
            cx, cy = int(centroids[label][0]), int(centroids[label][1])
            
            # Determine shape type
            num_vertices = len(vertices)
            if num_vertices == 4:
                shape_type = "rectangle"
            elif num_vertices <= 8:
                shape_type = "l_shape"
            else:
                shape_type = "complex"
            
            # Calculate confidence based on shape regularity
            confidence = self._calculate_confidence(vertices, area)
            
            rooms.append({
                "id": f"room_{len(rooms)+1:03d}",
                "polygon_vertices": vertices,
                "bounding_box": {
                    "x_min": x,
                    "y_min": y,
                    "x_max": x + w,
                    "y_max": y + h
                },
                "area_pixels": int(area),
                "centroid": (cx, cy),
                "confidence": confidence,
                "shape_type": shape_type,
                "num_vertices": num_vertices
            })
        
        return rooms
    
    def _calculate_confidence(self, vertices: List[Tuple[int, int]], area: int) -> float:
        """
        Calculate confidence score based on shape regularity.
        More regular shapes (rectangles) get higher confidence.
        """
        num_vertices = len(vertices)
        
        # Base confidence on vertex count
        if num_vertices == 4:
            return 0.95
        elif num_vertices <= 6:
            return 0.85
        elif num_vertices <= 8:
            return 0.75
        else:
            return 0.65

