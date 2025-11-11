import React, { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';
import type { Room } from '../types';

interface RoomVisualizationProps {
  imageUrl: string;
  rooms: Room[];
}

export interface RoomVisualizationRef {
  getCanvas: () => HTMLCanvasElement | null;
}

/**
 * Client-side Canvas component for visualizing room detections.
 * Used for v2 model which returns JSON only (no server-rendered visualization).
 */
export const RoomVisualization = forwardRef<RoomVisualizationRef, RoomVisualizationProps>(
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

      // Draw room bounding boxes
      rooms.forEach((room) => {
        const { bounding_box, id, confidence } = room;
        const { x_min, y_min, x_max, y_max } = bounding_box;

        // Calculate box dimensions
        const width = x_max - x_min;
        const height = y_max - y_min;

        // Determine color and style based on hover state
        const isHovered = hoveredRoom === id;
        const strokeColor = isHovered ? 'rgba(255, 165, 0, 0.9)' : 'rgba(255, 140, 0, 0.7)';
        const fillColor = isHovered ? 'rgba(255, 140, 0, 0.15)' : 'rgba(255, 140, 0, 0.1)';
        const lineWidth = isHovered ? 4 : 3;

        // Fill bounding box
        ctx.fillStyle = fillColor;
        ctx.fillRect(x_min, y_min, width, height);

        // Draw bounding box outline
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth;
        ctx.strokeRect(x_min, y_min, width, height);

        // Draw confidence label if hovered
        if (isHovered) {
          const label = `${(confidence * 100).toFixed(1)}%`;
          const padding = 4;
          const fontSize = 14;

          ctx.font = `bold ${fontSize}px sans-serif`;
          const textWidth = ctx.measureText(label).width;

          // Position label at top-left of bounding box
          const labelX = x_min;
          const labelY = y_min - 8;

          // Draw label background
          ctx.fillStyle = 'rgba(255, 140, 0, 0.9)';
          ctx.fillRect(
            labelX - padding,
            labelY - fontSize - padding,
            textWidth + padding * 2,
            fontSize + padding * 2
          );

          // Draw label text
          ctx.fillStyle = 'white';
          ctx.fillText(label, labelX, labelY - padding);
        }
      });

      setImageLoaded(true);
    };

    img.onerror = () => {
      console.error('Failed to load image for visualization');
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

    // Find room under cursor
    const hoveredRoom = rooms.find((room) => {
      const { x_min, y_min, x_max, y_max } = room.bounding_box;
      return x >= x_min && x <= x_max && y >= y_min && y <= y_max;
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

RoomVisualization.displayName = 'RoomVisualization';
