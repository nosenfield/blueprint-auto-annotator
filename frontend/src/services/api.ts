/**
 * API client for room detection service.
 * Supports both v1 (wall model) and v2 (room model).
 */
import type {
  ModelVersion,
  DetectionOptions,
  DetectionResponse,
  WallDetectionResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Detect rooms in blueprint image using v1 model (wall detection → geometric conversion).
 * For v1, this function handles the 2-step pipeline internally.
 */
export async function detectRooms(
  imageBase64: string,
  options: DetectionOptions = {}
): Promise<DetectionResponse> {
  const {
    version = 'v1',
    confidence_threshold = 0.10,
    min_room_area = 2000,
    return_visualization = true,
  } = options;

  if (version === 'v1') {
    // V1 pipeline: wall detection → geometric conversion
    // Step 1: Detect walls
    const wallResponse = await detectWallsV1(imageBase64, confidence_threshold);
    
    if (!wallResponse.success || wallResponse.walls.length === 0) {
      return {
        success: true,
        rooms: [],
        total_rooms: 0,
        processing_time_ms: wallResponse.processing_time_ms,
        model_version: 'v1',
        visualization: wallResponse.visualization,
        metadata: {
          ...wallResponse.metadata,
          intermediate_detections: 0,
        },
      };
    }

    // Step 2: Convert walls to rooms
    const [width, height] = wallResponse.metadata?.image_dimensions || [0, 0];
    
    const conversionResponse = await convertWallsToRoomsV1(
      wallResponse.walls,
      [width, height],
      {
        min_room_area,
        return_visualization,
      }
    );

    return {
      ...conversionResponse,
      processing_time_ms: wallResponse.processing_time_ms + conversionResponse.processing_time_ms,
      metadata: {
        ...conversionResponse.metadata,
        wall_detection_time_ms: wallResponse.processing_time_ms,
        geometric_conversion_time_ms: conversionResponse.processing_time_ms,
      },
    };
  } else {
    // V2: Direct room detection (not implemented yet)
    throw new Error('V2 model not yet implemented');
  }
}

/**
 * Detect walls in blueprint image (v1 model).
 * This is for debugging/testing only - normal users should use detectRooms().
 */
export async function detectWallsV1(
  imageBase64: string,
  confidence_threshold: number = 0.10
): Promise<WallDetectionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/detect-walls`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image: imageBase64,
      confidence_threshold,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: 'Wall detection failed' } }));
    throw new Error(error.error?.message || 'Wall detection failed');
  }

  return response.json();
}

/**
 * Convert wall detections to room polygons (v1 model).
 * This is for debugging/testing only - normal users should use detectRooms().
 */
export async function convertWallsToRoomsV1(
  walls: any[],
  imageDimensions: [number, number],
  options: {
    min_room_area?: number;
    return_visualization?: boolean;
  } = {}
): Promise<DetectionResponse> {
  const { min_room_area = 2000, return_visualization = true } = options;

  const response = await fetch(`${API_BASE_URL}/api/convert-to-rooms`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      walls,
      image_dimensions: imageDimensions,
      min_room_area,
      return_visualization,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: 'Geometric conversion failed' } }));
    throw new Error(error.error?.message || 'Geometric conversion failed');
  }

  return response.json();
}

