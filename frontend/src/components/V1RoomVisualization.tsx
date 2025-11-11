import React, { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';
import type { Room } from '../types';

interface V1RoomVisualizationProps {
  imageUrl: string;
  rooms: Room[];
}

export interface V1RoomVisualizationRef {
  getCanvas: () => HTMLCanvasElement | null;
}

/**
 * Client-side Canvas component for visualizing v1 room detections.
 * Draws room polygon boundaries over the original blueprint image.
 */
export const V1RoomVisualization = forwardRef<V1RoomVisualizationRef, V1RoomVisualizationProps>(
  ({ imageUrl, rooms }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [imageLoaded, setImageLoaded] = useState(false);
    const [hoveredRoom, setHoveredRoom] = useState<string | null>(null);

    useImperativeHandle(ref, () => ({
      getCanvas: () => canvasRef.current,
    }));

    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const img = new Image();
      img.onload = () => {
        // Set canvas size to match image
        canvas.width = img.width;
        canvas.height = img.height;

        // Draw the blueprint image
        ctx.drawImage(img, 0, 0);

        // Draw room polygons
        rooms.forEach((room) => {
          const { polygon_vertices, id } = room;

          // Determine color and style based on hover state
          const isHovered = hoveredRoom === id;
          const strokeColor = isHovered ? 'rgba(0, 255, 0, 0.9)' : 'rgba(0, 200, 0, 0.7)';
          const fillColor = isHovered ? 'rgba(0, 255, 0, 0.15)' : 'rgba(0, 200, 0, 0.1)';
          const lineWidth = isHovered ? 3 : 2;

          // Draw polygon
          if (polygon_vertices.length > 0) {
            ctx.beginPath();
            ctx.moveTo(polygon_vertices[0][0], polygon_vertices[0][1]);

            for (let i = 1; i < polygon_vertices.length; i++) {
              ctx.lineTo(polygon_vertices[i][0], polygon_vertices[i][1]);
            }

            ctx.closePath();

            // Fill polygon
            ctx.fillStyle = fillColor;
            ctx.fill();

            // Stroke polygon
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = lineWidth;
            ctx.stroke();

            // Draw label if hovered
            if (isHovered) {
              const centroid = room.centroid;
              const label = `${room.id}\n${(room.confidence * 100).toFixed(1)}%`;
              const padding = 6;
              const fontSize = 14;

              ctx.font = `bold ${fontSize}px sans-serif`;
              const lines = label.split('\n');
              const maxWidth = Math.max(...lines.map(line => ctx.measureText(line).width));

              // Position label at centroid
              const labelX = centroid[0] - maxWidth / 2;
              const labelY = centroid[1] - (lines.length * fontSize) / 2;

              // Draw label background
              ctx.fillStyle = 'rgba(0, 200, 0, 0.9)';
              ctx.fillRect(
                labelX - padding,
                labelY - fontSize - padding,
                maxWidth + padding * 2,
                lines.length * fontSize + padding * 2
              );

              // Draw label text
              ctx.fillStyle = 'white';
              lines.forEach((line, i) => {
                const textX = centroid[0] - ctx.measureText(line).width / 2;
                const textY = labelY + i * fontSize;
                ctx.fillText(line, textX, textY);
              });
            }
          }
        });

        setImageLoaded(true);
      };

      img.onerror = () => {
        console.error('Failed to load image for v1 visualization');
      };

      img.src = imageUrl;
    }, [imageUrl, rooms, hoveredRoom]);

    // Handle mouse move to detect hover over rooms
    const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;

      const x = (e.clientX - rect.left) * scaleX;
      const y = (e.clientY - rect.top) * scaleY;

      // Find room under cursor using point-in-polygon test
      const hoveredRoom = rooms.find((room) => {
        return isPointInPolygon([x, y], room.polygon_vertices);
      });

      setHoveredRoom(hoveredRoom?.id || null);
    };

    const handleMouseLeave = () => {
      setHoveredRoom(null);
    };

    return (
      <div className="relative w-full">
        <canvas
          ref={canvasRef}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          className="w-full h-auto border rounded shadow-sm cursor-pointer"
          style={{
            display: imageLoaded ? 'block' : 'none',
            maxWidth: '768px',
            maxHeight: '512px',
            objectFit: 'contain'
          }}
        />
        {!imageLoaded && (
          <div className="flex items-center justify-center h-64 bg-gray-100 rounded border">
            <p className="text-gray-500">Loading visualization...</p>
          </div>
        )}
      </div>
    );
  });

V1RoomVisualization.displayName = 'V1RoomVisualization';

/**
 * Point-in-polygon test using ray casting algorithm
 */
function isPointInPolygon(point: [number, number], polygon: [number, number][]): boolean {
  const [x, y] = point;
  let inside = false;

  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];

    const intersect = ((yi > y) !== (yj > y)) &&
      (x < (xj - xi) * (y - yi) / (yj - yi) + xi);

    if (intersect) inside = !inside;
  }

  return inside;
}
